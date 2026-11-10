"""Diagnostica scaricabile per Rilevatore consumi."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import VERSION

# Nessun dato segreto: si oscura solo il nome scelto dall'utente
TO_REDACT = {"name", "title"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Stato del contatore utile per segnalare un problema."""
    meter = entry.runtime_data
    recorder_loaded = "recorder" in hass.config.components
    return {
        "version": VERSION,
        "entry": async_redact_data(
            {
                "title": entry.title,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "recorder_loaded": recorder_loaded,
        "meter": {
            "reading": meter.reading,
            "previous": meter.previous,
            "updated": meter.updated.isoformat() if meter.updated else None,
            "baselines": meter.baselines,
            "log_count": len(meter.log),
            "recent_log": meter.log[-10:],
            "adopt_import": meter.adopt_import,
            "import_running": meter.import_running,
            "import_progress": meter.import_progress,
        },
    }
