"""Config flow for pH Control integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_SOURCE_ENTITY,
    CONF_SETPOINT,
    CONF_TIME_WINDOW,
    CONF_MIN_AMPLITUDE,
    CONF_NOISE_FILTER,
    CONF_MIN_DURATION,
    DEFAULT_SETPOINT,
    DEFAULT_TIME_WINDOW,
    DEFAULT_MIN_AMPLITUDE,
    DEFAULT_NOISE_FILTER,
    DEFAULT_MIN_DURATION,
)

_LOGGER = logging.getLogger(__name__)

class PHControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for pH Control."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        data_schema = vol.Schema({
            vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Optional(CONF_SETPOINT, default=DEFAULT_SETPOINT): vol.Coerce(float),
            vol.Optional(CONF_TIME_WINDOW, default=DEFAULT_TIME_WINDOW): vol.Coerce(int),
            vol.Optional(CONF_MIN_AMPLITUDE, default=DEFAULT_MIN_AMPLITUDE): vol.Coerce(float),
            vol.Optional(CONF_NOISE_FILTER, default=DEFAULT_NOISE_FILTER): vol.Coerce(float),
            vol.Optional(CONF_MIN_DURATION, default=DEFAULT_MIN_DURATION): vol.Coerce(int),
        })

        if user_input is not None:
            try:
                # Check if this entity is already configured
                await self.async_set_unique_id(user_input[CONF_SOURCE_ENTITY])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"pH Control for {user_input[CONF_SOURCE_ENTITY]}",
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PHControlOptionsFlow(config_entry)


class PHControlOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for pH Control."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        # Don't set self.config_entry - use entry directly in methods
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Prepare default values from the entry
        default_setpoint = self.entry.options.get(
            CONF_SETPOINT, self.entry.data.get(CONF_SETPOINT, DEFAULT_SETPOINT)
        )
        default_time_window = self.entry.options.get(
            CONF_TIME_WINDOW, self.entry.data.get(CONF_TIME_WINDOW, DEFAULT_TIME_WINDOW)
        )
        default_min_amplitude = self.entry.options.get(
            CONF_MIN_AMPLITUDE, self.entry.data.get(CONF_MIN_AMPLITUDE, DEFAULT_MIN_AMPLITUDE)
        )
        default_noise_filter = self.entry.options.get(
            CONF_NOISE_FILTER, self.entry.data.get(CONF_NOISE_FILTER, DEFAULT_NOISE_FILTER)
        )
        default_min_duration = self.entry.options.get(
            CONF_MIN_DURATION, self.entry.data.get(CONF_MIN_DURATION, DEFAULT_MIN_DURATION)
        )

        # Create options schema with defaults
        options_schema = vol.Schema({
            vol.Optional(CONF_SETPOINT, default=default_setpoint): vol.Coerce(float),
            vol.Optional(CONF_TIME_WINDOW, default=default_time_window): vol.Coerce(int),
            vol.Optional(CONF_MIN_AMPLITUDE, default=default_min_amplitude): vol.Coerce(float),
            vol.Optional(CONF_NOISE_FILTER, default=default_noise_filter): vol.Coerce(float),
            vol.Optional(CONF_MIN_DURATION, default=default_min_duration): vol.Coerce(int),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
