"""Logica del contatore manuale: letture, periodi, validazione e lettura da foto."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er, selector
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

MAX_LOG = 400

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
        def _check(_now: datetime) -> None:
            if self._roll(dt_util.now(), exact=True):
                self._store.async_delay_save(self._as_dict, 1)
            self._notify()  # riscrive gli stati: Home Assistant ignora quelli uguali

        # A mezzanotte, e ogni ora come rete di sicurezza (PC o Docker fermi a
        # mezzanotte, sospensione): il cambio giorno non resta mai indietro.
        stop_midnight = async_track_time_change(
            self.hass, _check, hour=0, minute=0, second=1
        )
        stop_hourly = async_track_time_change(self.hass, _check, minute=0, second=5)

        @callback
        def _stop() -> None:
            stop_midnight()
            stop_hourly()

        return _stop

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
    def _roll(self, now: datetime, exact: bool = False) -> bool:
        """Aggiorna le basi di calcolo se è cambiato un periodo.

        exact=True solo al cambio di giorno a mezzanotte: la lettura di quel momento
        è davvero quella di inizio periodo. Negli altri casi la base è provvisoria
        e viene rifinita dallo storico (async_refine_baselines).
        """
        if self.reading is None:
            return False
        changed = False
        for period in PERIODS:
            key = _period_key(period, now)
            base = self.baselines.get(period)
            if base is None or base.get("key") != key:
                self.baselines[period] = {
                    "key": key,
                    "value": self.reading,
                    "exact": exact,
                }
                changed = True
        return changed

    def consumption(self, period: str) -> int | None:
        """Consumo nel periodo corrente in m³."""
        if self.reading is None:
            return None
        # Se il periodo è cambiato e nessuno se n'è accorto, la lettura non è
        # cambiata dall'inizio del nuovo periodo: la base è la lettura attuale.
        if self._roll(dt_util.now(), exact=True):
            self._store.async_delay_save(self._as_dict, 1)
        base = self.baselines.get(period)
        if base is None:
            return None
        return max(self.reading - int(base["value"]), 0)

    def is_exact(self, period: str) -> bool:
        """True se la base del periodo è la lettura vera di inizio periodo."""
        base = self.baselines.get(period)
        return bool(base and base.get("exact"))

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
                self.baselines[period]["exact"] = True
        self.previous = current
        self.reading = new
        self.updated = now
        self.log = [*self.log, self._log_item(new, now, replace)][-MAX_LOG:]
        await self._store.async_save(self._as_dict())
        self._notify()

    # ------------------------------------------------------------------ storico da file
    async def async_apply_history(
        self, readings: list[tuple[datetime, int]]
    ) -> dict[str, Any]:
        """Unisce letture importate: elenco, consumi dei periodi e lettura attuale."""
        now = dt_util.now()
        known: dict[int, dict[str, Any]] = {}
        for item in self.log:
            when = dt_util.parse_datetime(item["t"])
            if when is not None:
                known[int(when.timestamp())] = item
        added = 0
        for when, value in readings:
            key = int(when.timestamp())
            if key not in known:
                known[key] = self._log_item(value, dt_util.as_local(when))
                added += 1
        merged = [known[k] for k in sorted(known)]
        self.log = merged[-MAX_LOG:]

        points = [
            (dt_util.parse_datetime(i["t"]), int(i["v"])) for i in merged
        ]
        points = [(t, v) for t, v in points if t is not None]

        # Lettura attuale: solo se il file ne contiene una più recente e non più bassa
        newest_time, newest_value = readings[-1]
        reading_updated = False
        if self.reading is None or (
            (self.updated is None or newest_time > self.updated)
            and newest_value >= self.reading
        ):
            self.previous = self.reading
            self.reading = newest_value
            self.updated = newest_time
            reading_updated = True
        self._roll(now)

        # Consumi dei periodi in corso: la base è la lettura all'inizio del periodo
        from .importer import value_at  # noqa: PLC0415

        for period in PERIODS:
            base = self.baselines.get(period)
            if base is None or base.get("key") != _period_key(period, now):
                continue
            start = period_start(period, now)
            if points and points[0][0] <= start and self.reading is not None:
                at_start = round(value_at(points, start))
                if at_start < int(base["value"]) and at_start <= self.reading:
                    base["value"] = at_start
                    base["exact"] = True

        await self._store.async_save(self._as_dict())
        self._notify()
        return {
            "added": added,
            "log_size": len(self.log),
            "reading_updated": reading_updated,
        }

    async def async_refine_baselines(self) -> bool:
        """Calcola dallo storico la lettura a inizio giorno/mese/anno.

        Senza questo i consumi di mese e anno ripartirebbero dal momento in cui
        l'integrazione è stata installata. Si usano le statistiche a lungo termine
        del sensore (anche quelle importate da un vecchio sensore o da un file).
        """
        if self.reading is None or "recorder" not in self.hass.config.components:
            return False
        registry = er.async_get(self.hass)
        total_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{self.entry.entry_id}_total"
        )
        if total_id is None:
            return False
        now = dt_util.now()
        pending = [
            period
            for period in PERIODS
            if (base := self.baselines.get(period)) is not None
            and base.get("key") == _period_key(period, now)
            and not base.get("exact")
        ]
        if not pending:
            return False

        from .history import async_state_at  # noqa: PLC0415

        changed = False
        for period in pending:
            value = await async_state_at(
                self.hass, total_id, period_start(period, now)
            )
            if value is None:
                continue
            at_start = round(value)
            base = self.baselines[period]
            # La base provvisoria non può essere più bassa del vero inizio periodo
            if at_start <= self.reading and at_start <= int(base["value"]):
                base["value"] = at_start
                base["exact"] = True
                changed = True
        if changed:
            await self._store.async_save(self._as_dict())
            self._notify()
        return changed

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
