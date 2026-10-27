"""Test del recupero dello storico (statistiche a lungo termine)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.components.recorder import Recorder, get_instance
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.rilevatore_consumi.const import DOMAIN
from custom_components.rilevatore_consumi.history import merge_rows

from .conftest import make_entry

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Il recorder va avviato prima di hass: sostituisce la fixture comune."""
    return


OLD = "sensor.vecchio_gas"
NEW = "sensor.gas_meter_reading"


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


async def _rows(hass: HomeAssistant, statistic_id: str) -> list[dict]:
    instance = get_instance(hass)
    await async_wait_recording_done(hass)
    result = await instance.async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utc_from_timestamp(0),
        None,
        {statistic_id},
        "hour",
        None,
        {"state", "sum"},
    )
    return result.get(statistic_id, [])


def _hours(first, values: list[tuple[float, float]]) -> list[dict]:
    return [
        {"start": first + timedelta(hours=i), "state": s, "sum": m}
        for i, (s, m) in enumerate(values)
    ]


def test_merge_shifts_new_rows() -> None:
    """Le righe nuove proseguono la somma del vecchio sensore."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    old = _hours(t0, [(5700.0, 10.0), (5710.0, 20.0), (5720.0, 30.0)])
    new = _hours(t0 + timedelta(hours=5), [(5726.0, 0.0), (5728.0, 2.0)])
    merged = merge_rows(old, new)
    assert [round(m["sum"], 3) for m in merged] == [10, 20, 30, 36, 38]
    assert [m["state"] for m in merged] == [5700, 5710, 5720, 5726, 5728]


def test_merge_meter_replaced_not_added() -> None:
    """Se la lettura nuova è più bassa (contatore sostituito) il salto non si somma."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    old = _hours(t0, [(5700.0, 10.0)])
    new = _hours(t0 + timedelta(hours=3), [(10.0, 0.0), (12.0, 2.0)])
    merged = merge_rows(old, new)
    assert [round(m["sum"], 3) for m in merged] == [10, 10, 12]


def test_merge_ignores_overlap_and_empty() -> None:
    """Le righe vecchie che si sovrappongono alle nuove non si importano."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    old = _hours(t0, [(1.0, 1.0), (2.0, 2.0)])
    with pytest.raises(ServiceValidationError):
        merge_rows(old, _hours(t0, [(5.0, 0.0)]))
    assert len(merge_rows(old, [])) == 2


async def _setup(hass: HomeAssistant):
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_service_copies_history(recorder_mock: Recorder, hass: HomeAssistant) -> None:
    """Lo storico del vecchio sensore compare su quello nuovo, senza buchi."""
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    t0 = now - timedelta(days=30)
    old_rows = [
        {"start": t0 + timedelta(hours=i), "state": 5000.0 + i, "sum": float(i)}
        for i in range(0, 24 * 25)
    ]
    async_import_statistics(hass, _meta(OLD), old_rows)
    await async_wait_recording_done(hass)
    await _setup(hass)

    response = await hass.services.async_call(
        DOMAIN,
        "import_history",
        {"source": OLD},
        target={"entity_id": NEW},
        blocking=True,
        return_response=True,
    )
    assert response[NEW]["imported_hours"] == 24 * 25
    rows = await _rows(hass, NEW)
    assert len(rows) >= 24 * 25
    assert rows[0]["sum"] == 0.0
    assert rows[24 * 25 - 1]["sum"] == 24 * 25 - 1

    # ripetere non rovina nulla
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_history", {"source": OLD},
            target={"entity_id": NEW}, blocking=True, return_response=True,
        )
    assert len(await _rows(hass, NEW)) == len(rows)


async def test_service_errors(recorder_mock: Recorder, hass: HomeAssistant) -> None:
    """Origine inesistente o uguale alla destinazione."""
    await _setup(hass)
    for source in ("sensor.non_esiste", NEW):
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "import_history", {"source": source},
                target={"entity_id": NEW}, blocking=True, return_response=True,
            )


async def test_service_shifts_existing_new_stats(
    recorder_mock: Recorder, hass: HomeAssistant
) -> None:
    """Le ore già registrate dal sensore nuovo (ripartite da 0) proseguono il vecchio."""
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    t0 = now - timedelta(days=10)
    old = [
        {"start": t0 + timedelta(hours=i), "state": 5000.0 + i, "sum": float(i)}
        for i in range(48)
    ]
    first_new = t0 + timedelta(days=5)
    new = [
        {"start": first_new + timedelta(hours=i), "state": 5060.0 + i, "sum": float(i)}
        for i in range(5)
    ]
    async_import_statistics(hass, _meta(OLD), old)
    async_import_statistics(hass, _meta(NEW), new)
    await async_wait_recording_done(hass)
    await _setup(hass)

    await hass.services.async_call(
        DOMAIN, "import_history", {"source": OLD},
        target={"entity_id": NEW}, blocking=True, return_response=True,
    )
    rows = await _rows(hass, NEW)
    sums = [r["sum"] for r in rows]
    assert sums == sorted(sums)  # mai un calo: la serie è continua
    assert sums[47] == 47.0
    # 47 (ultima vecchia) + salto di lettura 5060-5047=13 + incremento locale
    assert sums[48] == 47.0 + 13.0
    assert sums[52] == 47.0 + 13.0 + 4.0
