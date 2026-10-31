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
from custom_components.rilevatore_consumi.history import merge_rows, rebuild_sums

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


def test_merge_keeps_existing_rows_untouched() -> None:
    """Le righe già presenti non cambiano; si spostano quelle importate."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    old = _hours(t0, [(5700.0, 10.0), (5710.0, 20.0), (5720.0, 30.0)])
    new = _hours(t0 + timedelta(hours=5), [(5726.0, 0.0), (5728.0, 2.0)])
    merged = merge_rows(old, new)
    # le righe esistenti sono identiche: il recorder prosegue da lì
    assert [round(m["sum"], 3) for m in merged[-2:]] == [0, 2]
    # le importate arrivano senza salti: +10 +10 e poi 6 m³ di lettura tra 5720 e 5726
    sums = [round(m["sum"], 3) for m in merged]
    assert [b - a for a, b in zip(sums, sums[1:])] == [10, 10, 6, 2]
    assert [m["state"] for m in merged] == [5700, 5710, 5720, 5726, 5728]


def test_merge_meter_replaced_not_added() -> None:
    """Se la lettura esistente è più bassa (contatore sostituito) il salto non si somma."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    old = _hours(t0, [(5700.0, 10.0)])
    new = _hours(t0 + timedelta(hours=3), [(10.0, 0.0), (12.0, 2.0)])
    merged = merge_rows(old, new)
    sums = [round(m["sum"], 3) for m in merged]
    assert sums[-2:] == [0, 2]
    assert sums[0] == sums[1]  # nessun consumo tra 5700 e 10


def test_rebuild_sums_removes_drop() -> None:
    """Somma ricaduta a un'ora (barra negativa): si ricalcola dalle letture."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    # 5 ore con somma gonfiata (+400), poi le righe vive ripartono dalla somma vera
    rows = _hours(
        t0,
        [(5000.0, 400.0), (5010.0, 410.0), (5020.0, 420.0), (5030.0, 430.0),
         (5040.0, 440.0), (5045.0, 45.0), (5050.0, 50.0)],
    )
    fixed = rebuild_sums(rows)
    sums = [m["sum"] for m in fixed]
    assert sums[-2:] == [45.0, 50.0]  # la riga più recente resta il riferimento
    gains = [round(b - a, 3) for a, b in zip(sums, sums[1:])]
    assert gains == [10, 10, 10, 10, 5, 5]
    assert all(g >= 0 for g in gains)


def test_rebuild_sums_meter_replaced() -> None:
    """Un calo di lettura (contatore sostituito) non conta come consumo."""
    t0 = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    rows = _hours(t0, [(5700.0, 100.0), (5710.0, 110.0), (3.0, 110.0), (5.0, 112.0)])
    sums = [m["sum"] for m in rebuild_sums(rows)]
    assert [round(b - a, 3) for a, b in zip(sums, sums[1:])] == [10, 0, 2]


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
    # la prima riga è l'àncora (un'ora prima, stessa somma della successiva)
    assert rows[0]["sum"] == rows[1]["sum"] == 0.0
    total_rows = len(rows)
    rows = rows[1:]
    assert rows[24 * 25 - 1]["sum"] == 24 * 25 - 1

    # ripetere non rovina nulla
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_history", {"source": OLD},
            target={"entity_id": NEW}, blocking=True, return_response=True,
        )
    assert len(await _rows(hass, NEW)) == total_rows


async def test_service_errors(recorder_mock: Recorder, hass: HomeAssistant) -> None:
    """Origine inesistente o uguale alla destinazione."""
    await _setup(hass)
    for source in ("sensor.non_esiste", NEW):
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "import_history", {"source": source},
                target={"entity_id": NEW}, blocking=True, return_response=True,
            )


async def test_service_keeps_existing_rows(
    recorder_mock: Recorder, hass: HomeAssistant
) -> None:
    """Le ore già registrate dal sensore nuovo restano com'erano; si sposta il vecchio storico."""
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
    # le 5 righe esistenti sono identiche a prima (0, 1, 2, 3, 4)
    assert sums[-5:] == [0.0, 1.0, 2.0, 3.0, 4.0]
    # tra l'ultima ora vecchia (5047) e la prima esistente (5060) ci sono 13 m³
    # (sums[0] è l'àncora in testa, le ore vecchie vanno da sums[1] a sums[48])
    assert sums[-5] - sums[48] == 13.0
    # le vecchie mantengono i loro incrementi
    assert sums[48] - sums[1] == 47.0


async def test_repair_service_fixes_negative_bar(
    recorder_mock: Recorder, hass: HomeAssistant
) -> None:
    """Il tuo caso: righe importate con somma più alta delle righe vive."""
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    t0 = now - timedelta(days=20)
    rows = []
    for i in range(0, 24 * 15):  # importate, somma gonfiata di 400
        rows.append({"start": t0 + timedelta(hours=i), "state": 5000.0 + i / 10,
                     "sum": 400.0 + i / 10})
    base = 5000.0 + (24 * 15) / 10
    for j in range(0, 24 * 4):  # vive: ripartono dalla somma vera
        rows.append({"start": t0 + timedelta(hours=24 * 15 + j),
                     "state": base + j / 10, "sum": 20.0 + j / 10})
    async_import_statistics(hass, _meta(NEW), rows)
    await async_wait_recording_done(hass)
    await _setup(hass)

    before = await _rows(hass, NEW)
    assert min(b["sum"] - a["sum"] for a, b in zip(before, before[1:])) < -300

    response = await hass.services.async_call(
        DOMAIN, "repair_statistics", {},
        target={"entity_id": NEW}, blocking=True, return_response=True,
    )
    assert response[NEW]["hours_fixed"] == 24 * 15
    after = await _rows(hass, NEW)
    gains = [b["sum"] - a["sum"] for a, b in zip(after, after[1:])]
    assert min(gains) >= -1e-6
    assert round(after[-1]["sum"], 3) == round(rows[-1]["sum"], 3)  # riferimento intatto

    again = await hass.services.async_call(
        DOMAIN, "repair_statistics", {},
        target={"entity_id": NEW}, blocking=True, return_response=True,
    )
    assert again[NEW]["hours_fixed"] == 0  # ripetibile


async def test_first_month_change_is_right_after_repair(
    recorder_mock: Recorder, hass: HomeAssistant
) -> None:
    """Il primo mese dell'intervallo (come lo calcola Energia) non esce negativo."""
    from homeassistant.components.recorder.statistics import statistics_during_period

    await hass.config.async_set_time_zone("Europe/Rome")
    first = dt_util.as_utc(dt_util.parse_datetime("2026-01-01T00:00:00+01:00"))
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    hours = int((now - first).total_seconds() // 3600)
    rows = []
    for i in range(hours):  # 1 m³ ogni 10 ore, somma gonfiata di 400 fino a metà
        total = i / 10
        rows.append({"start": first + timedelta(hours=i), "state": 5000.0 + total,
                     "sum": total + (400.0 if i < hours // 2 else 0.0)})
    async_import_statistics(hass, _meta(NEW), rows)
    await async_wait_recording_done(hass)
    await _setup(hass)

    await hass.services.async_call(
        DOMAIN, "repair_statistics", {},
        target={"entity_id": NEW}, blocking=True, return_response=True,
    )
    await async_wait_recording_done(hass)
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, first, None, {NEW}, "month", None, {"change"}
    )
    changes = [round(r["change"], 1) for r in result[NEW]]
    assert changes[0] == round((31 * 24 - 1) / 10, 1)  # gennaio: 74,3 m³ (fino all'ultima ora)
    assert all(c > 0 for c in changes[:-1])
    assert round(sum(changes), 1) == round((hours - 1) / 10, 1)

    # ripetere non aggiunge altre righe di àncora
    count = len(await _rows(hass, NEW))
    await hass.services.async_call(
        DOMAIN, "repair_statistics", {},
        target={"entity_id": NEW}, blocking=True, return_response=True,
    )
    assert len(await _rows(hass, NEW)) == count
