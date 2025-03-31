import datetime
import asyncio
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.helpers.history import get_last_state_changes
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from statistics import mean
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry, async_add_entities):
    """Set up the pH Control sensor entity."""
    sensor_entity = entry.data["ph_sensor"]
    sensor = PHControlSensor(hass, sensor_entity)
    async_add_entities([sensor], True)
    async_track_time_interval(hass, sensor.update_data, datetime.timedelta(minutes=5))

class PHControlSensor(SensorEntity):
    """Sensor to monitor pH fluctuations."""
    def __init__(self, hass, sensor_entity):
        self.hass = hass
        self._sensor_entity = sensor_entity
        self._state = None
        self._oscillations = 0
        self._attr_name = "PH Control Delta"
        self._attr_unique_id = f"ph_control_{sensor_entity}"
        self._attr_device_class = "measurement"
        self._attr_native_unit_of_measurement = "pH"
        self._attr_icon = "mdi:wave"
    
    @property
    def state(self):
        return self._state
    
    @property
    def extra_state_attributes(self):
        return {"daily_oscillations": self._oscillations}
    
    async def update_data(self, _):
        now = dt_util.utcnow()
        start_time = now - datetime.timedelta(hours=24)  # Analyze last 24 hours
        
        history = await self.hass.async_add_executor_job(
            get_last_state_changes, self.hass, 2000, self._sensor_entity, start_time, now
        )
        
        if not history or self._sensor_entity not in history:
            return
        
        ph_values = [float(state.state) for state in history[self._sensor_entity] if state.state.replace('.', '', 1).isdigit()]
        
        if len(ph_values) < 2:
            return
        
        peaks = []
        troughs = []
        oscillations = 0
        
        for i in range(1, len(ph_values) - 1):
            if ph_values[i] > ph_values[i - 1] and ph_values[i] > ph_values[i + 1]:
                peaks.append(ph_values[i])
            elif ph_values[i] < ph_values[i - 1] and ph_values[i] < ph_values[i + 1]:
                troughs.append(ph_values[i])
        
        if peaks and troughs:
            delta_values = [p - t for p, t in zip(peaks, troughs)]
            self._state = round(mean(delta_values), 2)
            oscillations = min(len(peaks), len(troughs))  # Count number of oscillations
        else:
            self._state = None
            oscillations = 0
        
        self._oscillations = oscillations
        self.async_write_ha_state()
