"""Support for pH Control sensors."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers.typing import EventType

from .const import (
    DOMAIN,
    CONF_SOURCE_ENTITY,
    CONF_SETPOINT,
    CONF_TIME_WINDOW,
    CONF_MIN_AMPLITUDE,
    CONF_NOISE_FILTER,
    CONF_MIN_DURATION,
    DEFAULT_SETPOINT,
    DEFAULT_TIME_WINDOW,
    DEFAULT_MIN_AMPLITUDE,
    DEFAULT_NOISE_FILTER,
    DEFAULT_MIN_DURATION,
    ATTR_OSCILLATIONS,
    ATTR_CURRENT_STATE,
    ATTR_LAST_CHANGE,
    ATTR_CURRENT_PH,
    ATTR_SETPOINT,
    ATTR_TREND,
    ATTR_AMPLITUDE,
    ATTR_RISING,
    ATTR_FALLING,
    ATTR_STABLE,
    ATTR_DURATION,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the pH Control sensor from a config entry."""
    config = config_entry.data
    
    source_entity = config.get(CONF_SOURCE_ENTITY)
    setpoint = config.get(CONF_SETPOINT, DEFAULT_SETPOINT)
    time_window = config.get(CONF_TIME_WINDOW, DEFAULT_TIME_WINDOW)
    min_amplitude = config.get(CONF_MIN_AMPLITUDE, DEFAULT_MIN_AMPLITUDE)
    noise_filter = config.get(CONF_NOISE_FILTER, DEFAULT_NOISE_FILTER)
    min_duration = config.get(CONF_MIN_DURATION, DEFAULT_MIN_DURATION)
    
    # Get any updated options from config entry
    if config_entry.options:
        setpoint = config_entry.options.get(CONF_SETPOINT, setpoint)
        time_window = config_entry.options.get(CONF_TIME_WINDOW, time_window)
        min_amplitude = config_entry.options.get(CONF_MIN_AMPLITUDE, min_amplitude)
        noise_filter = config_entry.options.get(CONF_NOISE_FILTER, noise_filter)
        min_duration = config_entry.options.get(CONF_MIN_DURATION, min_duration)

    ph_controller = PHControlSensor(
        hass,
        config_entry.entry_id,
        source_entity,
        setpoint,
        time_window,
        min_amplitude,
        noise_filter,
        min_duration,
    )
    
    async_add_entities([ph_controller], True)


class PHControlSensor(SensorEntity):
    """Representation of a pH Control Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        source_entity: str,
        setpoint: float,
        time_window: int,
        min_amplitude: float,
        noise_filter: float,
        min_duration: int,
    ) -> None:
        """Initialize the pH Control sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._setpoint = setpoint
        self._time_window = time_window
        self._min_amplitude = min_amplitude
        self._noise_filter = noise_filter
        self._min_duration = min_duration
        
        self._attr_name = f"pH Control {source_entity}"
        self._attr_unique_id = f"{entry_id}_{source_entity}_controller"
        
        self._current_ph = None
        self._state = None
        self._last_change = datetime.now()
        self._trend = ATTR_STABLE
        self._amplitude = 0.0
        self._oscillations = 0
        self._duration = 0
        
        self._history = []
        self._last_value = None
        self._high_point = None
        self._low_point = None
        self._direction = None
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this sensor."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=f"pH Controller for {self._source_entity}",
            manufacturer="Home Assistant",
            model="pH Controller",
            entry_type="service",
        )

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {
            ATTR_CURRENT_PH: self._current_ph,
            ATTR_SETPOINT: self._setpoint,
            ATTR_TREND: self._trend,
            ATTR_AMPLITUDE: self._amplitude,
            ATTR_LAST_CHANGE: self._last_change,
            ATTR_OSCILLATIONS: self._oscillations,
            ATTR_DURATION: self._duration,
        }

    async def async_added_to_hass(self) -> None:
        """Set up a listener when this entity is added to HA."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity], self._async_source_changed
            )
        )
        
        # Initialize the sensor with current state
        state = self.hass.states.get(self._source_entity)
        if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._update_state(float(state.state))

    @callback
    def _async_source_changed(self, event: EventType) -> None:
        """Handle source entity changes."""
        if (
            event.data.get("new_state") is None
            or event.data["new_state"].state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        ):
            return

        try:
            value = float(event.data["new_state"].state)
            self._update_state(value)
            self.async_write_ha_state()
        except (ValueError, TypeError) as ex:
            _LOGGER.warning(
                "Unable to update from source %s: %s", self._source_entity, ex
            )

    def _update_state(self, value: float) -> None:
        """Update sensor state based on pH value."""
        now = datetime.now()
        
        # Store the value and timestamp in history
        self._history.append((value, now))
        
        # Remove entries older than time_window
        cutoff_time = now - timedelta(seconds=self._time_window)
        self._history = [(v, t) for (v, t) in self._history if t >= cutoff_time]
        
        # Update current pH
        self._current_ph = value
        
        # Determine if we need to track oscillations around setpoint
        if self._last_value is None:
            self._last_value = value
            return
            
        # Calculate direction of change
        change = value - self._last_value
        
        # Filter out noise
        if abs(change) <= self._noise_filter:
            # No significant change
            pass
        else:
            # Determine direction of change
            current_direction = ATTR_RISING if change > 0 else ATTR_FALLING
            
            # Track high and low points to determine amplitude
            if self._direction is None:
                self._direction = current_direction
                self._high_point = max(value, self._last_value) if current_direction == ATTR_RISING else None
                self._low_point = min(value, self._last_value) if current_direction == ATTR_FALLING else None
            elif current_direction != self._direction:
                # Direction has changed - record amplitude and update oscillation count
                if self._direction == ATTR_RISING and self._high_point is not None:
                    # We were rising and now falling
                    if self._low_point is not None:
                        amp = self._high_point - self._low_point
                        if amp >= self._min_amplitude:
                            self._amplitude = amp
                            self._oscillations += 1
                            self._trend = ATTR_OSCILLATIONS
                            self._last_change = now
                    self._low_point = value
                elif self._direction == ATTR_FALLING and self._low_point is not None:
                    # We were falling and now rising
                    if self._high_point is not None:
                        amp = self._high_point - self._low_point
                        if amp >= self._min_amplitude:
                            self._amplitude = amp
                            self._oscillations += 1
                            self._trend = ATTR_OSCILLATIONS
                            self._last_change = now
                    self._high_point = value
                
                # Update direction
                self._direction = current_direction
            else:
                # Continuing in same direction, update high/low point
                if self._direction == ATTR_RISING:
                    self._high_point = max(value, self._high_point if self._high_point is not None else value)
                else:
                    self._low_point = min(value, self._low_point if self._low_point is not None else value)
        
        # Determine state based on oscillations and duration
        time_since_change = (now - self._last_change).total_seconds()
        self._duration = int(time_since_change)
        
        if self._trend == ATTR_OSCILLATIONS and time_since_change >= self._min_duration:
            if abs(value - self._setpoint) <= self._noise_filter:
                self._state = "stable"
            elif value > self._setpoint:
                self._state = "high"
            else:
                self._state = "low"
        else:
            # Not enough time has passed or not enough oscillations
            if abs(value - self._setpoint) <= self._noise_filter:
                self._state = "near_setpoint"
            elif value > self._setpoint:
                self._state = "above_setpoint"
            else:
                self._state = "below_setpoint"
        
        # Update last value
        self._last_value = value
