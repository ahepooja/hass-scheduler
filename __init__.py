"""The home_appliance_scheduler integration."""
from homeassistant import config_entries, core

DOMAIN = "home_appliance_scheduler"

async def async_setup(hass: core.HomeAssistant, config: dict):
    """Set up the home_appliance_scheduler component."""
    return True

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up home_appliance_scheduler from a config entry."""
    hass.data[DOMAIN] = entry.data
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
    return True