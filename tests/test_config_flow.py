"""Test della configurazione da interfaccia."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rilevatore_consumi.const import (
    CONF_AI_TASK,
    CONF_EXISTING,
    CONF_INITIAL,
    CONF_MAX_JUMP,
    CONF_TYPE,
    DOMAIN,
)

from .conftest import make_entry


async def _start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result


async def test_manual_reading(hass: HomeAssistant) -> None:
    """Lettura iniziale digitata a mano."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Gas", CONF_TYPE: "gas", CONF_INITIAL: 5726},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Gas"
    assert result["data"][CONF_INITIAL] == 5726
    assert isinstance(result["data"][CONF_INITIAL], int)
    assert CONF_EXISTING not in result["data"]


async def test_reading_from_existing_sensor(hass: HomeAssistant) -> None:
    """La lettura si importa dalla sola parte intera di un sensore esistente."""
    hass.states.async_set("sensor.gas_consumption", "5726.713")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Gas",
            CONF_TYPE: "gas",
            CONF_EXISTING: "sensor.gas_consumption",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_INITIAL] == 5726
    assert result["data"][CONF_EXISTING] == "sensor.gas_consumption"


async def test_typed_reading_wins_over_existing_sensor(hass: HomeAssistant) -> None:
    """Se scrivi anche la lettura, vale quella scritta."""
    hass.states.async_set("sensor.gas_consumption", "5000")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Gas",
            CONF_TYPE: "gas",
            CONF_INITIAL: 5726,
            CONF_EXISTING: "sensor.gas_consumption",
        },
    )
    assert result["data"][CONF_INITIAL] == 5726


async def test_reading_required(hass: HomeAssistant) -> None:
    """Senza lettura e senza sensore valido si resta nel modulo."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Acqua", CONF_TYPE: "water"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "reading_required"}


async def test_existing_sensor_without_number(hass: HomeAssistant) -> None:
    """Un sensore orfano (non disponibile) non basta."""
    hass.states.async_set("sensor.gas_consumption", "unavailable")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Gas", CONF_TYPE: "gas", CONF_EXISTING: "sensor.gas_consumption"},
    )
    assert result["errors"] == {"base": "reading_required"}


async def test_name_required(hass: HomeAssistant) -> None:
    """Il nome non può essere vuoto."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "   ", CONF_TYPE: "gas", CONF_INITIAL: 1}
    )
    assert result["errors"] == {"name": "name_required"}


async def test_duplicate_is_aborted(hass: HomeAssistant) -> None:
    """Stesso tipo e stesso nome: un solo contatore."""
    make_entry(name="Gas").add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Gas", CONF_TYPE: "gas", CONF_INITIAL: 1}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_gas_and_water_can_coexist(hass: HomeAssistant) -> None:
    """Un contatore gas e uno acqua insieme."""
    for name, kind, reading in (("Gas", "gas", 5726), ("Acqua", "water", 364)):
        result = await _start(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": name, CONF_TYPE: kind, CONF_INITIAL: reading}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert hass.states.get("sensor.gas_meter_reading").state == "5726"
    assert hass.states.get("sensor.acqua_meter_reading").state == "364"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Opzioni: entità AI e salto massimo."""
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MAX_JUMP: 50}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_MAX_JUMP] == 50
    assert CONF_AI_TASK not in entry.options
    assert hass.states.get("sensor.gas_meter_reading").attributes["max_jump"] == 50
