"""Configurazione da interfaccia per Rilevatore consumi."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    CONF_AI_TASK,
    CONF_EXISTING,
    CONF_INITIAL,
    CONF_MAX_JUMP,
    CONF_TYPE,
    DEFAULT_MAX_JUMP,
    DOMAIN,
    MAX_READING,
    METER_TYPES,
    TYPE_GAS,
    TYPE_WATER,
)


def _state_to_int(hass: Any, entity_id: str) -> int | None:
    """Parte intera dello stato di un'entità, se è un numero."""
    state = hass.states.get(entity_id)
    if state is None:
        return None
    try:
        value = int(float(str(state.state).replace(",", ".")))
    except ValueError:
        return None
    return value if 0 <= value <= MAX_READING else None


class RilevatoreConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gestisce l'aggiunta di un contatore."""

    VERSION = 1

    def __init__(self) -> None:
        """Inizializza il flusso."""
        self._meter_type = TYPE_GAS

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Primo passo: gas o acqua."""
        if user_input is not None:
            self._meter_type = user_input[CONF_TYPE]
            return await self.async_step_details()
        schema = vol.Schema(
            {
                vol.Required(CONF_TYPE, default=TYPE_GAS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(METER_TYPES),
                        translation_key="meter_type",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    def _default_name(self) -> str:
        italian = self.hass.config.language.startswith("it")
        if self._meter_type == TYPE_WATER:
            return "Acqua" if italian else "Water"
        return "Gas"

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Secondo passo: nome e lettura iniziale (o sensore da sostituire)."""
        errors: dict[str, str] = {}
        meter_type = self._meter_type
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            existing = user_input.get(CONF_EXISTING)

            reading: int | None = None
            if existing:
                reading = _state_to_int(self.hass, existing)
            if user_input.get(CONF_INITIAL) is not None:
                reading = int(user_input[CONF_INITIAL])

            if not name:
                errors[CONF_NAME] = "name_required"
            elif reading is None:
                errors["base"] = "reading_required"
            else:
                await self.async_set_unique_id(f"{meter_type}_{slugify(name)}")
                self._abort_if_unique_id_configured()
                data: dict[str, Any] = {
                    CONF_NAME: name,
                    CONF_TYPE: meter_type,
                    CONF_INITIAL: reading,
                }
                if existing:
                    data[CONF_EXISTING] = existing
                return self.async_create_entry(title=name, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Optional(CONF_INITIAL): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=MAX_READING,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="m³",
                    )
                ),
                vol.Optional(CONF_EXISTING): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )
        suggested = user_input or {CONF_NAME: self._default_name()}
        return self.async_show_form(
            step_id="details",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RilevatoreOptionsFlow:
        """Opzioni: entità AI per la foto e salto massimo."""
        return RilevatoreOptionsFlow()


class RilevatoreOptionsFlow(OptionsFlow):
    """Opzioni di un contatore."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Mostra le opzioni."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        meter_type = self.config_entry.data[CONF_TYPE]
        schema = vol.Schema(
            {
                vol.Optional(CONF_AI_TASK): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="ai_task")
                ),
                vol.Required(
                    CONF_MAX_JUMP, default=DEFAULT_MAX_JUMP.get(meter_type, 300)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=MAX_READING,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="m³",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
        )
