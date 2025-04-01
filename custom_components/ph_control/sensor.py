"""Sensor platform for pH Control integration."""
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import State
from homeassistant.components.recorder import get_instance
from homeassistant.util import dt as dt_util

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
    ATTR_AVERAGE_AMPLITUDE,
    ATTR_MAX_AMPLITUDE,
    ATTR_LAST_AMPLITUDE,
    ATTR_TREND,
    ATTR_LAST_PEAK,
    ATTR_LAST_TROUGH,
    ATTR_STATUS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the pH Control sensor from config entry."""
    name = config_entry.title
    source_entity = config_entry.data[CONF_SOURCE_ENTITY]
    
    # Get configuration with defaults
    setpoint = config_entry.options.get(
        CONF_SETPOINT, 
        config_entry.data.get(CONF_SETPOINT, DEFAULT_SETPOINT)
    )
    time_window = config_entry.options.get(
        CONF_TIME_WINDOW, 
        config_entry.data.get(CONF_TIME_WINDOW, DEFAULT_TIME_WINDOW)
    )
    min_amplitude = config_entry.options.get(
        CONF_MIN_AMPLITUDE, 
        config_entry.data.get(CONF_MIN_AMPLITUDE, DEFAULT_MIN_AMPLITUDE)
    )
    noise_filter = config_entry.options.get(
        CONF_NOISE_FILTER, 
        config_entry.data.get(CONF_NOISE_FILTER, DEFAULT_NOISE_FILTER)
    )
    min_duration = config_entry.options.get(
        CONF_MIN_DURATION, 
        config_entry.data.get(CONF_MIN_DURATION, DEFAULT_MIN_DURATION)
    )
    
    async_add_entities(
        [
            PHControlSensor(
                hass, 
                name, 
                source_entity, 
                float(setpoint), 
                int(time_window), 
                float(min_amplitude), 
                float(noise_filter), 
                int(min_duration)
            )
        ],
        True,
    )


class PHControlSensor(SensorEntity):
    """Representation of a pH Control Sensor."""

    def __init__(self, hass, name, source_entity, setpoint, time_window, min_amplitude, noise_filter, min_duration):
        """Initialize the pH control sensor."""
        self.hass = hass
        self._name = name
        self.source_entity = source_entity
        self.setpoint = setpoint
        self.time_window = time_window
        self.min_amplitude = min_amplitude
        self.noise_filter = noise_filter
        self.min_duration = min_duration
        
        self._state = None
        self._state_history = []
        self._peaks = []
        self._troughs = []
        self._oscillations = []
        self._above_setpoint = None
        self._attributes = {}
        self._last_update = None
        
        # Set entity properties
        self._attr_unique_id = f"ph_control_{source_entity}"
        self._attr_name = name
        self._attr_icon = "mdi:chart-bell-curve"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await self.hass.async_add_executor_job(self.update_data)

    def update_data(self) -> None:
        """Calculate pH oscillation metrics."""
        try:
            # Get history data from the database
            end_time = dt_util.utcnow()
            start_time = end_time - timedelta(hours=self.time_window)
            
            # Get history data from recorder with proper iteration handling
            recorder = get_instance(self.hass)
            history_list = []
            
            with recorder.get_session() as session:
                states = session.query(State).filter(
                    State.entity_id == self.source_entity,
                    State.last_updated >= start_time,
                    State.last_updated <= end_time,
                ).order_by(State.last_updated.asc()).all()
                
                # Process each state individually to avoid iteration error
                for state in states:
                    try:
                        timestamp = state.last_updated
                        ph_value = float(state.state)
                        history_list.append((timestamp, ph_value))
                    except (ValueError, TypeError):
                        continue
            
            if not history_list:
                _LOGGER.warning("No pH data found for the specified time window")
                self._state = "unknown"
                return
            
            # Save history for processing
            self._state_history = history_list
            
            # Process pH data for oscillation analysis
            self._detect_oscillations()
            self._calculate_metrics()
            
            # Update sensor state with the most important metric (amplitude trend)
            self._state = self._attributes.get(ATTR_TREND, "unknown")
            
            self._last_update = dt_util.utcnow()
            
        except Exception as e:
            _LOGGER.error("Error updating pH control sensor: %s", e)
            self._state = "unknown"
    
    def _detect_oscillations(self) -> None:
        """Detect oscillations around the setpoint."""
        self._peaks = []
        self._troughs = []
        self._oscillations = []
        
        if not self._state_history or len(self._state_history) < 5:
            return
        
        # Start by determining if we're above or below setpoint
        self._above_setpoint = self._state_history[0][1] > self.setpoint
        
        current_segment = []
        for timestamp, ph_value in self._state_history:
            is_above = ph_value > self.setpoint
            
            # Check for setpoint crossing
            if is_above != self._above_setpoint:
                # Process segment and find peak/trough
                if current_segment:
                    if self._above_setpoint:
                        self._process_peak_segment(current_segment)
                    else:
                        self._process_trough_segment(current_segment)
                
                # Reset for new segment
                current_segment = [(timestamp, ph_value)]
                self._above_setpoint = is_above
            else:
                current_segment.append((timestamp, ph_value))
        
        # Process the last segment if it exists
        if current_segment:
            if self._above_setpoint:
                self._process_peak_segment(current_segment)
            else:
                self._process_trough_segment(current_segment)
        
        # Match peaks and troughs to form oscillations
        self._match_oscillations()
    
    def _process_peak_segment(self, segment):
        """Process a segment above the setpoint to find peaks."""
        if len(segment) < 2:
            return
        
        # Find the highest point in the segment
        peak_value = max(segment, key=lambda x: x[1])
        
        # Only consider it a peak if it's significantly above the setpoint
        if peak_value[1] - self.setpoint > self.min_amplitude:
            # Check if the segment duration is long enough
            segment_duration = (segment[-1][0] - segment[0][0]).total_seconds()
            if segment_duration >= self.min_duration:
                self._peaks.append(peak_value)
    
    def _process_trough_segment(self, segment):
        """Process a segment below the setpoint to find troughs."""
        if len(segment) < 2:
            return
        
        # Find the lowest point in the segment
        trough_value = min(segment, key=lambda x: x[1])
        
        # Only consider it a trough if it's significantly below the setpoint
        if self.setpoint - trough_value[1] > self.min_amplitude:
            # Check if the segment duration is long enough
            segment_duration = (segment[-1][0] - segment[0][0]).total_seconds()
            if segment_duration >= self.min_duration:
                self._troughs.append(trough_value)
    
    def _match_oscillations(self):
        """Match peaks and troughs to form complete oscillations."""
        if not self._peaks or not self._troughs:
            return
        
        # Sort peaks and troughs by timestamp
        sorted_peaks = sorted(self._peaks, key=lambda x: x[0])
        sorted_troughs = sorted(self._troughs, key=lambda x: x[0])
        
        # Match peaks with subsequent troughs to form oscillations
        for i, peak in enumerate(sorted_peaks):
            # Find the next trough that occurs after this peak
            next_troughs = [t for t in sorted_troughs if t[0] > peak[0]]
            if next_troughs:
                next_trough = next_troughs[0]
                amplitude = peak[1] - next_trough[1]
                
                # Only record oscillations with significant amplitude
                if amplitude > self.min_amplitude:
                    self._oscillations.append({
                        "peak_time": peak[0],
                        "peak_value": peak[1],
                        "trough_time": next_trough[0],
                        "trough_value": next_trough[1],
                        "amplitude": amplitude,
                        "duration": (next_trough[0] - peak[0]).total_seconds()
                    })
    
    def _calculate_metrics(self):
        """Calculate metrics based on detected oscillations."""
        attributes = {}
        
        # Count oscillations in the last 24 hours
        now = dt_util.utcnow()
        recent_oscillations = [
            osc for osc in self._oscillations 
            if (now - osc["peak_time"]).total_seconds() / 3600 <= 24
        ]
        
        attributes[ATTR_OSCILLATIONS] = len(recent_oscillations)
        
        if recent_oscillations:
            # Calculate average and maximum amplitude
            amplitudes = [osc["amplitude"] for osc in recent_oscillations]
            attributes[ATTR_AVERAGE_AMPLITUDE] = round(sum(amplitudes) / len(amplitudes), 2)
            attributes[ATTR_MAX_AMPLITUDE] = round(max(amplitudes), 2)
            
            # Get last oscillation amplitude
            attributes[ATTR_LAST_AMPLITUDE] = round(recent_oscillations[-1]["amplitude"], 2)
            
            # Store timestamps of last peak and trough
            attributes[ATTR_LAST_PEAK] = recent_oscillations[-1]["peak_time"].isoformat()
            attributes[ATTR_LAST_TROUGH] = recent_oscillations[-1]["trough_time"].isoformat()
            
            # Calculate trend (increasing amplitude indicates alkalinity depletion)
            if len(recent_oscillations) > 1:
                # Get average amplitudes for first half and second half
                half_idx = len(recent_oscillations) // 2
                first_half = recent_oscillations[:half_idx]
                second_half = recent_oscillations[half_idx:]
                
                first_avg = sum(osc["amplitude"] for osc in first_half) / len(first_half)
                second_avg = sum(osc["amplitude"] for osc in second_half) / len(second_half)
                
                percent_change = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
                
                if percent_change > 15:
                    trend = "rapidly_increasing"
                    status = "low"
                elif percent_change > 5:
                    trend = "increasing"
                    status = "decreasing"
                elif percent_change < -5:
                    trend = "decreasing"
                    status = "good"
                else:
                    trend = "stable"
                    status = "normal"
            else:
                trend = "unknown"
                status = "unknown"
                
            attributes[ATTR_TREND] = trend
            attributes[ATTR_STATUS] = status
        else:
            attributes[ATTR_AVERAGE_AMPLITUDE] = 0
            attributes[ATTR_MAX_AMPLITUDE] = 0
            attributes[ATTR_LAST_AMPLITUDE] = 0
            attributes[ATTR_TREND] = "unknown"
            attributes[ATTR_STATUS] = "unknown"
        
        self._attributes = attributes
