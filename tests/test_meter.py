"""Test di letture, validazione, periodi e persistenza."""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.rilevatore_consumi.const import DOMAIN

from .conftest import make_entry

SENSOR = "sensor.gas_meter_reading"
TODAY = "sensor.gas_consumption_today"
MONTH = "sensor.gas_consumption_this_month"
YEAR = "sensor.gas_consumption_this_year"
NUMBER = "number.gas_new_reading"


async def _setup(hass: HomeAssistant, **kwargs):
    entry = make_entry(**kwargs)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _set(hass: HomeAssistant, reading, **extra) -> None:
    await hass.services.async_call(
        DOMAIN,
        "set_reading",
        {"reading": reading, **extra},
        target={"entity_id": SENSOR},
        blocking=True,
    )


async def test_initial_state(hass: HomeAssistant) -> None:
    """Lettura iniziale, consumi a zero, attributi per la card."""
    entry = await _setup(hass)
    state = hass.states.get(SENSOR)
    assert state.state == "5726"
    assert state.attributes["device_class"] == "gas"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["unit_of_measurement"] == "m³"
    assert state.attributes["entry_id"] == entry.entry_id
    assert state.attributes["previous_reading"] is None
    assert hass.states.get(NUMBER).state == "5726"
    for entity_id in (TODAY, MONTH, YEAR):
        assert hass.states.get(entity_id).state == "0"
        assert hass.states.get(entity_id).attributes["state_class"] == "total"


async def test_water_device_class(hass: HomeAssistant) -> None:
    """Il contatore dell'acqua usa la classe water."""
    entry = make_entry(364, "water", "Acqua")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.acqua_meter_reading").attributes["device_class"] == "water"


async def test_new_reading_updates_periods(hass: HomeAssistant) -> None:
    """Una nuova lettura aggiorna lettura e consumi per periodo."""
    await _setup(hass)
    await _set(hass, 5730)
    state = hass.states.get(SENSOR)
    assert state.state == "5730"
    assert state.attributes["previous_reading"] == 5726
    assert state.attributes["last_reading_time"]
    for entity_id in (TODAY, MONTH, YEAR):
        assert hass.states.get(entity_id).state == "4"


async def test_decimals_are_dropped(hass: HomeAssistant) -> None:
    """Si lavora solo con la parte intera."""
    await _setup(hass)
    await _set(hass, 5730.9)
    assert hass.states.get(SENSOR).state == "5730"


async def test_number_entity_sets_reading(hass: HomeAssistant) -> None:
    """Il campo numerico registra la lettura."""
    await _setup(hass)
    await hass.services.async_call(
        "number", "set_value", {"entity_id": NUMBER, "value": 5740}, blocking=True
    )
    assert hass.states.get(SENSOR).state == "5740"


async def test_lower_reading_rejected(hass: HomeAssistant) -> None:
    """Una lettura più bassa è rifiutata, dal servizio e dal campo."""
    await _setup(hass)
    with pytest.raises(ServiceValidationError):
        await _set(hass, 5700)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "number", "set_value", {"entity_id": NUMBER, "value": 5700}, blocking=True
        )
    assert hass.states.get(SENSOR).state == "5726"


async def test_same_reading_is_accepted(hass: HomeAssistant) -> None:
    """Rileggere lo stesso valore non è un errore e non cambia i consumi."""
    await _setup(hass)
    await _set(hass, 5726)
    assert hass.states.get(TODAY).state == "0"


async def test_big_jump_needs_force(hass: HomeAssistant) -> None:
    """Un aumento oltre il massimo richiede conferma esplicita."""
    await _setup(hass)  # massimo gas: 300 m³
    with pytest.raises(ServiceValidationError):
        await _set(hass, 5726 + 301)
    await _set(hass, 5726 + 300)  # al limite: va bene
    assert hass.states.get(SENSOR).state == "6026"
    await _set(hass, 6026 + 400, force=True)
    assert hass.states.get(SENSOR).state == "6426"


async def test_max_jump_option(hass: HomeAssistant) -> None:
    """Il massimo si cambia dalle opzioni."""
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"max_jump": 10})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError):
        await _set(hass, 5740)
    await _set(hass, 5736)
    assert hass.states.get(SENSOR).state == "5736"


async def test_water_default_jump(hass: HomeAssistant) -> None:
    """Per l'acqua il massimo predefinito è più basso."""
    entry = make_entry(364, "water", "Acqua")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "set_reading",
            {"reading": 364 + 101},
            target={"entity_id": "sensor.acqua_meter_reading"},
            blocking=True,
        )


async def test_replace_meter_keeps_consumption(hass: HomeAssistant) -> None:
    """Con il contatore sostituito, i consumi già maturati restano."""
    await _setup(hass)
    await _set(hass, 5736)  # 10 m³ nei periodi in corso
    await _set(hass, 3, replace_meter=True)
    assert hass.states.get(SENSOR).state == "3"
    for entity_id in (TODAY, MONTH, YEAR):
        assert hass.states.get(entity_id).state == "10"
    await _set(hass, 8)
    for entity_id in (TODAY, MONTH, YEAR):
        assert hass.states.get(entity_id).state == "15"


async def test_invalid_values(hass: HomeAssistant) -> None:
    """Valori fuori intervallo."""
    await _setup(hass)
    with pytest.raises(Exception):  # noqa: B017 - lo schema del servizio rifiuta
        await _set(hass, -5)
    with pytest.raises(Exception):  # noqa: B017
        await _set(hass, 10**9)


async def test_period_rollover(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A mezzanotte giorno e mese ripartono, l'anno no (31 ottobre → 1 novembre)."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to("2026-10-31 22:00:00+00:00")  # 31/10 23:00 a Roma
    await _setup(hass)
    await _set(hass, 5736)
    assert hass.states.get(TODAY).state == "10"

    freezer.move_to("2026-10-31 23:00:30+00:00")  # 1/11 00:00:30 a Roma
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(TODAY).state == "0"
    assert hass.states.get(MONTH).state == "0"
    assert hass.states.get(YEAR).state == "10"
    assert hass.states.get(MONTH).attributes["last_reset"].startswith("2026-11-01T00:00:00")

    await _set(hass, 5740)
    assert hass.states.get(TODAY).state == "4"
    assert hass.states.get(MONTH).state == "4"
    assert hass.states.get(YEAR).state == "14"


async def test_year_rollover(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A capodanno riparte anche l'anno."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to("2026-12-31 22:00:00+00:00")
    await _setup(hass)
    await _set(hass, 5800)
    assert hass.states.get(YEAR).state == "74"
    freezer.move_to("2026-12-31 23:00:30+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(YEAR).state == "0"


async def test_rollover_while_offline(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage
) -> None:
    """Se Home Assistant era spento a cavallo di un periodo, riparte da zero."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to("2026-10-10 10:00:00+00:00")
    entry = await _setup(hass)
    await _set(hass, 5740)
    await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to("2026-11-03 10:00:00+00:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "5740"
    assert hass.states.get(TODAY).state == "0"
    assert hass.states.get(MONTH).state == "0"
    assert hass.states.get(YEAR).state == "14"


async def test_persistence_across_reload(hass: HomeAssistant) -> None:
    """Lettura, lettura precedente e consumi sopravvivono a un riavvio."""
    entry = await _setup(hass)
    await _set(hass, 5740)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(SENSOR)
    assert state.state == "5740"
    assert state.attributes["previous_reading"] == 5726
    assert hass.states.get(MONTH).state == "14"


async def test_initial_reading_not_reapplied(hass: HomeAssistant) -> None:
    """Dopo un riavvio vale la lettura salvata, non quella iniziale."""
    entry = await _setup(hass)
    await _set(hass, 5750)
    await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "5750"


async def test_remove_entry_deletes_storage(hass: HomeAssistant, hass_storage) -> None:
    """Rimuovendo il contatore si cancellano anche i dati salvati."""
    entry = await _setup(hass)
    await _set(hass, 5730)
    key = f"{DOMAIN}.{entry.entry_id}"
    assert key in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage
