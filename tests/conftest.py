"""Fixture comuni per i test di Rilevatore consumi."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rilevatore_consumi.const import (
    CONF_INITIAL,
    CONF_TYPE,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Abilita le integrazioni custom in ogni test."""
    return


def make_entry(
    reading: int = 5726, meter_type: str = "gas", name: str = "Gas", **extra
) -> MockConfigEntry:
    """Crea una voce di configurazione già pronta."""
    data = {"name": name, CONF_TYPE: meter_type, CONF_INITIAL: reading, **extra}
    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        title=name,
        unique_id=f"{meter_type}_{name.lower()}",
    )
