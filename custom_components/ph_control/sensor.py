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

class PHAmplitudeSensor(SensorEntity):
    """Representation of a pH Amplitude Sensor."""

    def __init__(self, hass: HomeAssistant, entry_id: str, source_entity: str) -> None:
        """Initialize the amplitude sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._attr_name = f"pH Amplitude {source_entity.split('.')[1]}"
        self._attr_unique_id = f"{entry_id}_amplitude"
        self._attr_native_unit_of_measurement = ""
        self._attr_state_class = "measurement"
        
        self._amplitude = None
        self._peaks = []
        self._troughs = []
        self._last_value = None
        self._trend = None
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
                if self._last_value is None:
                    self._last_value = current_value
                    return

                # Detect peaks and troughs
                if self._trend is None:
                    # Initialize trend direction
                    if current_value > self._last_value:
                        self._trend = "up"
                    elif current_value < self._last_value:
                        self._trend = "down"
                else:
                    # Detect trend reversals
                    if self._trend == "up" and current_value < self._last_value:
                        # Peak detected
                        self._peaks.append(self._last_value)
                        self._trend = "down"
                    elif self._trend == "down" and current_value > self._last_value:
                        # Trough detected
                        self._troughs.append(self._last_value)
                        self._trend = "up"

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
        }

class PHOscillationSensor(SensorEntity):
    """Representation of the pH Oscillation Count Sensor."""

    def __init__(self, hass: HomeAssistant, entry_id: str, source_entity: str) -> None:
        """Initialize the oscillation sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._attr_name = f"pH Oscillations {source_entity.split('.')[1]}"
        self._attr_unique_id = f"{entry_id}_oscillations"
        self._attr_native_unit_of_measurement = "cycles"
        self._attr_state_class = "measurement"
        
        self._oscillations = 0
        self._direction_changes = 0
        self._last_value = None
        self._trend = None
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
                if self._last_value is None:
                    self._last_value = current_value
                    return

                # Detect trend changes
                if self._trend is None:
                    # Initialize trend direction
                    if current_value > self._last_value:
                        self._trend = "up"
                    elif current_value < self._last_value:
                        self._trend = "down"
                else:
                    # Detect trend reversals
                    if self._trend == "up" and current_value < self._last_value:
                        self._direction_changes += 1
                        self._trend = "down"
                    elif self._trend == "down" and current_value > self._last_value:
                        self._direction_changes += 1
                        self._trend = "up"
                
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

    # Create amplitude and oscillation sensors
    amplitude_sensor = PHAmplitudeSensor(hass, entry_id, source_entity)
    oscillation_sensor = PHOscillationSensor(hass, entry_id, source_entity)

    async_add_entities([amplitude_sensor, oscillation_sensor], True)
