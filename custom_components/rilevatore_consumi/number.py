"""Campo numerico per inserire la lettura."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MAX_READING
from .entity import RilevatoreEntity
from .meter import Meter

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[Meter],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea il campo di inserimento."""
    async_add_entities([ReadingNumber(entry.runtime_data)])


class ReadingNumber(RilevatoreEntity, NumberEntity):
    """Inserimento manuale della lettura (solo numeri interi)."""

    _attr_translation_key = "new_reading"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_READING
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, meter: Meter) -> None:
        """Inizializza il campo."""
        super().__init__(meter, "reading_input")

    @property
    def native_value(self) -> float | None:
        """Lettura attuale."""
        return self.meter.reading

    async def async_set_native_value(self, value: float) -> None:
        """Registra la lettura, con validazione."""
        await self.meter.async_set_reading(value)
