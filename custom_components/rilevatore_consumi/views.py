"""Endpoint HTTP per caricare la foto del contatore dalla card."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.http import KEY_HASS

from .const import CONF_EXISTING, DOMAIN, MAX_PHOTO_BYTES
from .importer import MAX_FILE_BYTES, ImportFileError, hourly_rows, parse_readings


class PhotoView(HomeAssistantView):
    """POST /api/rilevatore_consumi/photo/{entry_id}: corpo = immagine."""

    url = "/api/rilevatore_consumi/photo/{entry_id}"
    name = "api:rilevatore_consumi:photo"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Ultima proposta da foto (se recente): serve se la pagina si è ricaricata."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return self.json_message("Contatore non trovato", HTTPStatus.NOT_FOUND)
        return self.json({"proposal": entry.runtime_data.recent_proposal()})

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Legge la foto e restituisce la proposta di lettura (non salva nulla)."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return self.json_message("Contatore non trovato", HTTPStatus.NOT_FOUND)

        content_type = request.content_type or ""
        if not content_type.startswith("image/"):
            return self.json_message(
                "Il corpo deve essere un'immagine", HTTPStatus.BAD_REQUEST
            )
        if request.content_length and request.content_length > MAX_PHOTO_BYTES:
            return self.json_message(
                "Immagine troppo grande", HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            )
        body = await request.read()
        if not body or len(body) > MAX_PHOTO_BYTES:
            return self.json_message(
                "Immagine vuota o troppo grande", HTTPStatus.BAD_REQUEST
            )

        try:
            proposal: dict[str, Any] = await entry.runtime_data.async_read_photo(
                body, content_type
            )
        except HomeAssistantError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        return self.json(proposal)


def _notify_done(
    hass: HomeAssistant, entry: Any, count: int, statistics: dict[str, Any] | None
) -> None:
    """Avviso a fine importazione, visibile anche se la pagina si è ricaricata."""
    from homeassistant.components import persistent_notification  # noqa: PLC0415

    it = str(hass.config.language).startswith("it")
    if statistics and statistics.get("error"):
        detail = (
            "lo storico dei grafici NON è stato scritto: " if it
            else "the chart history was NOT written: "
        ) + str(statistics["error"])
    elif statistics and statistics.get("imported_hours") is not None:
        hours = statistics["imported_hours"] + statistics.get("adjusted_hours", 0)
        detail = (
            f"storico dei grafici ricostruito ({hours} ore)." if it
            else f"chart history rebuilt ({hours} hours)."
        )
    else:
        detail = (
            "storico dei grafici già presente." if it else "chart history already present."
        )
    if statistics and statistics.get("sums_fixed"):
        detail += (
            f" Somme della plancia Energia corrette in {statistics['sums_fixed']} punti."
            if it
            else f" Energy dashboard sums fixed at {statistics['sums_fixed']} points."
        )
    message = (
        f"{entry.title}: importate {count} letture; {detail}" if it
        else f"{entry.title}: imported {count} readings; {detail}"
    )
    persistent_notification.async_create(
        hass,
        message,
        title="Rilevatore consumi",
        notification_id=f"{DOMAIN}_import_{entry.entry_id}",
    )


class ImportView(HomeAssistantView):
    """POST /api/rilevatore_consumi/import/{entry_id}?commit=0|1: corpo = CSV."""

    url = "/api/rilevatore_consumi/import/{entry_id}"
    name = "api:rilevatore_consumi:import"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Anteprima (commit=0) o importazione (commit=1) di letture da file."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return self.json_message("Contatore non trovato", HTTPStatus.NOT_FOUND)
        if request.content_length and request.content_length > MAX_FILE_BYTES:
            return self.json({"code": "too_large", "message": "File troppo grande"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        raw = await request.read()
        if len(raw) > MAX_FILE_BYTES:
            return self.json({"code": "too_large", "message": "File troppo grande"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        meter = entry.runtime_data
        registry = er.async_get(hass)
        total_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry_id}_total")
        preferred = tuple(
            e for e in (total_id, entry.options.get(CONF_EXISTING),
                        entry.data.get(CONF_EXISTING)) if e
        )
        try:
            parsed = parse_readings(text, preferred)
        except ImportFileError as err:
            return self.json(
                {"code": err.code, "message": err.code, **err.extra},
                HTTPStatus.BAD_REQUEST,
            )

        readings = parsed.readings
        summary: dict[str, Any] = {
            "count": len(readings),
            "from": readings[0][0].isoformat(),
            "to": readings[-1][0].isoformat(),
            "first_value": readings[0][1],
            "last_value": readings[-1][1],
            "total": parsed.total,
            "decreases": parsed.decreases,
            "ignored_rows": parsed.ignored_rows,
            "duplicates": parsed.duplicates,
            "current": meter.reading,
            "sets_current": meter.reading is None
            or (
                (meter.updated is None or readings[-1][0] > meter.updated)
                and readings[-1][1] >= meter.reading
            ),
            "committed": False,
        }
        if request.query.get("commit") != "1":
            return self.json(summary)

        if meter.import_running:
            return self.json(
                {"code": "import_running", "message": "Importazione già in corso"},
                HTTPStatus.CONFLICT,
            )
        meter.import_running = True
        try:
            replaced = request.query.get("replace") == "1"
            if replaced:
                # Sostituisce tutto: i dati esistenti (letture, consumi, statistiche,
                # cronologia) vengono cancellati e si riparte dal file
                from .history import async_clear_history, meter_sensor_ids  # noqa: PLC0415

                await meter.async_reset(readings[-1][1], log_reading=False)
                try:
                    await async_clear_history(hass, meter_sensor_ids(hass, entry_id))
                except HomeAssistantError as err:
                    return self.json(
                        {"code": "reset_failed", "message": str(err)},
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
            result = await meter.async_apply_history(readings)
            statistics: dict[str, Any] | None = None
            if total_id and "recorder" in hass.config.components:
                from .history import (  # noqa: PLC0415
                async_repair_sums,
                async_write_history,
            )

                try:
                    statistics = await async_write_history(
                        hass, total_id, hourly_rows(readings), entry.title
                    )
                except HomeAssistantError as err:
                    if getattr(err, "translation_key", None) == "nothing_to_import":
                        # Lo storico dei grafici c'è già: non è un errore
                        statistics = {"skipped": "already_present"}
                    else:
                        statistics = {"error": str(err)}
                if statistics is not None and "error" not in statistics:
                    # Controllo finale: se tra storico importato e righe già scritte
                    # dal recorder c'è un salto (barre negative in plancia Energia)
                    # lo si ripara
                    try:
                        fixed = await async_repair_sums(hass, total_id, entry.title)
                        count = fixed["hours_fixed"] + (1 if fixed["anchor_added"] else 0)
                        if count:
                            statistics["sums_fixed"] = count
                    except HomeAssistantError:
                        pass  # nessuno storico da controllare
                await meter.async_refine_baselines()
            _notify_done(hass, entry, summary["count"], statistics)
            return self.json({**summary, **result, "committed": True, "replaced": replaced, "statistics": statistics})
        finally:
            meter.import_running = False
