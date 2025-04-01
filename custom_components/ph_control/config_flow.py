"""Config flow for pH Control integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_SOURCE_ENTITY,
    CONF_SETPOINT,
    CONF_TIME_WINDOW,
    CONF_MIN_AMPLITUDE,
    CONF_NOISE_FILTER,
    CONF_MIN_DURATION,
    DEFAULT_NAME,
    DEFAULT_SETPOINT,
    DEFAULT_TIME_WINDOW,
    DEFAULT_MIN_AMPLITUDE,
    DEFAULT_NOISE_FILTER,
    DEFAULT_MIN_DURATION,
)


class PHControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for pH Control."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", DEFAULT_NAME),
                data=user_input,
            )

        # Define the configuration schema
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Optional("name", default=DEFAULT_NAME): str,
                vol.Optional(CONF_SETPOINT, default=DEFAULT_SETPOINT): vol.Coerce(float),
                vol.Optional(CONF_TIME_WINDOW, default=DEFAULT_TIME_WINDOW): vol.Coerce(int),
                vol.Optional(CONF_MIN_AMPLITUDE, default=DEFAULT_MIN_AMPLITUDE): vol.Coerce(float),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PHControlOptionsFlowHandler(config_entry)


class PHControlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for pH Control integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current configuration or use defaults
        data = self.config_entry.data
        options = self.config_entry.options

        option_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SETPOINT,
                    default=options.get(CONF_SETPOINT, data.get(CONF_SETPOINT, DEFAULT_SETPOINT)),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_TIME_WINDOW,
                    default=options.get(CONF_TIME_WINDOW, data.get(CONF_TIME_WINDOW, DEFAULT_TIME_WINDOW)),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_MIN_AMPLITUDE,
                    default=options.get(CONF_MIN_AMPLITUDE, data.get(CONF_MIN_AMPLITUDE, DEFAULT_MIN_AMPLITUDE)),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_NOISE_FILTER,
                    default=options.get(CONF_NOISE_FILTER, data.get(CONF_NOISE_FILTER, DEFAULT_NOISE_FILTER)),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_MIN_DURATION,
                    default=options.get(CONF_MIN_DURATION, data.get(CONF_MIN_DURATION, DEFAULT_MIN_DURATION)),
                ): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="init", data_schema=option_schema)
