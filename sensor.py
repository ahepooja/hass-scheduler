"""The Sensor platform for home_appliance_scheduler integration."""
from homeassistant.helpers.device_registry import async_get as get_device_registry
import logging
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
import pandas as pd
from datetime import datetime, timedelta
import json
from dateutil.parser import parse
from . import DOMAIN
import yaml
import numpy as np
import pytz
from pydantic import BaseModel

logger = logging.getLogger(__name__)
pd.set_option('display.float_format', '{:.3f}'.format)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup sensor platform."""
    name = config.get("name")
    window_size = config.get("window_size")
    polling_interval = config.get("polling_interval")

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    logger.warn(entry.data)
    device_id = entry.data.get("name")
    window_size = entry.data.get("window_size")
    polling_interval = entry.data.get("polling_interval")
    async_add_devices([CoreSensor(device_id, window_size, polling_interval), SchedulerEntity(hass, device_id, "start"), SchedulerEntity(hass, device_id, "end"), SchedulerEntity(hass, device_id, "value")])


class DeviceEntity(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def unique_id(self):
        return f"{self._device_id}.{self._name}"

    @property
    def device_info(self):
        return {
            'identifiers': {(DOMAIN, self._device_id)},
            'name': f"Scheduler: {self._device_id}",
        }

class SchedulerEntity(DeviceEntity):
    def __init__(self, hass, device_id, attribute):
        self._hass = hass
        self._device_id = device_id
        self._name = attribute
        self._value = None

    @property
    def name(self):
        return self._name.capitalize()

    @property
    def state(self):
        return self._value

    async def async_update(self):
        # Use the hass object to access the state machine
        logger.warn(f"{self._device_id},{self._name}")
        logger.warn(f"sensor.{self._device_id}_forecast")
        self._value = self.hass.states.get(f"sensor.{self._device_id}_forecast").attributes.get(self._name)

class ScheduleItem(BaseModel):
    start: datetime = None
    end: datetime = None
    value: float = None


class CoreSensor(DeviceEntity):
    def __init__(self, device_id, window_size, polling_interval):
        self._device_id = device_id
        self._window_size = window_size
        self._polling_interval = polling_interval
        self._name = "Forecast"
        self._forecast = []

    def get_schedule(self):
        """
        Calculate the best time to start the washing machine based on a rolling mean of power usage data.

        Parameters:
        power_usage_data (pd.Series): A pandas Series where the index is the time of day and the values are the power usage at that time.
        window_size (int): The size of the rolling window in minutes.

        Returns:
        pd.Timestamp: The best time to start the washing machine.
        """
        if len(self._forecast) == 0:
            return ScheduleItem()
        # Get the current time
        dt = datetime.fromisoformat(self._forecast[0].get("start"))
        now = datetime.now(dt.tzinfo)
        # Expand the forecast list to a pandas Series with a data point for every minute
        forecast_data = pd.Series()
        
        logger.warn(f"Getting forecast data {len(self._forecast)}")
        for item in self._forecast:
            start = datetime.fromisoformat(item['start'])
            end = datetime.fromisoformat(item['end'])
            value = item['value']
            dates = pd.date_range(start, end, freq='T')
            logger.warn(value, dates)
            forecast_data = pd.concat([forecast_data, pd.Series(np.full(len(dates), value), index=dates)])

        # Filter the forecast data to only include times from now onwards
        future_forecast_data = forecast_data[forecast_data.index >= now]

        # Calculate the rolling mean of the future forecast data
        rolling_mean = future_forecast_data.rolling(window=self._window_size, min_periods=1).mean()

        # Find the time of the lowest mean power usage
        window_start = rolling_mean.idxmin()
        window_end = window_start + timedelta(minutes=self._window_size)

        # Calculate the mean price for the window
        value = forecast_data.loc[window_start:window_end].mean()

        logger.warn(f"Window start: {window_start}, window end: {window_end}, value: {value}")
        schedule_item = ScheduleItem(start=window_start, end=window_end, value=value)
        return schedule_item


    @property
    def name(self):
        return f"{self._name}"

    @property
    def state(self):
        return bool(self._forecast)

    @property
    def extra_state_attributes(self):
        schedule: ScheduleItem = self.get_schedule()
        return {
            "start": schedule.start,
            "end": schedule.end,
            "value": schedule.value
        }

    
    
    async def async_update(self):
        # Use the hass object to access the state machine
        forecast_entity = self.hass.states.get("sensor.nordpool_kwh_fi_eur_3_10_024")

        # Define a safe dictionary for eval
        if forecast_entity is not None:
            self._forecast = forecast_entity.attributes.get("raw_total")

class ScheduleEntity(Entity):
    def __init__(self, device_id, attribute):
        self._device_id = device_id
        self._attribute = attribute

    @property
    def state(self):
        schedule_item = self.hass.states.get(self._device_id)
        return schedule_item.attributes.get(self._) if schedule_item else None


    async def async_update(self):
        self._device.async_update()