"""Entità base per Rilevatore consumi."""

from __future__ import annotations

from typing import Any

from homeassistant.core import ServiceResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CONF_TYPE, DOMAIN
from .meter import Meter


class RilevatoreEntity(Entity):
    """Base comune: tutte le entità di un contatore condividono lo stesso Meter."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, meter: Meter, key: str) -> None:
        """Inizializza l'entità."""
        self.meter = meter
        entry = meter.entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Rilevatore consumi",
            model=entry.data[CONF_TYPE],
        )

    async def async_added_to_hass(self) -> None:
        """Si iscrive agli aggiornamenti del contatore."""
        self.async_on_remove(self.meter.async_add_listener(self.async_write_ha_state))

    # Servizi (disponibili su qualunque entità del contatore)
    async def async_service_set_reading(
        self, reading: float, force: bool = False, replace_meter: bool = False
    ) -> None:
        """Servizio set_reading."""
        await self.meter.async_set_reading(reading, force=force, replace=replace_meter)

    async def async_service_read_from_photo(self, media: dict[str, Any]) -> ServiceResponse:
        """Servizio read_from_photo: restituisce una proposta, non salva nulla."""
        media_id = media.get("media_content_id") if isinstance(media, dict) else None
        if not media_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="media_required"
            )
        return await self.meter.async_read_media(
            media_id, media.get("media_content_type") or "image/jpeg"
        )

    async def async_service_import_history(self, source: str) -> ServiceResponse:
        """Servizio import_history: porta qui lo storico di un vecchio sensore."""
        from .history import async_import_history  # noqa: PLC0415

        result = await async_import_history(self.hass, self.entity_id, source)
        await self.meter.async_refine_baselines()
        return result
