import datetime
import asyncio
import logging
from statistics import mean
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up pH Control sensors."""
    sensor_entity_id = entry.data["ph_sensor"]
    new_sensor = PHControlSensor(hass, sensor_entity_id)
    async_add_entities([new_sensor], True)
    async_track_time_interval(hass, new_sensor.update_data, datetime.timedelta(minutes=5))

class PHControlSensor(SensorEntity, RestoreEntity):
    """Sensor to monitor pH fluctuations."""
    def __init__(self, hass: HomeAssistant, sensor_entity_id: str):
        self.hass = hass
        self._sensor_entity_id = sensor_entity_id
        self._state = None
        self._oscillations = 0
        self._attr_name = f"Delta pH {sensor_entity_id}"  # Unique name
        self._attr_unique_id = f"delta_ph_{sensor_entity_id.replace('.', '_')}"
        self._attr_device_class = "measurement"
        self._attr_native_unit_of_measurement = "pH"
        self._attr_icon = "mdi:wave"
    
    @property
    def state(self):
        return self._state
    
    @property
    def extra_state_attributes(self):
        return {"daily_oscillations": self._oscillations}
    
    async def async_added_to_hass(self):
        """Restore previous state on restart."""
        if (last_state := await self.async_get_last_state()) is not None:
            self._state = last_state.state
            self._oscillations = last_state.attributes.get("daily_oscillations", 0)
        self.async_write_ha_state()
    
    async def update_data(self, _):
        """Calculate delta pH and oscillations."""
        now = datetime.datetime.utcnow()
        start_time = now - datetime.timedelta(hours=24)  # Analyze last 24 hours
        
        # Get historical states from Home Assistant state machine
        history = self.hass.states.get(self._sensor_entity_id)
        if not history:
            _LOGGER.warning(f"No state history found for {self._sensor_entity_id}")
            return
        
        ph_values = []
        for state in history:
            try:
                ph_values.append(float(state.state))
            except ValueError:
                continue  # Skip invalid values
        
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
