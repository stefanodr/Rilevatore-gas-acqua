"""Consumi di oggi / mese / anno: base dallo storico e cambio periodo mancato."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.rilevatore_consumi.const import DOMAIN

from .conftest import make_entry

OLD = "sensor.vecchio_gas"
NEW = "sensor.gas_meter_reading"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Il recorder va avviato prima di hass."""
    return


def _meta(statistic_id: str) -> dict:
    return {
        "has_sum": True,
        "mean_type": StatisticMeanType.NONE,
        "name": None,
        "source": "recorder",
        "statistic_id": statistic_id,
        "unit_class": "volume",
        "unit_of_measurement": "m³",
    }


async def test_month_and_year_start_from_history(
    recorder_mock: Recorder, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Mese e anno non ripartono dall'installazione: usano la lettura storica."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to("2026-10-30 08:00:00+01:00")
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    start = dt_util.as_utc(dt_util.parse_datetime("2025-12-31T20:00:00+01:00"))
    rows, total, hour = [], 0.0, start
    while hour < now:
        # un metro cubo ogni 20 ore, a partire dal 31/12
        state = 5280 + (hour - start).total_seconds() // 3600 // 20
        total = state - 5280
        rows.append({"start": hour, "state": float(state), "sum": float(total)})
        hour += timedelta(hours=1)
    async_import_statistics(hass, _meta(OLD), rows)
    await async_wait_recording_done(hass)

    last = rows[-1]["state"]
    entry = make_entry(int(last))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Subito dopo l'installazione i consumi ripartono da zero...
    assert hass.states.get("sensor.gas_consumption_this_year").state == "0"

    # ...poi si copia lo storico e le basi vengono rifinite
    await hass.services.async_call(
        DOMAIN, "import_history", {"source": OLD},
        target={"entity_id": NEW}, blocking=True, return_response=True,
    )
    await hass.async_block_till_done()
    year = int(hass.states.get("sensor.gas_consumption_this_year").state)
    month = int(hass.states.get("sensor.gas_consumption_this_month").state)
    jan1 = next(r for r in rows if dt_util.as_local(r["start"]).day == 1
                and dt_util.as_local(r["start"]).month == 1
                and dt_util.as_local(r["start"]).hour == 1)
    assert year == int(last) - jan1["state"]  # lettura a mezzanotte del 1/1
    assert 0 < month < year
    assert month == int(last) - rows[
        next(i for i, r in enumerate(rows)
             if dt_util.as_local(r["start"]).month == 10
             and dt_util.as_local(r["start"]).day == 1
             and dt_util.as_local(r["start"]).hour == 0) - 1
    ]["state"]


async def test_day_rolls_over_even_if_midnight_was_missed(
    recorder_mock: Recorder, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Se a mezzanotte l'istanza era ferma, "Oggi" riparte da zero comunque."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to("2026-10-29 12:00:00+01:00")
    entry = make_entry(5728)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "set_reading", {"reading": 5729},
        target={"entity_id": NEW}, blocking=True,
    )
    assert hass.states.get("sensor.gas_consumption_today").state == "1"

    # Il giorno dopo si salta la mezzanotte (nessun timer scatta): basta il
    # controllo orario perché il valore si aggiorni
    freezer.move_to("2026-10-30 08:30:00+01:00")
    assert entry.runtime_data.consumption("day") == 0
    freezer.move_to("2026-10-30 09:00:10+01:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.gas_consumption_today").state == "0"
    assert hass.states.get("sensor.gas_consumption_this_month").state == "1"
