"""Lettura di un file CSV di letture e conversione in statistiche orarie."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import io
import re

from homeassistant.util import dt as dt_util

from .const import MAX_READING

TIME_COLUMNS = (
    "last_changed", "last_updated", "datetime", "timestamp", "time",
    "date", "data", "data/ora", "data e ora", "ora", "quando",
)
VALUE_COLUMNS = ("state", "value", "valore", "lettura", "reading", "stato")
ENTITY_COLUMNS = ("entity_id", "entita", "entità", "entity")
BAD_STATES = {"", "unknown", "unavailable", "none", "null", "nan", "n.d.", "-"}
DATE_FORMATS = (
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
    "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
)
MAX_FILE_BYTES = 2 * 1024 * 1024


class ImportFileError(Exception):
    """File non utilizzabile; `code` è una chiave che la card traduce."""

    def __init__(self, code: str, **extra: object) -> None:
        super().__init__(code)
        self.code = code
        self.extra = extra


@dataclass
class ParsedReadings:
    """Risultato della lettura del file."""

    readings: list[tuple[datetime, int]]  # (istante, m³ interi), ordinati
    ignored_rows: int = 0
    duplicates: int = 0
    decreases: int = 0
    entity_id: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Consumo complessivo (le diminuzioni non si sommano)."""
        total = 0
        for (_, a), (_, b) in zip(self.readings, self.readings[1:]):
            total += max(0, b - a)
        return total


def parse_number(raw: str) -> int | None:
    """Parte intera di un numero scritto all'italiana o all'inglese."""
    text = raw.strip().replace(" ", "").replace(" ", "")
    if text.lower() in BAD_STATES:
        return None
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif re.fullmatch(r"\d{1,3}([.,]\d{3})+", text):  # 5.724 / 1,234,567
        text = re.sub(r"[.,]", "", text)
    else:
        text = text.replace(",", ".")
    try:
        number = int(float(text))
    except ValueError:
        return None
    return number if 0 <= number <= MAX_READING else None


def parse_time(raw: str) -> datetime | None:
    """Data e ora in ISO, o gg/mm/aaaa [hh:mm[:ss]] (ora locale se senza fuso)."""
    text = raw.strip().strip('"')
    if not text:
        return None
    parsed = dt_util.parse_datetime(text.replace("Z", "+00:00"))
    if parsed is None:
        for fmt in DATE_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt)  # noqa: DTZ007
                break
            except ValueError:
                continue
    if parsed is None:
        parsed_date = dt_util.parse_date(text)
        if parsed_date is not None:
            parsed = datetime(parsed_date.year, parsed_date.month, parsed_date.day)  # noqa: DTZ001
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_local(parsed)


def _find(header: list[str], names: tuple[str, ...]) -> int | None:
    for name in names:
        if name in header:
            return header.index(name)
    return None


def parse_readings(text: str, prefer_entities: tuple[str, ...] = ()) -> ParsedReadings:
    """Legge un CSV (export della cronologia di HA o semplice data;lettura)."""
    text = text.lstrip("﻿")
    if not text.strip():
        raise ImportFileError("empty")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]
    if not rows:
        raise ImportFileError("empty")

    header = [c.strip().lower() for c in rows[0]]
    t_idx = _find(header, TIME_COLUMNS)
    v_idx = _find(header, VALUE_COLUMNS)
    e_idx = _find(header, ENTITY_COLUMNS)
    if t_idx is not None and v_idx is not None:
        body = rows[1:]
    else:  # senza intestazione: data, lettura
        t_idx, v_idx, e_idx = 0, 1, None
        body = rows

    entities = sorted({r[e_idx].strip() for r in body if e_idx is not None and len(r) > e_idx})
    chosen: str | None = None
    if len(entities) > 1:
        for wanted in prefer_entities:
            if wanted in entities:
                chosen = wanted
                break
        if chosen is None:
            raise ImportFileError("multiple_entities", entities=entities[:10])
    elif entities:
        chosen = entities[0]

    points: list[tuple[datetime, int]] = []
    ignored = 0
    for row in body:
        if len(row) <= max(t_idx, v_idx):
            ignored += 1
            continue
        if chosen and e_idx is not None and row[e_idx].strip() != chosen:
            continue
        when = parse_time(row[t_idx])
        value = parse_number(row[v_idx])
        if when is None or value is None:
            ignored += 1
            continue
        points.append((when, value))

    if not points:
        raise ImportFileError("no_readings")
    points.sort(key=lambda p: p[0])

    readings: list[tuple[datetime, int]] = []
    duplicates = 0
    for when, value in points:
        if readings and readings[-1][1] == value:
            duplicates += 1  # stessa lettura ripetuta: si tiene la prima
            continue
        if readings and readings[-1][0] == when:
            readings[-1] = (when, value)
            continue
        readings.append((when, value))

    decreases = sum(1 for a, b in zip(readings, readings[1:]) if b[1] < a[1])
    return ParsedReadings(
        readings=readings,
        ignored_rows=ignored,
        duplicates=duplicates,
        decreases=decreases,
        entity_id=chosen,
    )


def value_at(readings: list[tuple[datetime, int]], when: datetime) -> float:
    """Lettura stimata in un istante (lineare tra due letture; salto se il contatore cala)."""
    if when <= readings[0][0]:
        return float(readings[0][1])
    if when >= readings[-1][0]:
        return float(readings[-1][1])
    for (t0, v0), (t1, v1) in zip(readings, readings[1:]):
        if t0 <= when < t1:
            if v1 < v0:
                return float(v0)
            return v0 + (v1 - v0) * (when - t0) / (t1 - t0)
    return float(readings[-1][1])  # pragma: no cover


def hourly_rows(readings: list[tuple[datetime, int]]) -> list[dict]:
    """Righe orarie (start, state, sum) con il consumo ripartito tra le letture."""
    first = dt_util.as_utc(readings[0][0]).replace(minute=0, second=0, microsecond=0)
    last = dt_util.as_utc(readings[-1][0]).replace(minute=0, second=0, microsecond=0)
    rows: list[dict] = []
    previous = float(readings[0][1])
    total = 0.0
    hour = first
    while hour <= last:
        state = value_at(readings, hour + timedelta(hours=1))
        total += max(0.0, state - previous)
        rows.append({"start": hour, "state": round(state, 3), "sum": round(total, 3)})
        previous = state
        hour += timedelta(hours=1)
    return rows
