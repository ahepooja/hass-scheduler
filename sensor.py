"""The Sensor platform for home_appliance_scheduler integration."""
import logging
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

# Add constructors for datetime.datetime and zoneinfo.ZoneInfo
def datetime_constructor(loader, node):
    return datetime.strptime(node.value, "%Y-%m-%d %H:%M:%S")

def zoneinfo_constructor(loader, node):
    return ZoneInfo(node.value)

# yaml.SafeLoader.add_constructor('!!python/object:datetime.datetime', datetime_constructor)
# yaml.SafeLoader.add_constructor('!!python/object:zoneinfo.ZoneInfo', zoneinfo_constructor)

class ScheduleItem(BaseModel):
    start: datetime = None
    end: datetime = None
    value: float = None

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    config = hass.data[DOMAIN]

    sensor = HomeApplianceSchedulerSensor(
        name = config.get("name"),
        window_size = config.get("window_size"),
        polling_interval= config.get("polling_interval"),
    )
    async_add_entities([sensor])

class HomeApplianceSchedulerSensor(Entity):
    def __init__(self, name, window_size, polling_interval):
        self._window_size = window_size
        self._polling_interval = polling_interval
        self._unique_id = f"home_appliance_scheduler_sensor_{name.lower()}"
        self._name = f"Scheduler: {name}"
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
        logger.warn(f"Schedule item: {schedule_item}")
        return schedule_item

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return bool(self._forecast)

    @property
    def extra_state_attributes(self):
        schedule_item: ScheduleItem = self.get_schedule()

        return {
            "window_size": self._window_size,
            "polling_interval": self._polling_interval,
            "forecast": self._forecast,
            "schedule_start": schedule_item.start,
            "schedule_end": schedule_item.end,
            "schedule_price": schedule_item.value
        }
    
    async def async_update(self):
        # Use the hass object to access the state machine
        forecast_entity = self.hass.states.get("sensor.nordpool_kwh_fi_eur_3_10_024")

        # Define a safe dictionary for eval
        if forecast_entity is not None:
             self._forecast = forecast_entity.attributes.get("raw_total")