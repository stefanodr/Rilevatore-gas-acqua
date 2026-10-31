"""Recupero dello storico: copia le statistiche di un vecchio sensore su uno nuovo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .const import DOMAIN

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
TYPES = {"state", "sum", "last_reset"}


def _ts(value: Any) -> datetime:
    """Converte un istante (timestamp o datetime) in datetime UTC."""
    if isinstance(value, datetime):
        return dt_util.as_utc(value)
    return dt_util.utc_from_timestamp(float(value))


def _fetch(hass: HomeAssistant, statistic_id: str) -> list[dict[str, Any]]:
    """Statistiche orarie (da eseguire nel thread del recorder)."""
    result = statistics_during_period(
        hass, EPOCH, None, {statistic_id}, "hour", None, TYPES
    )
    return [
        row
        for row in result.get(statistic_id, [])
        if row.get("sum") is not None and row.get("state") is not None
    ]


def _item(row: dict[str, Any], sum_value: float) -> StatisticData:
    item = StatisticData(
        start=_ts(row["start"]), state=row["state"], sum=round(sum_value, 3)
    )
    if row.get("last_reset") is not None:
        item["last_reset"] = _ts(row["last_reset"])
    return item


def merge_rows(
    old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]
) -> list[StatisticData]:
    """Unisce lo storico importato con quello già presente in un'unica serie continua.

    Le righe già presenti NON si toccano: il recorder continua a produrre quelle
    nuove a partire dalle proprie statistiche a 5 minuti, quindi la loro somma
    non deve cambiare, altrimenti alla prima ora nuova la somma ricadrebbe e la
    plancia Energia mostrerebbe un consumo negativo. Si spostano invece le righe
    importate (precedenti), in modo che la somma arrivi senza salti alla prima
    riga esistente. Il consumo tra l'ultima lettura importata e la prima
    esistente si somma; se la lettura cala (contatore sostituito) non si somma.
    """
    cutoff = _ts(new_rows[0]["start"]) if new_rows else None
    kept = [row for row in old_rows if cutoff is None or _ts(row["start"]) < cutoff]
    if not kept:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="nothing_to_import"
        )

    delta = 0.0
    if new_rows:
        last = kept[-1]
        first_new = new_rows[0]
        gap = max(0.0, first_new["state"] - last["state"])
        delta = first_new["sum"] - (last["sum"] + gap)

    merged = [_item(row, row["sum"] + delta) for row in kept]
    merged.extend(_item(row, row["sum"]) for row in new_rows)
    return merged


def rebuild_sums(rows: list[dict[str, Any]]) -> list[StatisticData]:
    """Ricalcola le somme dalle letture, partendo dalla riga più recente.

    La riga più recente è quella che il recorder sta già continuando: la si
    tiene com'è e si risale all'indietro. Ogni ora precedente vale la successiva
    meno l'aumento di lettura tra le due (un calo, cioè un contatore sostituito,
    non conta).
    """
    result: list[StatisticData] = [None] * len(rows)  # type: ignore[list-item]
    current = float(rows[-1]["sum"])
    result[-1] = _item(rows[-1], current)
    for i in range(len(rows) - 2, -1, -1):
        current -= max(0.0, rows[i + 1]["state"] - rows[i]["state"])
        result[i] = _item(rows[i], current)
    return result


async def async_repair_sums(
    hass: HomeAssistant, target_id: str, name: str | None = None
) -> dict[str, Any]:
    """Rimette in continuità le somme dello storico di target_id."""
    instance = get_instance(hass)
    await instance.async_block_till_done()
    rows = await instance.async_add_executor_job(_fetch, hass, target_id)
    if not rows:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_history",
            translation_placeholders={"source": target_id},
        )
    fixed = rebuild_sums(rows)
    changed = sum(
        1 for old, new in zip(rows, fixed) if abs(float(old["sum"]) - new["sum"]) > 0.01
    )
    if changed:
        async_import_statistics(hass, _metadata(target_id, name), fixed)
        await instance.async_block_till_done()
    return {"target": target_id, "hours": len(rows), "hours_fixed": changed}


def _metadata(target_id: str, name: str | None) -> StatisticMetaData:
    return StatisticMetaData(
        has_sum=True,
        mean_type=StatisticMeanType.NONE,
        name=name,
        source="recorder",
        statistic_id=target_id,
        unit_class=VolumeConverter.UNIT_CLASS,
        unit_of_measurement="m³",
    )


async def async_import_history(
    hass: HomeAssistant, target_id: str, source_id: str, name: str | None = None
) -> dict[str, Any]:
    """Copia lo storico di source_id su target_id e restituisce un riepilogo."""
    if source_id == target_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="same_source"
        )
    instance = get_instance(hass)
    await instance.async_block_till_done()
    old_rows = await instance.async_add_executor_job(_fetch, hass, source_id)
    if not old_rows:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_history",
            translation_placeholders={"source": source_id},
        )
    result = await async_write_history(hass, target_id, old_rows, name)
    result["source"] = source_id
    return result


async def async_write_history(
    hass: HomeAssistant,
    target_id: str,
    old_rows: list[dict[str, Any]],
    name: str | None = None,
) -> dict[str, Any]:
    """Scrive old_rows come storico di target_id, prima di quello già presente."""
    instance = get_instance(hass)
    await instance.async_block_till_done()
    new_rows = await instance.async_add_executor_job(_fetch, hass, target_id)
    merged = merge_rows(old_rows, new_rows)

    metadata = _metadata(target_id, name)
    async_import_statistics(hass, metadata, merged)
    await instance.async_block_till_done()
    return {
        "target": target_id,
        "imported_hours": len(merged) - len(new_rows),
        "adjusted_hours": len(new_rows),
        "from": _ts(merged[0]["start"]).isoformat(),
    }


def _state_before(
    hass: HomeAssistant, statistic_id: str, when: datetime
) -> float | None:
    """Lettura a fine dell'ora che precede `when` (thread del recorder)."""
    result = statistics_during_period(
        hass,
        when - timedelta(hours=2),
        when,
        {statistic_id},
        "hour",
        None,
        {"state"},
    )
    rows = [
        row
        for row in result.get(statistic_id, [])
        if row.get("state") is not None and _ts(row["start"]) < dt_util.as_utc(when)
    ]
    if not rows:
        return None
    return float(max(rows, key=lambda r: _ts(r["start"]))["state"])


async def async_state_at(
    hass: HomeAssistant, statistic_id: str, when: datetime
) -> float | None:
    """Lettura del sensore a un certo istante, dalle statistiche (o None)."""
    instance = get_instance(hass)
    await instance.async_block_till_done()
    return await instance.async_add_executor_job(
        _state_before, hass, statistic_id, when
    )
