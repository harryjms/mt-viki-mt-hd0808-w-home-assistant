"""Config and options flow for the MT-VIKI matrix integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_HOST,
    CONF_INPUT_NAMES,
    CONF_OUTPUT_NAMES,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INPUTS,
    OUTPUTS,
)
from .helpers import default_input_names, default_output_names
from .matrix import MatrixClient, MatrixError


class MtVikiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect host and port, and verify connectivity."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            client = MatrixClient(host, port, OUTPUTS, INPUTS)
            try:
                await client.async_test_connection()
            except MatrixError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"MT-VIKI Matrix ({host})", data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return MtVikiOptionsFlow()


class MtVikiOptionsFlow(OptionsFlow):
    """Handle naming of inputs/outputs and the poll interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Present the options form."""
        options = self.config_entry.options

        if user_input is not None:
            data = {
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                CONF_INPUT_NAMES: [
                    user_input[f"input_{i}"] for i in range(1, INPUTS + 1)
                ],
                CONF_OUTPUT_NAMES: [
                    user_input[f"output_{o}"] for o in range(1, OUTPUTS + 1)
                ],
            }
            return self.async_create_entry(title="", data=data)

        current_inputs = options.get(CONF_INPUT_NAMES) or default_input_names()
        current_outputs = options.get(CONF_OUTPUT_NAMES) or default_output_names()

        fields: dict[Any, Any] = {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=5, max=3600)),
        }
        for i in range(1, INPUTS + 1):
            fields[
                vol.Required(f"input_{i}", default=current_inputs[i - 1])
            ] = str
        for o in range(1, OUTPUTS + 1):
            fields[
                vol.Required(f"output_{o}", default=current_outputs[o - 1])
            ] = str

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(fields)
        )
