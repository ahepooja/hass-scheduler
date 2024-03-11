"""The Sensor platform for scheduler integration."""
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
from typing import List

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
    async_add_devices([CoreSensor(device_id, window_size, polling_interval)])

class DeviceEntity(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def unique_id(self):
        logger.warn(f"Entity_id: {self._device_id}.{self._name}")
        return f"{self._device_id}_{self._name}"

    @property
    def name(self):
        return f"{self._device_id}_{self._name}"

    @property
    def device_info(self):
        return {
            'identifiers': {(DOMAIN, self._device_id)},
            'name': f"Scheduler: {self._device_id}",
        }

class ScheduleItem(BaseModel):
    start: datetime = None
    end: datetime = None
    value: float = None


class CoreSensor(DeviceEntity):
    def __init__(self, device_id, window_size, polling_interval):
        self._device_id = device_id
        self._window_size = window_size
        self._polling_interval = polling_interval
        self._name = "forecast"
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
            return [ScheduleItem() for _ in range(5)]
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

        # Sort by rolling_mean in ascending order
        sorted_data = rolling_mean.sort_values()

        # Find the top 5 times of the lowest mean power usage that are at least one hour apart
        results = []
        for time, mean in sorted_data.items():
            if not results or all(abs((time - r.start).total_seconds()) >= 3600 for r in results):
                window_end = time + timedelta(minutes=self._window_size)
                value = future_forecast_data.loc[time:window_end].mean()
                results.append(ScheduleItem(start=time, end=window_end, value=value))
                if len(results) == 5:
                    break

        results = sorted(results, key=lambda x: x.value)

        return results

    @property
    def state(self):
        return bool(self._forecast)

    @property
    def extra_state_attributes(self):
        schedules: List[ScheduleItem] = self.get_schedule()
        logger.warn(schedules)
        return {
            "device": self._device_id,
            "schedules": [s.dict() for s in schedules]
        }
    
    async def async_update(self):
        # Use the hass object to access the state machine
        forecast_entity = self.hass.states.get("sensor.nordpool_kwh_fi_eur_3_10_024")

        # Define a safe dictionary for eval
        if forecast_entity is not None:
            self._forecast = forecast_entity.attributes.get("raw_total")