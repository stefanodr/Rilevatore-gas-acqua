"""Endpoint HTTP per caricare la foto del contatore dalla card."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.http import KEY_HASS

from .const import DOMAIN, MAX_PHOTO_BYTES


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
