"""Constants for the pH Control integration."""

DOMAIN = "ph_control"

# Configuration constants
CONF_SOURCE_ENTITY = "source_entity"
CONF_SETPOINT = "setpoint"
CONF_TIME_WINDOW = "time_window"
CONF_MIN_AMPLITUDE = "min_amplitude"
CONF_NOISE_FILTER = "noise_filter"
CONF_MIN_DURATION = "min_duration"

# Default values
DEFAULT_SETPOINT = 8.2  # Keeping at 8.2 for CO₂ injection control
DEFAULT_TIME_WINDOW = 300
DEFAULT_MIN_AMPLITUDE = 0.1
DEFAULT_NOISE_FILTER = 0.05
DEFAULT_MIN_DURATION = 30

# Attributes
ATTR_OSCILLATIONS = "oscillations"
ATTR_CURRENT_STATE = "current_state"
ATTR_LAST_CHANGE = "last_change"
ATTR_CURRENT_PH = "current_ph"
ATTR_SETPOINT = "setpoint"
ATTR_TREND = "trend"
ATTR_AMPLITUDE = "amplitude"
ATTR_RISING = "rising"
ATTR_FALLING = "falling"
ATTR_STABLE = "stable"
ATTR_DURATION = "duration"
