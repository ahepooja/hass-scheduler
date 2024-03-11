"""Config flow for scheduler."""
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from . import DOMAIN

class HomeApplianceSchedulerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input['name'])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input['name'],
                data={"name": user_input["name"], "window_size": user_input["window_size"], "polling_interval": user_input["polling_interval"]},
            )

        # Show the form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("window_size", default=60): int,
                vol.Optional("polling_interval", default=5): int,
            }),
        )