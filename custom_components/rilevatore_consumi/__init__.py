"""Integrazione Rilevatore consumi gas/acqua."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    CARD_FILE,
    CONF_EXISTING,
    DOMAIN,
    STORAGE_VERSION,
    URL_BASE,
    VERSION,
)
from .meter import Meter
from .views import ImportView, PhotoView

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = ["sensor", "number", "image"]

type RilevatoreConfigEntry = ConfigEntry[Meter]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Registra la card e l'endpoint per le foto (una sola volta)."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(Path(__file__).parent / "frontend"), False)]
    )
    frontend.add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILE}?v={VERSION}")
    hass.http.register_view(PhotoView())
    hass.http.register_view(ImportView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RilevatoreConfigEntry) -> bool:
    """Configura un contatore."""
    meter = Meter(hass, entry)
    await meter.async_load()
    entry.runtime_data = meter

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(meter.async_start())
    _async_adopt_entity_id(hass, entry)
    _async_sync_device_name(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_title_changed))
    return True


def _async_sync_device_name(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Il nome del dispositivo segue il titolo dell'integrazione."""
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    if device is not None and device.name != entry.title:
        registry.async_update_device(device.id, name=entry.title)


async def _async_title_changed(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Dopo una modifica (nome o opzioni): aggiorna il dispositivo e ricarica."""
    _async_sync_device_name(hass, entry)
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: RilevatoreConfigEntry) -> bool:
    """Scarica un contatore."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: RilevatoreConfigEntry) -> None:
    """Cancella i dati salvati quando il contatore viene rimosso."""
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()


def _async_adopt_entity_id(hass: HomeAssistant, entry: RilevatoreConfigEntry) -> None:
    """Se richiesto, prende il posto di un sensore esistente (stesso entity_id).

    Così le statistiche della plancia Energia, legate al nome del sensore,
    continuano senza interruzioni.
    """
    preferred = entry.options.get(CONF_EXISTING) or entry.data.get(CONF_EXISTING)
    issue_id = f"entity_id_busy_{entry.entry_id}"
    if not preferred:
        return

    registry = er.async_get(hass)
    current = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_total")
    if current is None or current == preferred:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    occupant = registry.async_get(preferred)
    if occupant is not None and occupant.platform != DOMAIN:
        state = hass.states.get(preferred)
        # Un'entità orfana (non più fornita da nessuno) si può sostituire
        if state is None or state.attributes.get("restored"):
            _LOGGER.info("Rimuovo l'entità orfana %s per riutilizzare il nome", preferred)
            registry.async_remove(preferred)
            occupant = None

    if occupant is None and hass.states.get(preferred) is None:
        registry.async_update_entity(current, new_entity_id=preferred)
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="entity_id_busy",
        translation_placeholders={"entity_id": preferred, "name": entry.title},
    )
