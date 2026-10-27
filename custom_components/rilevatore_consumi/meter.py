"""Logica del contatore manuale: letture, periodi, validazione e lettura da foto."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import selector
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AI_TASK,
    CONF_INITIAL,
    CONF_MAX_JUMP,
    CONF_TYPE,
    DEFAULT_MAX_JUMP,
    DOMAIN,
    MAX_READING,
    PERIODS,
    STORAGE_VERSION,
    TYPE_GAS,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .image import PhotoImage

_LOGGER = logging.getLogger(__name__)

MAX_LOG = 60

INSTRUCTIONS = {
    "gas": (
        "Nella foto c'è un contatore del gas. Leggi il valore totale mostrato sul "
        "display o sui rulli, in metri cubi (m³). Restituisci SOLO la parte intera, "
        "cioè le cifre prima della virgola o del punto decimale, ignorando tutte le "
        "cifre decimali (spesso rosse o dopo il separatore). Ignora numeri di "
        "matricola, anno di costruzione, codici a barre e altre scritte. Togli gli "
        "zeri iniziali (05726.713 diventa 5726). Se le cifre non sono leggibili con "
        "sicurezza, imposta readable=false e non indovinare."
    ),
    "water": (
        "Nella foto c'è un contatore dell'acqua. Leggi il valore totale mostrato sui "
        "rulli o sul display, in metri cubi (m³). Restituisci SOLO la parte intera, "
        "cioè le cifre prima della virgola: di solito sono i rulli neri, mentre i "
        "rulli rossi o le lancette sono i decimali e vanno ignorati. Ignora numeri "
        "di matricola, anno di costruzione, codici a barre e altre scritte. Togli gli "
        "zeri iniziali (00364 diventa 364). Se le cifre non sono leggibili con "
        "sicurezza, imposta readable=false e non indovinare."
    ),
}

PHOTO_STRUCTURE = vol.Schema(
    {
        vol.Required(
            "readable",
            description="True solo se le cifre intere sono leggibili con sicurezza",
        ): selector.BooleanSelector(),
        vol.Optional(
            "reading",
            description="Parte intera della lettura in m³, senza decimali né zeri iniziali",
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=MAX_READING, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
)


def _period_key(period: str, now: datetime) -> str:
    """Chiave che identifica il periodo corrente."""
    if period == "day":
        return now.date().isoformat()
    if period == "month":
        return f"{now.year:04d}-{now.month:02d}"
    return f"{now.year:04d}"


def period_start(period: str, now: datetime) -> datetime:
    """Inizio (ora locale) del periodo corrente."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return start.replace(day=1)
    if period == "year":
        return start.replace(month=1, day=1)
    return start


class Meter:
    """Stato e logica di un contatore (un gas o un'acqua)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Inizializza il contatore."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.reading: int | None = None
        self.previous: int | None = None
        self.updated: datetime | None = None
        self.baselines: dict[str, dict[str, Any]] = {}
        self.log: list[dict[str, Any]] = []
        self.photo: PhotoImage | None = None
        self._listeners: list[Callable[[], None]] = []

    # ------------------------------------------------------------------ proprietà
    @property
    def meter_type(self) -> str:
        """Tipo di contatore (gas / water)."""
        return self.entry.data[CONF_TYPE]

    @property
    def max_jump(self) -> int:
        """Salto massimo accettato senza conferma esplicita."""
        return int(
            self.entry.options.get(
                CONF_MAX_JUMP, DEFAULT_MAX_JUMP.get(self.meter_type, 300)
            )
        )

    # ------------------------------------------------------------------ ciclo di vita
    async def async_load(self) -> None:
        """Carica i dati salvati (o la lettura iniziale)."""
        data = await self._store.async_load()
        now = dt_util.now()
        if data:
            self.reading = data.get("reading")
            self.previous = data.get("previous")
            updated = data.get("updated")
            self.updated = dt_util.parse_datetime(updated) if updated else None
            self.baselines = data.get("baselines", {})
            self.log = list(data.get("log", []))
            if not self.log and self.reading is not None:
                self.log = [self._log_item(self.reading, self.updated or now)]
        else:
            initial = self.entry.data.get(CONF_INITIAL)
            if initial is not None:
                self.reading = int(initial)
                self.updated = now
                self.log = [self._log_item(self.reading, now)]
        if self._roll(now):
            await self._store.async_save(self._as_dict())

    @callback
    def async_start(self) -> Callable[[], None]:
        """Avvia il controllo del cambio periodo a mezzanotte."""

        @callback
        def _midnight(_now: datetime) -> None:
            if self._roll(dt_util.now()):
                self._store.async_delay_save(self._as_dict, 1)
            self._notify()

        return async_track_time_change(self.hass, _midnight, hour=0, minute=0, second=1)

    # ------------------------------------------------------------------ ascoltatori
    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Registra un ascoltatore, restituisce la funzione di rimozione."""
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------ periodi
    def _roll(self, now: datetime) -> bool:
        """Aggiorna le basi di calcolo se è cambiato un periodo."""
        if self.reading is None:
            return False
        changed = False
        for period in PERIODS:
            key = _period_key(period, now)
            base = self.baselines.get(period)
            if base is None or base.get("key") != key:
                self.baselines[period] = {"key": key, "value": self.reading}
                changed = True
        return changed

    def consumption(self, period: str) -> int | None:
        """Consumo nel periodo corrente in m³."""
        base = self.baselines.get(period)
        if self.reading is None or base is None:
            return None
        return max(self.reading - int(base["value"]), 0)

    def last_reset(self, period: str) -> datetime:
        """Inizio del periodo corrente."""
        return period_start(period, dt_util.now())

    def _as_dict(self) -> dict[str, Any]:
        return {
            "reading": self.reading,
            "previous": self.previous,
            "updated": self.updated.isoformat() if self.updated else None,
            "baselines": self.baselines,
            "log": self.log,
        }

    @staticmethod
    def _log_item(value: int, when: datetime, replaced: bool = False) -> dict[str, Any]:
        item: dict[str, Any] = {"t": when.isoformat(), "v": value}
        if replaced:
            item["replaced"] = True
        return item

    # ------------------------------------------------------------------ letture
    async def async_set_reading(
        self, value: float, *, force: bool = False, replace: bool = False
    ) -> None:
        """Registra una nuova lettura (intero in m³) con validazione."""
        new = int(value)
        if new < 0 or new > MAX_READING:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_reading",
                translation_placeholders={"new": str(new)},
            )
        now = dt_util.now()
        self._roll(now)
        current = self.reading
        if current is not None and not replace:
            if new < current:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="reading_lower",
                    translation_placeholders={"new": str(new), "current": str(current)},
                )
            if not force and new - current > self.max_jump:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="reading_jump",
                    translation_placeholders={
                        "new": str(new),
                        "current": str(current),
                        "max": str(self.max_jump),
                    },
                )
        if current is None:
            for period in PERIODS:
                self.baselines[period] = {"key": _period_key(period, now), "value": new}
        elif replace:
            # Sostituzione contatore: i consumi già maturati nei periodi restano
            for period in PERIODS:
                done = self.consumption(period) or 0
                self.baselines[period]["value"] = new - done
        self.previous = current
        self.reading = new
        self.updated = now
        self.log = [*self.log, self._log_item(new, now, replace)][-MAX_LOG:]
        await self._store.async_save(self._as_dict())
        self._notify()

    # ------------------------------------------------------------------ foto / AI
    async def async_read_photo(self, content: bytes, content_type: str) -> dict[str, Any]:
        """Legge una foto caricata e restituisce una proposta di lettura."""
        if self.photo is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="photo_unavailable"
            )
        self.photo.async_set_image(content, content_type)
        return await self.async_read_media(
            f"media-source://image/{self.photo.entity_id}", content_type
        )

    async def async_read_media(
        self, media_content_id: str, media_content_type: str = "image/jpeg"
    ) -> dict[str, Any]:
        """Legge un'immagine da una sorgente multimediale e propone la lettura."""
        if "ai_task" not in self.hass.config.components:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="ai_task_missing"
            )
        from homeassistant.components import ai_task  # noqa: PLC0415

        try:
            result = await ai_task.async_generate_data(
                self.hass,
                task_name=f"{self.entry.title} - lettura contatore",
                entity_id=self.entry.options.get(CONF_AI_TASK) or None,
                instructions=INSTRUCTIONS.get(self.meter_type, INSTRUCTIONS[TYPE_GAS]),
                structure=PHOTO_STRUCTURE,
                attachments=[
                    {
                        "media_content_id": media_content_id,
                        "media_content_type": media_content_type,
                    }
                ],
            )
        except HomeAssistantError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="ai_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        return self._build_proposal(result.data)

    def _build_proposal(self, data: Any) -> dict[str, Any]:
        """Trasforma la risposta dell'AI in una proposta con eventuali avvisi."""
        data = data if isinstance(data, dict) else {}
        reading = _to_int(data.get("reading"))
        readable = bool(data.get("readable")) and reading is not None
        proposal: dict[str, Any] = {
            "readable": readable,
            "reading": reading if readable else None,
            "current": self.reading,
            "warning": None,
        }
        if not readable:
            proposal["warning"] = "unreadable"
        elif self.reading is not None:
            if reading < self.reading:
                proposal["warning"] = "lower"
            elif reading - self.reading > self.max_jump:
                proposal["warning"] = "jump"
        return proposal


def _to_int(value: Any) -> int | None:
    """Converte in intero la parte intera di un valore, se possibile."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= MAX_READING else None
