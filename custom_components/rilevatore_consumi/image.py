"""Ultima foto del contatore (solo in memoria, mai salvata su disco)."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import RilevatoreEntity
from .meter import Meter

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[Meter],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea l'entità immagine."""
    async_add_entities([PhotoImage(hass, entry.runtime_data)])


class PhotoImage(RilevatoreEntity, ImageEntity):
    """Contiene l'ultima foto inviata, usata anche come allegato per l'AI."""

    _attr_translation_key = "last_photo"

    def __init__(self, hass: HomeAssistant, meter: Meter) -> None:
        """Inizializza l'entità."""
        RilevatoreEntity.__init__(self, meter, "photo")
        ImageEntity.__init__(self, hass)
        self._data: bytes | None = None

    async def async_added_to_hass(self) -> None:
        """Si registra sul contatore per poter ricevere le foto."""
        await super().async_added_to_hass()
        self.meter.photo = self

    async def async_will_remove_from_hass(self) -> None:
        """Si scollega dal contatore."""
        if self.meter.photo is self:
            self.meter.photo = None

    async def async_image(self) -> bytes | None:
        """Restituisce l'ultima foto."""
        return self._data

    @callback
    def async_set_image(self, content: bytes, content_type: str) -> None:
        """Memorizza una nuova foto."""
        self._data = content
        self._attr_content_type = content_type
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()
