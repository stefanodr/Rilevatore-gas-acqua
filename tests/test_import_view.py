"""Test dell'importazione da file dalla card (anteprima e conferma)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.recorder import Recorder, get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from .conftest import make_entry

CSV = (Path(__file__).parent / "data" / "history_gas.csv").read_bytes()
SENSOR = "sensor.gas_meter_reading"


class _Clock:
    """Orologio del solo contatore: congelare tutto invaliderebbe il token di accesso."""

    def __init__(self) -> None:
        self.value = dt_util.now()

    def set(self, text: str) -> None:
        self.value = dt_util.as_local(dt_util.parse_datetime(text))

    def now(self, *_args, **_kwargs):
        return self.value

    def __getattr__(self, name):
        return getattr(dt_util, name)


@pytest.fixture
def clock():
    clk = _Clock()
    with patch("custom_components.rilevatore_consumi.meter.dt_util", clk):
        yield clk


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Il recorder va avviato prima di hass."""
    return


async def _setup(hass: HomeAssistant, clock, reading: int = 5728):
    await hass.config.async_set_time_zone("Europe/Rome")
    clock.set("2026-10-27 12:00:00+01:00")
    entry = make_entry(reading)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _post(client, entry, body=CSV, commit=False, ct="text/csv"):
    return await client.post(
        f"/api/rilevatore_consumi/import/{entry.entry_id}?commit={int(commit)}",
        data=body,
        headers={"Content-Type": ct},
    )


async def _rows(hass: HomeAssistant, statistic_id: str) -> list[dict]:
    await async_wait_recording_done(hass)
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, dt_util.utc_from_timestamp(0), None,
        {statistic_id}, "hour", None, {"state", "sum"},
    )
    return result.get(statistic_id, [])


async def test_preview_changes_nothing(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """L'anteprima riassume il file e non salva nulla."""
    entry = await _setup(hass, clock)
    client = await hass_client()
    resp = await _post(client, entry)
    assert resp.status == 200
    data = await resp.json()
    assert data["count"] == 48
    assert data["total"] == 442
    assert data["first_value"] == 5285
    assert data["last_value"] == 5727
    assert data["current"] == 5728
    assert data["sets_current"] is False  # il file finisce prima dell'ultima lettura
    assert data["committed"] is False
    assert len(hass.states.get(SENSOR).attributes["recent_readings"]) == 1
    assert await _rows(hass, SENSOR) == []


async def test_commit_imports_history(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Dopo la conferma: letture, consumi dei periodi e statistiche per il grafico."""
    entry = await _setup(hass, clock)
    client = await hass_client()
    resp = await _post(client, entry, commit=True)
    assert resp.status == 200
    data = await resp.json()
    assert data["committed"] is True
    assert data["added"] == 48
    assert data["reading_updated"] is False
    assert data["statistics"]["imported_hours"] > 24 * 295

    state = hass.states.get(SENSOR)
    assert state.state == "5728"  # la lettura attuale resta quella più recente
    readings = state.attributes["recent_readings"]
    assert [r["v"] for r in readings][-2:] == [5727, 5728]
    assert hass.states.get("sensor.gas_consumption_this_year").state == "443"
    assert 8 <= int(hass.states.get("sensor.gas_consumption_this_month").state) <= 10
    assert hass.states.get("sensor.gas_consumption_today").state in ("0", "1")

    rows = await _rows(hass, SENSOR)
    assert rows[0]["sum"] <= 1
    assert round(rows[-1]["sum"]) == 442
    assert rows[-1]["state"] == 5727
    # il consumo di gennaio è ripartito sulle ore, non concentrato nei giorni di lettura
    jan = [r for r in rows if dt_util.utc_from_timestamp(r["start"] if isinstance(r["start"], (int, float)) else r["start"].timestamp()).month == 1]
    assert len(jan) > 24 * 28


async def test_commit_is_repeatable(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Importare due volte lo stesso file non duplica nulla."""
    entry = await _setup(hass, clock)
    client = await hass_client()
    await _post(client, entry, commit=True)
    first = len(await _rows(hass, SENSOR))
    resp = await _post(client, entry, commit=True)
    data = await resp.json()
    assert data["added"] == 0
    assert data["statistics"] == {"skipped": "already_present"}  # non è un errore
    assert len(entry.runtime_data.log) == 49  # nessun duplicato
    assert len(await _rows(hass, SENSOR)) == first


async def test_newer_readings_update_current(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Una lettura più recente nel file diventa la lettura attuale."""
    entry = await _setup(hass, clock, reading=5700)
    client = await hass_client()
    resp = await _post(client, entry, b"data;lettura\n27/10/2026 13:00;5750\n")
    assert (await resp.json())["sets_current"] is True
    clock.set("2026-10-27 14:00:00+01:00")
    await _post(client, entry, b"data;lettura\n27/10/2026 13:00;5750\n", commit=True)
    assert hass.states.get(SENSOR).state == "5750"


async def test_file_errors(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Errori chiari per file vuoti o illeggibili e per contatori inesistenti."""
    entry = await _setup(hass, clock)
    client = await hass_client()
    resp = await _post(client, entry, b"")
    assert resp.status == 400
    assert (await resp.json())["code"] == "empty"
    resp = await _post(client, entry, b"data,valore\nxx,yy\n")
    assert (await resp.json())["code"] == "no_readings"
    resp = await _post(client, entry, b"entity_id,state,last_changed\nsensor.a,1,2026-01-01\nsensor.b,2,2026-01-01\n")
    body = await resp.json()
    assert body["code"] == "multiple_entities"
    assert body["entities"] == ["sensor.a", "sensor.b"]
    resp = await client.post("/api/rilevatore_consumi/import/nope", data=CSV)
    assert resp.status == 404


async def test_requires_auth(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client_no_auth, clock
) -> None:
    entry = await _setup(hass, clock)
    client = await hass_client_no_auth()
    assert (await _post(client, entry)).status == 401


async def test_single_reading_sets_year_start(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Una sola riga al 1/1 basta per far tornare il consumo dell'anno."""
    entry = await _setup(hass, clock, reading=365)
    client = await hass_client()
    body = b"data;lettura\n01/01/2026;314\n"
    data = await (await _post(client, entry, body)).json()
    assert data["count"] == 1
    assert data["sets_current"] is False
    data = await (await _post(client, entry, body, commit=True)).json()
    assert data["committed"] is True
    assert hass.states.get(SENSOR).state == "365"  # la lettura attuale non cambia
    assert hass.states.get("sensor.gas_consumption_this_year").state == "51"
