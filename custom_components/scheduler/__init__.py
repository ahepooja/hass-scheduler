"""The scheduler integration."""
from homeassistant import config_entries, core

DOMAIN = "scheduler"

async def async_setup(hass: core.HomeAssistant, config: dict):
    """Set up the scheduler component."""
    return True

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up scheduler from a config entry."""
    # res = await _dry_setup(hass, entry.data)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    # entry.add_update_listener(async_reload_entry)
    return True