"""Support for pH Control sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from datetime import datetime, timedelta

from .const import DOMAIN, ATTR_PEAKS, ATTR_TROUGHS


class PHAmplitudeSensor(SensorEntity):
    """Representation of the pH Amplitude Sensor."""

    def __init__(self, entry_id: str, source_entity: str) -> None:
        """Initialize the amplitude sensor."""
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._attr_name = f"pH Amplitude {source_entity}"
        self._attr_unique_id = f"{entry_id}_{source_entity}_amplitude"
        self._amplitude = None
        self._attributes = {}

    @property
    def native_value(self):
        """Return the current amplitude."""
        return self._amplitude

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return self._attributes

    async def async_update(self):
        """Fetch amplitude data."""
        # Logic to calculate amplitude based on peaks and troughs
        peaks = self.hass.states.get(f"{self._source_entity}_peaks")
        troughs = self.hass.states.get(f"{self._source_entity}_troughs")

        if peaks and troughs:
            peak_values = peaks.attributes.get(ATTR_PEAKS, [])
            trough_values = troughs.attributes.get(ATTR_TROUGHS, [])
            if peak_values and trough_values:
                self._amplitude = max(peak_values) - min(trough_values)

                # Update attributes
                self._attributes.update({
                    "last_peak": peak_values[-1] if peak_values else None,
                    "last_trough": trough_values[-1] if trough_values else None,
                    "last_updated": datetime.now().isoformat(),
                })


class PHOscillationSensor(SensorEntity):
    """Representation of the pH Oscillation Count Sensor."""

    def __init__(self, entry_id: str, source_entity: str) -> None:
        """Initialize the oscillation sensor."""
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._attr_name = f"pH Oscillations {source_entity}"
        self._attr_unique_id = f"{entry_id}_{source_entity}_oscillations"
        self._oscillations = 0
        self._attributes = {}

    @property
    def native_value(self):
        """Return the current oscillation count."""
        return self._oscillations

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return self._attributes

    async def async_update(self):
        """Fetch oscillation data."""
        # Logic to calculate oscillations based on peaks and troughs crossing setpoint
        history = self.hass.states.get(self._source_entity)
        
        if history:
            # Example logic to count oscillations based on setpoint crossings
            state_changes = history.attributes.get("state_changes", [])
            oscillation_count = len(state_changes) // 2  # Assuming each oscillation has a peak and a trough
            
            self._oscillations = oscillation_count

            # Update attributes
            self._attributes.update({
                "last_updated": datetime.now().isoformat(),
                "state_changes": state_changes,
            })


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
    amplitude_sensor = PHAmplitudeSensor(entry_id, source_entity)
    oscillation_sensor = PHOscillationSensor(entry_id, source_entity)

    async_add_entities([amplitude_sensor, oscillation_sensor], True)
