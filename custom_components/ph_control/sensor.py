"""Support for pH Control sensors."""
import logging
from datetime import datetime
from typing import Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, ATTR_PEAKS, ATTR_TROUGHS, ATTR_AMPLITUDE, ATTR_OSCILLATIONS

_LOGGER = logging.getLogger(__name__)

CONF_SETPOINT = "setpoint"
CONF_THRESHOLD = "threshold"
CONF_MIN_AMPLITUDE = "min_amplitude"

DEFAULT_SETPOINT = 7.8  # Midpoint of typical pH oscillation
DEFAULT_THRESHOLD = 0.3 # How much deviation is significant
DEFAULT_MIN_AMPLITUDE = 0.1 # Minimum change to consider

class PHAmplitudeSensor(SensorEntity):
    """Representation of a pH Amplitude Sensor."""

    def __init__(self, hass: HomeAssistant, entry_id: str, source_entity: str, 
                 setpoint: float, threshold: float, min_amplitude: float) -> None:
        """Initialize the amplitude sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._setpoint = setpoint
        self._threshold = threshold
        self._min_amplitude = min_amplitude
        
        self._attr_name = f"pH Amplitude {source_entity.split('.')[1]}"
        self._attr_unique_id = f"{entry_id}_amplitude"
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = "measurement"
        
        self._amplitude = None
        self._peaks = []
        self._troughs = []
        self._last_value = None
        self._trend = None
        self._significant_change = False
        self._last_direction_change_time = None
        self._unsub_listener = None

    async def async_added_to_hass(self) -> None:
        """Set up state change listener when added to hass."""
        @callback
        def process_state_change(event):
            """Handle state changes."""
            new_state = event.data.get("new_state")
            if new_state is None:
                return

            try:
                current_value = float(new_state.state)
                current_time = datetime.now()
                
                if self._last_value is None:
                    self._last_value = current_value
                    return

                # Check if the change is significant (exceeds min amplitude)
                value_change = abs(current_value - self._last_value)
                if value_change < self._min_amplitude:
                    # Ignore small fluctuations
                    self._last_value = current_value
                    return
                
                # Determine if we've moved significantly from the setpoint
                deviation_from_setpoint = abs(current_value - self._setpoint)
                self._significant_change = deviation_from_setpoint > self._threshold
                
                # Detect peaks and troughs based on trend changes
                if self._trend is None:
                    # Initialize trend direction
                    if current_value > self._last_value:
                        self._trend = "up"
                    elif current_value < self._last_value:
                        self._trend = "down"
                else:
                    # Detect significant trend reversals
                    if self._trend == "up" and current_value < self._last_value:
                        # Peak detected - only register if significant
                        if self._significant_change:
                            self._peaks.append(self._last_value)
                            self._trend = "down"
                            self._last_direction_change_time = current_time
                    elif self._trend == "down" and current_value > self._last_value:
                        # Trough detected - only register if significant
                        if self._significant_change:
                            self._troughs.append(self._last_value)
                            self._trend = "up"
                            self._last_direction_change_time = current_time

                # Calculate amplitude if we have both peaks and troughs
                if self._peaks and self._troughs:
                    self._amplitude = max(self._peaks) - min(self._troughs)
                    self.async_write_ha_state()

                self._last_value = current_value
            except (ValueError, TypeError):
                _LOGGER.error("Unable to process pH value: %s", new_state.state)

        self._unsub_listener = async_track_state_change_event(
            self.hass, [self._source_entity], process_state_change
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        if self._unsub_listener is not None:
            self._unsub_listener()

    @property
    def native_value(self):
        """Return the current amplitude."""
        return self._amplitude

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            ATTR_PEAKS: self._peaks[-10:] if self._peaks else [],
            ATTR_TROUGHS: self._troughs[-10:] if self._troughs else [],
            "last_updated": datetime.now().isoformat(),
            "trend": self._trend,
            "setpoint": self._setpoint,
            "threshold": self._threshold,
            "min_amplitude": self._min_amplitude
        }

class PHOscillationSensor(SensorEntity):
    """Representation of the pH Oscillation Count Sensor."""

    def __init__(self, hass: HomeAssistant, entry_id: str, source_entity: str,
                 setpoint: float, threshold: float, min_amplitude: float) -> None:
        """Initialize the oscillation sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._setpoint = setpoint
        self._threshold = threshold
        self._min_amplitude = min_amplitude
        
        self._attr_name = f"pH Oscillations {source_entity.split('.')[1]}"
        self._attr_unique_id = f"{entry_id}_oscillations"
        self._attr_native_unit_of_measurement = "cycles"
        self._attr_state_class = "measurement"
        
        self._oscillations = 0
        self._direction_changes = 0
        self._last_value = None
        self._trend = None
        self._significant_change = False
        self._last_direction_change_time = None
        self._unsub_listener = None

    async def async_added_to_hass(self) -> None:
        """Set up state change listener when added to hass."""
        @callback
        def process_state_change(event):
            """Handle state changes."""
            new_state = event.data.get("new_state")
            if new_state is None:
                return

            try:
                current_value = float(new_state.state)
                current_time = datetime.now()
                
                if self._last_value is None:
                    self._last_value = current_value
                    return

                # Check if the change is significant (exceeds min amplitude)
                value_change = abs(current_value - self._last_value)
                if value_change < self._min_amplitude:
                    # Ignore small fluctuations
                    self._last_value = current_value
                    return
                
                # Determine if we've moved significantly from the setpoint
                deviation_from_setpoint = abs(current_value - self._setpoint)
                self._significant_change = deviation_from_setpoint > self._threshold
                
                # Detect trend changes
                if self._trend is None:
                    # Initialize trend direction
                    if current_value > self._last_value:
                        self._trend = "up"
                    elif current_value < self._last_value:
                        self._trend = "down"
                else:
                    # Detect significant trend reversals
                    if self._trend == "up" and current_value < self._last_value:
                        if self._significant_change:
                            self._direction_changes += 1
                            self._trend = "down"
                            self._last_direction_change_time = current_time
                    elif self._trend == "down" and current_value > self._last_value:
                        if self._significant_change:
                            self._direction_changes += 1
                            self._trend = "up"
                            self._last_direction_change_time = current_time
                
                # Each complete oscillation has two direction changes
                self._oscillations = self._direction_changes // 2
                self.async_write_ha_state()
                
                self._last_value = current_value
            except (ValueError, TypeError):
                _LOGGER.error("Unable to process pH value: %s", new_state.state)

        self._unsub_listener = async_track_state_change_event(
            self.hass, [self._source_entity], process_state_change
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        if self._unsub_listener is not None:
            self._unsub_listener()

    @property
    def native_value(self):
        """Return the current oscillation count."""
        return self._oscillations

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "direction_changes": self._direction_changes,
            "last_updated": datetime.now().isoformat(),
            "trend": self._trend,
            "setpoint": self._setpoint,
            "threshold": self._threshold,
            "min_amplitude": self._min_amplitude
        }

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up pH Control sensors from a config entry."""
    config = config_entry.data
    source_entity = config.get("source_entity")
    entry_id = config_entry.entry_id
    
    # Get the configurable parameters with defaults
    setpoint = config.get(CONF_SETPOINT, DEFAULT_SETPOINT)
    threshold = config.get(CONF_THRESHOLD, DEFAULT_THRESHOLD)
    min_amplitude = config.get(CONF_MIN_AMPLITUDE, DEFAULT_MIN_AMPLITUDE)

    # Create amplitude and oscillation sensors
    amplitude_sensor = PHAmplitudeSensor(
        hass, entry_id, source_entity, setpoint, threshold, min_amplitude
    )
    oscillation_sensor = PHOscillationSensor(
        hass, entry_id, source_entity, setpoint, threshold, min_amplitude
    )

    async_add_entities([amplitude_sensor, oscillation_sensor], True)
