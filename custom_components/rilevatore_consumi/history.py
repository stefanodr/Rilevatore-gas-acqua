"""Recupero dello storico: copia le statistiche di un vecchio sensore su uno nuovo."""

from __future__ import annotations

from datetime import UTC, datetime
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


def merge_rows(
    old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]
) -> list[StatisticData]:
    """Unisce lo storico vecchio e quello nuovo in un'unica serie continua.

    Le righe vecchie restano com'erano. Quelle nuove, che ripartivano da zero,
    vengono traslate in modo che la somma prosegua da dove finiva il vecchio
    sensore (il consumo tra l'ultima lettura vecchia e la prima nuova si somma;
    se il contatore è stato sostituito, cioè la lettura cala, non si somma).
    """
    cutoff = _ts(new_rows[0]["start"]) if new_rows else None
    kept = [row for row in old_rows if cutoff is None or _ts(row["start"]) < cutoff]
    if not kept:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="nothing_to_import"
        )

    merged: list[StatisticData] = []
    for row in kept:
        item = StatisticData(
            start=_ts(row["start"]), state=row["state"], sum=row["sum"]
        )
        if row.get("last_reset") is not None:
            item["last_reset"] = _ts(row["last_reset"])
        merged.append(item)

    if new_rows:
        last = kept[-1]
        first_new = new_rows[0]
        offset = (
            last["sum"]
            + max(0.0, first_new["state"] - last["state"])
            - first_new["sum"]
        )
        for row in new_rows:
            item = StatisticData(
                start=_ts(row["start"]),
                state=row["state"],
                sum=row["sum"] + offset,
            )
            if row.get("last_reset") is not None:
                item["last_reset"] = _ts(row["last_reset"])
            merged.append(item)
    return merged


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
    new_rows = await instance.async_add_executor_job(_fetch, hass, target_id)
    merged = merge_rows(old_rows, new_rows)

    metadata = StatisticMetaData(
        has_sum=True,
        mean_type=StatisticMeanType.NONE,
        name=name,
        source="recorder",
        statistic_id=target_id,
        unit_class=VolumeConverter.UNIT_CLASS,
        unit_of_measurement="m³",
    )
    async_import_statistics(hass, metadata, merged)
    await instance.async_block_till_done()
    return {
        "source": source_id,
        "target": target_id,
        "imported_hours": len(merged) - len(new_rows),
        "adjusted_hours": len(new_rows),
        "from": _ts(merged[0]["start"]).isoformat(),
    }
