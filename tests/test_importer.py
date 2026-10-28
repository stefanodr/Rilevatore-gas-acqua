"""Test della lettura di file CSV con le letture."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from custom_components.rilevatore_consumi.importer import (
    ImportFileError,
    hourly_rows,
    parse_number,
    parse_readings,
    value_at,
)

DATA = Path(__file__).parent / "data" / "history_gas.csv"


def test_home_assistant_export() -> None:
    """L'export della cronologia di HA: righe doppie e ".0" si riducono a una lettura."""
    parsed = parse_readings(DATA.read_text(), ("sensor.gas_consumption",))
    assert len(parsed.readings) == 48
    assert parsed.readings[0][1] == 5285
    assert parsed.readings[-1][1] == 5727
    assert parsed.total == 442
    assert parsed.decreases == 0
    assert parsed.ignored_rows == 0
    assert parsed.entity_id == "sensor.gas_consumption"
    assert [t for t, _ in parsed.readings] == sorted(t for t, _ in parsed.readings)
    # la prima riga è la mezzanotte italiana del 1 gennaio
    assert parsed.readings[0][0] == datetime(2025, 12, 31, 23, 0, tzinfo=UTC)


def test_italian_semicolon_file() -> None:
    """Separatore ;, date gg/mm/aaaa, numeri con punto delle migliaia e virgola."""
    text = "Data;Lettura\n01/01/2026;5.285\n08/01/2026 09:30;5.312,4\n15/01/2026;unknown\n"
    parsed = parse_readings(text)
    assert [v for _, v in parsed.readings] == [5285, 5312]
    assert parsed.ignored_rows == 1
    assert parsed.readings[1][0].hour == 9


def test_headerless_two_columns() -> None:
    """Senza intestazione: data e lettura."""
    parsed = parse_readings("2026-03-01,100\n2026-03-08,110\n")
    assert [v for _, v in parsed.readings] == [100, 110]


def test_unsorted_and_decreasing() -> None:
    """Le righe si ordinano; una lettura che cala (contatore sostituito) si segnala."""
    parsed = parse_readings("data,valore\n2026-02-01,5\n2026-01-01,100\n2026-03-01,20\n")
    assert [v for _, v in parsed.readings] == [100, 5, 20]
    assert parsed.decreases == 1
    assert parsed.total == 15  # 5 -> 20, il calo non si somma


def test_multiple_entities() -> None:
    """Con più entità serve sceglierne una."""
    text = (
        "entity_id,state,last_changed\n"
        "sensor.a,1,2026-01-01T00:00:00Z\nsensor.b,9,2026-01-01T00:00:00Z\n"
        "sensor.a,2,2026-01-02T00:00:00Z\n"
    )
    with pytest.raises(ImportFileError) as err:
        parse_readings(text)
    assert err.value.code == "multiple_entities"
    assert err.value.extra["entities"] == ["sensor.a", "sensor.b"]
    parsed = parse_readings(text, ("sensor.zzz", "sensor.a"))
    assert [v for _, v in parsed.readings] == [1, 2]


@pytest.mark.parametrize("text", ["", "   \n", "﻿"])
def test_empty(text) -> None:
    with pytest.raises(ImportFileError) as err:
        parse_readings(text)
    assert err.value.code == "empty"


def test_no_readable_rows() -> None:
    with pytest.raises(ImportFileError) as err:
        parse_readings("data,valore\nnon una data,abc\n")
    assert err.value.code == "no_readings"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5724", 5724), ("5724.0", 5724), ("5724,9", 5724), ("5.724", 5724),
        ("1,234,567", 1234567), ("1.234,5", 1234), (" 12 ", 12),
        ("unknown", None), ("", None), ("abc", None), ("-3", None), ("1e12", None),
    ],
)
def test_parse_number(raw, expected) -> None:
    assert parse_number(raw) == expected


def test_value_at_and_hourly_rows() -> None:
    """Il consumo tra due letture si ripartisce in modo uniforme sulle ore."""
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    readings = [(t0, 100), (t0 + timedelta(hours=24), 124), (t0 + timedelta(hours=30), 10)]
    assert value_at(readings, t0 + timedelta(hours=12)) == 112
    assert value_at(readings, t0 + timedelta(hours=27)) == 124  # contatore calato: resta fermo
    rows = hourly_rows(readings)
    assert rows[0] == {"start": t0, "state": 101.0, "sum": 1.0}
    assert rows[23]["sum"] == 24.0
    assert rows[-1]["start"] == t0 + timedelta(hours=30)
    assert rows[-1]["state"] == 10.0
    assert rows[-1]["sum"] == 24.0  # il calo non si somma
