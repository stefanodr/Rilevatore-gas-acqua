"""Sensori: lettura del contatore e consumi per periodo."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import (
    config_validation as cv,
    entity_platform,
    entity_registry as er,
    selector,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_FORCE,
    ATTR_MEDIA,
    ATTR_READING,
    ATTR_REPLACE,
    DOMAIN,
    MAX_READING,
    PERIODS,
    TYPE_WATER,
)
from .entity import RilevatoreEntity
from .meter import Meter

PARALLEL_UPDATES = 0


def _device_class(meter: Meter) -> SensorDeviceClass:
    return SensorDeviceClass.WATER if meter.meter_type == TYPE_WATER else SensorDeviceClass.GAS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[Meter],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea i sensori e registra i servizi."""
    meter = entry.runtime_data
    async_add_entities(
        [TotalSensor(meter), *(PeriodSensor(meter, period) for period in PERIODS)]
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_reading",
        {
            vol.Required(ATTR_READING): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=MAX_READING)
            ),
            vol.Optional(ATTR_FORCE, default=False): cv.boolean,
            vol.Optional(ATTR_REPLACE, default=False): cv.boolean,
        },
        "async_service_set_reading",
    )
    platform.async_register_entity_service(
        "import_history",
        {vol.Required("source"): cv.entity_id},
        "async_service_import_history",
        supports_response=SupportsResponse.OPTIONAL,
    )
    platform.async_register_entity_service(
        "read_from_photo",
        {vol.Required(ATTR_MEDIA): selector.MediaSelector()},
        "async_service_read_from_photo",
        supports_response=SupportsResponse.ONLY,
    )


class TotalSensor(RilevatoreEntity, SensorEntity):
    """Lettura del contatore (usata dalla plancia Energia)."""

    _attr_translation_key = "total"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_suggested_display_precision = 0
    # L'elenco delle ultime letture serve solo alla card: non va nel database
    _unrecorded_attributes = frozenset({"recent_readings", "day_entity",
        "month_entity", "year_entity", "photo_entity", "input_entity"})

    def __init__(self, meter: Meter) -> None:
        """Inizializza il sensore."""
        super().__init__(meter, "total")
        self._attr_device_class = _device_class(meter)

    @property
    def native_value(self) -> int | None:
        """Lettura attuale."""
        return self.meter.reading

    @property
    def available(self) -> bool:
        """Disponibile solo se esiste una lettura."""
        return self.meter.reading is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attributi usati anche dalla card."""
        updated = self.meter.updated
        registry = er.async_get(self.hass)
        entry_id = self.meter.entry.entry_id

        def sibling(domain: str, key: str) -> str | None:
            return registry.async_get_entity_id(domain, DOMAIN, f"{entry_id}_{key}")

        return {
            "entry_id": entry_id,
            "day_entity": sibling("sensor", "consumption_day"),
            "month_entity": sibling("sensor", "consumption_month"),
            "year_entity": sibling("sensor", "consumption_year"),
            "photo_entity": sibling("image", "photo"),
            "input_entity": sibling("number", "reading_input"),
            "meter_type": self.meter.meter_type,
            "previous_reading": self.meter.previous,
            "last_reading_time": updated.isoformat() if updated else None,
            "max_jump": self.meter.max_jump,
            "recent_readings": self.meter.log[-12:],
        }


class PeriodSensor(RilevatoreEntity, SensorEntity):
    """Consumo nel periodo corrente (giorno, mese, anno)."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_suggested_display_precision = 0
    _unrecorded_attributes = frozenset({"partial"})

    def __init__(self, meter: Meter, period: str) -> None:
        """Inizializza il sensore di periodo."""
        super().__init__(meter, f"consumption_{period}")
        self._period = period
        self._attr_translation_key = f"consumption_{period}"
        self._attr_device_class = _device_class(meter)

    @property
    def native_value(self) -> int | None:
        """Consumo del periodo."""
        return self.meter.consumption(self._period)

    @property
    def available(self) -> bool:
        """Disponibile solo se esiste una lettura."""
        return self.meter.reading is not None

    @property
    def last_reset(self) -> datetime:
        """Inizio del periodo corrente."""
        return self.meter.last_reset(self._period)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """partial: manca la lettura di inizio periodo, il consumo conta da dopo."""
        return {"partial": not self.meter.is_exact(self._period)}
