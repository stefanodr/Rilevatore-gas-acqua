"""Costanti per Rilevatore consumi gas/acqua."""

from __future__ import annotations

DOMAIN = "rilevatore_consumi"
VERSION = "2.0.0"

CONF_TYPE = "meter_type"
CONF_EXISTING = "existing_entity"
CONF_INITIAL = "initial_reading"
CONF_AI_TASK = "ai_task_entity"
CONF_MAX_JUMP = "max_jump"

TYPE_GAS = "gas"
TYPE_WATER = "water"
METER_TYPES = (TYPE_GAS, TYPE_WATER)

# Salto massimo (m³) rispetto all'ultima lettura oltre il quale serve una conferma esplicita
DEFAULT_MAX_JUMP = {TYPE_GAS: 300, TYPE_WATER: 100}

MAX_READING = 99_999_999
PERIODS = ("day", "month", "year")

STORAGE_VERSION = 1
MAX_PHOTO_BYTES = 10 * 1024 * 1024

URL_BASE = "/rilevatore_consumi_static"
CARD_FILE = "rilevatore-consumi-card.js"

ATTR_READING = "reading"
ATTR_FORCE = "force"
ATTR_REPLACE = "replace_meter"
ATTR_MEDIA = "media"
