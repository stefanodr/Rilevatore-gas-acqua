"""Test della sostituzione di un sensore esistente (stesso entity_id, stesse statistiche)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from custom_components.rilevatore_consumi.const import DOMAIN

from .conftest import make_entry

OLD = "sensor.gas_consumption"


async def _setup(hass: HomeAssistant, **extra):
    entry = make_entry(existing_entity=OLD, **extra)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_takes_free_entity_id(hass: HomeAssistant) -> None:
    """Se il nome è libero, il nuovo sensore lo prende."""
    await _setup(hass)
    registry = er.async_get(hass)
    assert registry.async_get(OLD).platform == DOMAIN
    assert hass.states.get(OLD).state == "5726"
    assert hass.states.get("sensor.gas_meter_reading") is None


async def test_replaces_orphaned_entity(hass: HomeAssistant) -> None:
    """Il vecchio sensore orfano (entità non più fornita) viene sostituito."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "template",
        "gas_consumption_sensor_template",
        suggested_object_id="gas_consumption",
    )
    hass.states.async_set(OLD, "unavailable", {"restored": True})

    await _setup(hass)

    new = registry.async_get(OLD)
    assert new.platform == DOMAIN
    assert hass.states.get(OLD).state == "5726"
    assert not hass.states.get(OLD).attributes.get("restored")
    # il vecchio unique_id non esiste più
    assert registry.async_get_entity_id(
        "sensor", "template", "gas_consumption_sensor_template"
    ) is None


async def test_busy_entity_is_not_touched(hass: HomeAssistant) -> None:
    """Se il vecchio sensore è ancora attivo non viene tolto: avviso e nome nuovo."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "template",
        "gas_consumption_sensor_template",
        suggested_object_id="gas_consumption",
    )
    hass.states.async_set(OLD, "5000")  # attivo, senza "restored"

    entry = await _setup(hass)

    assert hass.states.get(OLD).state == "5000"
    assert registry.async_get(OLD).platform == "template"
    assert hass.states.get("sensor.gas_meter_reading").state == "5726"
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"entity_id_busy_{entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders["entity_id"] == OLD


async def test_adopts_after_old_one_is_gone(hass: HomeAssistant) -> None:
    """Tolto il vecchio sensore, al ricaricamento il nome viene preso e l'avviso sparisce."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "template",
        "gas_consumption_sensor_template",
        suggested_object_id="gas_consumption",
    )
    hass.states.async_set(OLD, "5000")
    entry = await _setup(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"entity_id_busy_{entry.entry_id}")

    registry.async_remove(OLD)
    hass.states.async_remove(OLD)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get(OLD).platform == DOMAIN
    assert hass.states.get(OLD).state == "5726"
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"entity_id_busy_{entry.entry_id}") is None


async def test_without_existing_entity_nothing_changes(hass: HomeAssistant) -> None:
    """Senza sensore da sostituire si tengono i nomi automatici."""
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.gas_meter_reading").state == "5726"
    assert hass.states.get(OLD) is None
