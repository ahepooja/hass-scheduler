"""Config flow for home_appliance_scheduler."""
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from . import DOMAIN

class HomeApplianceSchedulerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for home_appliance_scheduler."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # TODO: Validate the user input.
            return self.async_create_entry(title=user_input["name"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name", description="Name of the sensor"): cv.string,
                vol.Required("window_size", description="Window size (in minutes)"): cv.positive_int,
                vol.Required("polling_interval", description="Polling interval (in minutes)"): cv.positive_int,
            }),
            errors=errors,
        )