import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

class PHControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for pH Control."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            return self.async_create_entry(title="pH Control", data=user_input)

        schema = vol.Schema({
            vol.Required("ph_sensor"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
