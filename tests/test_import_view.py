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
    year = hass.states.get("sensor.gas_consumption_this_year")
    assert year.state == "51"
    assert year.attributes["partial"] is False  # ora l'inizio anno è noto


async def test_water_scenario_history_then_january_row(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Storico solo da marzo copiato dal vecchio sensore, poi lettura al 1/1."""
    from datetime import timedelta

    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_import_statistics

    entry = await _setup(hass, clock, reading=368)
    start = dt_util.as_utc(dt_util.parse_datetime("2026-03-01T00:00:00+01:00"))
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    rows, hour = [], start
    while hour < now:
        state = 361 + int((hour - start).total_seconds() // 3600 // 24 // 30 * 1)
        rows.append({"start": hour, "state": float(min(state, 368)),
                     "sum": float(min(state, 368) - 361)})
        hour += timedelta(hours=1)
    meta = {"has_sum": True, "mean_type": StatisticMeanType.NONE, "name": None,
            "source": "recorder", "statistic_id": "sensor.vecchia_acqua",
            "unit_class": "volume", "unit_of_measurement": "m³"}
    async_import_statistics(hass, meta, rows)
    await async_wait_recording_done(hass)

    await hass.services.async_call(
        "rilevatore_consumi", "import_history", {"source": "sensor.vecchia_acqua"},
        target={"entity_id": SENSOR}, blocking=True, return_response=True,
    )
    await hass.async_block_till_done()
    year = hass.states.get("sensor.gas_consumption_this_year")

    client = await hass_client()
    body = b"data;lettura\n01/01/2026;351\n"
    resp = await _post(client, entry, body, commit=True)
    assert (await resp.json())["committed"] is True
    year = hass.states.get("sensor.gas_consumption_this_year")
    assert year.state == "17"
    assert year.attributes["partial"] is False


async def test_import_after_reset_covers_all_years(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Dopo reset_history un file dal 2022 riempie tutti gli anni, non solo l'ultimo."""
    from custom_components.rilevatore_consumi.const import DOMAIN  # noqa: PLC0415

    entry = await _setup(hass, clock, reading=5800)
    await hass.services.async_call(
        DOMAIN, "reset_history", {"confirm": True},
        target={"entity_id": SENSOR}, blocking=True,
    )
    lines = ["data;lettura"]
    value = 4000
    for year in range(2022, 2027):
        for month in range(1, 13):
            if (year, month) > (2026, 10):
                break
            lines.append(f"01/{month:02d}/{year};{value}")
            value += 40
    client = await hass_client()
    resp = await _post(client, entry, "\n".join(lines).encode(), commit=True)
    assert resp.status == 200
    data = await resp.json()
    rows = await _rows(hass, SENSOR)
    first = dt_util.utc_from_timestamp(
        rows[0]["start"] if isinstance(rows[0]["start"], (int, float)) else rows[0]["start"].timestamp()
    )
    assert "error" not in data["statistics"]
    # la prima riga è quella di riferimento, un'ora prima del 1° gennaio 2022
    local_first = dt_util.as_local(first)
    assert local_first.year == 2021 and (local_first.month, local_first.day) == (12, 31)
    assert dt_util.as_local(rows[1]["start"] if not isinstance(rows[1]["start"], (int, float)) else dt_util.utc_from_timestamp(rows[1]["start"])).year == 2022
    assert len(rows) > 24 * 365 * 4


async def test_import_with_replace_discards_existing_data(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Con replace=1 i dati esistenti spariscono e si riparte dal file."""
    entry = await _setup(hass, clock, reading=5728)
    client = await hass_client()
    wrong = b"data;lettura\n01/10/2026;5200\n20/10/2026;5300\n"
    resp = await client.post(
        f"/api/rilevatore_consumi/import/{entry.entry_id}?commit=1",
        data=wrong, headers={"Content-Type": "text/csv"},
    )
    assert resp.status == 200
    assert len(await _rows(hass, SENSOR)) > 0

    right = b"data;lettura\n01/10/2026;4000\n20/10/2026;4100\n"
    resp = await client.post(
        f"/api/rilevatore_consumi/import/{entry.entry_id}?commit=1&replace=1",
        data=right, headers={"Content-Type": "text/csv"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["replaced"] is True
    meter = entry.runtime_data
    assert meter.reading == 4100
    assert [item["v"] for item in meter.log] == [4000, 4100]
    rows = await _rows(hass, SENSOR)
    assert rows and max(float(r["state"]) for r in rows) <= 4100.0 + 1e-6
    assert min(float(r["state"]) for r in rows) >= 4000.0 - 1e-6


def _csv(start_value: int, years: int = 2) -> bytes:
    """CSV mensile di prova: una lettura al mese a partire dal 2024."""
    lines = ["data;lettura"]
    value = start_value
    for y in range(2024, 2024 + years):
        for m in range(1, 13):
            lines.append(f"01/{m:02d}/{y};{value}")
            value += 5
    return ("\n".join(lines) + "\n").encode()


async def _two_meters(hass, clock):
    await hass.config.async_set_time_zone("Europe/Rome")
    clock.set("2026-10-27 12:00:00+01:00")
    gas = make_entry(5728, "gas", "Gas")
    water = make_entry(364, "water", "Acqua")
    for e in (gas, water):
        e.add_to_hass(hass)
        assert await hass.config_entries.async_setup(e.entry_id)
    await hass.async_block_till_done()
    return gas, water


async def test_two_meters_imported_at_the_same_time(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Importare acqua e gas insieme, senza aspettare, non si disturba a vicenda."""
    import asyncio  # noqa: PLC0415

    gas, water = await _two_meters(hass, clock)
    client = await hass_client()
    r_gas, r_water = await asyncio.gather(
        _post(client, gas, _csv(1000), commit=True),
        _post(client, water, _csv(10), commit=True),
    )
    assert r_gas.status == 200 and r_water.status == 200
    gas_rows = await _rows(hass, "sensor.gas_meter_reading")
    water_rows = await _rows(hass, "sensor.acqua_meter_reading")
    assert gas_rows and water_rows
    # nessuna mescolanza: ogni contatore ha solo i propri valori
    assert max(float(r["state"]) for r in gas_rows) <= 1000 + 24 * 5
    assert min(float(r["state"]) for r in gas_rows) >= 1000
    assert max(float(r["state"]) for r in water_rows) <= 10 + 24 * 5
    assert min(float(r["state"]) for r in water_rows) >= 10
    assert len(gas_rows) == len(water_rows)


async def test_second_import_of_the_same_meter_is_refused(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Due importazioni insieme sullo stesso contatore: la seconda viene rifiutata."""
    entry = await _setup(hass, clock)
    client = await hass_client()
    entry.runtime_data.import_running = True
    resp = await _post(client, entry, _csv(100), commit=True)
    assert resp.status == 409
    assert (await resp.json())["code"] == "import_running"
    # l'anteprima resta sempre possibile
    assert (await _post(client, entry, _csv(100))).status == 200
    entry.runtime_data.import_running = False
    assert (await _post(client, entry, _csv(100), commit=True)).status == 200
    assert entry.runtime_data.import_running is False


async def test_interrupted_import_keeps_recent_months_and_can_be_completed(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Un'interruzione lascia i mesi più recenti; una nuova importazione completa il resto."""
    from custom_components.rilevatore_consumi import history as H  # noqa: PLC0415

    entry = await _setup(hass, clock)
    client = await hass_client()
    body = _csv(100, years=2)
    real = H.async_import_statistics
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] > 8:
            raise RuntimeError("interrotto")
        return real(*args, **kwargs)

    with patch.object(H, "async_import_statistics", flaky):
        resp = await _post(client, entry, body, commit=True)
    assert resp.status == 500
    partial = await _rows(hass, SENSOR)
    assert 0 < len(partial)
    last_partial = partial[-1]["start"]

    # la parte più recente è presente; riprovando si completa la più vecchia
    resp = await _post(client, entry, body, commit=True)
    assert resp.status == 200
    full = await _rows(hass, SENSOR)
    assert len(full) > len(partial)
    assert full[-1]["start"] == last_partial
    sums = [float(r["sum"]) for r in full]
    assert sums == sorted(sums)  # continuo, senza salti all'indietro


async def test_import_creates_a_notification(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """A fine importazione compare un avviso in Home Assistant."""
    entry = await _setup(hass, clock)
    client = await hass_client()
    resp = await _post(client, entry, _csv(100), commit=True)
    assert resp.status == 200
    notifications = hass.data.get("persistent_notification", {})
    assert any("Rilevatore consumi" in str(n) for n in notifications.values())


async def test_import_repairs_a_jump_in_the_sums(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Se dopo l'importazione le somme hanno un salto all'indietro, vengono riparate."""
    from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
        async_import_statistics,
    )

    from .test_history import _meta  # noqa: PLC0415

    entry = await _setup(hass, clock)
    client = await hass_client()
    assert (await _post(client, entry, _csv(100), commit=True)).status == 200
    rows = await _rows(hass, SENSOR)
    last = rows[-1]
    t0 = dt_util.utc_from_timestamp(last["start"]) + __import__("datetime").timedelta(hours=100)
    state = float(last["state"])
    # righe scritte "dal vivo" con la somma ripartita molto più in basso: salto all'indietro
    live = [
        {"start": t0 + __import__("datetime").timedelta(hours=i), "state": state, "sum": 3.0}
        for i in range(5)
    ]
    async_import_statistics(hass, _meta(SENSOR), live)
    await async_wait_recording_done(hass)
    before = [float(r["sum"]) for r in await _rows(hass, SENSOR)]
    assert before != sorted(before)

    resp = await _post(client, entry, _csv(100), commit=True)
    assert resp.status == 200
    data = await resp.json()
    assert data["statistics"]["sums_fixed"] > 0
    after = [float(r["sum"]) for r in await _rows(hass, SENSOR)]
    assert after == sorted(after)


async def test_import_continues_when_the_request_is_cancelled(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Pagina chiusa a metà: l'importazione prosegue e termina comunque."""
    import asyncio  # noqa: PLC0415

    from custom_components.rilevatore_consumi import history as H  # noqa: PLC0415

    entry = await _setup(hass, clock)
    client = await hass_client()
    meter = entry.runtime_data
    gate = asyncio.Event()
    started = asyncio.Event()
    real = H.async_write_history

    async def slow(*args, **kwargs):
        started.set()
        await gate.wait()
        return await real(*args, **kwargs)

    with patch.object(H, "async_write_history", slow):
        request = asyncio.ensure_future(_post(client, entry, _csv(100), commit=True))
        await asyncio.wait_for(started.wait(), 10)
        assert meter.import_running is True
        request.cancel()  # come una pagina che si chiude o si ricarica
        await asyncio.gather(request, return_exceptions=True)
        assert meter.import_running is True  # il lavoro non è stato interrotto
        gate.set()
        for _ in range(1200):
            if not meter.import_running:
                break
            await asyncio.sleep(0.05)
    assert meter.import_running is False
    assert len(await _rows(hass, SENSOR)) > 0
    notifications = hass.data.get("persistent_notification", {})
    assert any("importate" in str(n) or "imported" in str(n) for n in notifications.values())


async def test_reset_without_reading_takes_current_from_next_import(
    recorder_mock: Recorder, hass: HomeAssistant, hass_client, clock
) -> None:
    """Azzeramento senza `reading`: la lettura attuale arriva dal file importato dopo."""
    from custom_components.rilevatore_consumi.const import DOMAIN  # noqa: PLC0415

    entry = await _setup(hass, clock, reading=9000)  # lettura attuale errata, alta
    client = await hass_client()
    meter = entry.runtime_data
    await hass.services.async_call(
        DOMAIN, "reset_history", {"confirm": True},
        target={"entity_id": SENSOR}, blocking=True,
    )
    assert meter.reading == 9000 and meter.log == []
    resp = await _post(client, entry, _csv(100), commit=True)
    assert resp.status == 200
    assert meter.reading == 100 + 5 * 23  # ultima riga del file
    assert meter.adopt_import is False
    # un secondo file con una lettura più bassa non cambia più la lettura attuale
    await _post(client, entry, _csv(50), commit=True)
    assert meter.reading == 100 + 5 * 23
