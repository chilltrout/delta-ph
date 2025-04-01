"""Config flow for pH Control integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN

class PHControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for pH Control."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Validate input here if needed
            # For example, check if source entity exists
            
            return self.async_create_entry(
                title=f"pH Control for {user_input['source_entity']}", 
                data=user_input
            )

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("source_entity"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            multiple=False,
                        ),
                    ),
                }
            ),
            errors=errors,
        )
