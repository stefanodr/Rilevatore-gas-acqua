"""Endpoint HTTP per caricare la foto del contatore dalla card."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
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

        result = await meter.async_apply_history(readings)
        statistics: dict[str, Any] | None = None
        if total_id and "recorder" in hass.config.components:
            from .history import async_write_history  # noqa: PLC0415

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
        return self.json({**summary, **result, "committed": True, "statistics": statistics})
