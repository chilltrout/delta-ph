"""Constants for the pH Control integration."""

DOMAIN = "ph_control"

CONF_SOURCE_ENTITY = "source_entity"
CONF_SETPOINT = "setpoint"
CONF_TIME_WINDOW = "time_window"
CONF_MIN_AMPLITUDE = "min_amplitude"
CONF_NOISE_FILTER = "noise_filter"
CONF_MIN_DURATION = "min_duration"

DEFAULT_NAME = "pH Control"
DEFAULT_SETPOINT = 8.2
DEFAULT_TIME_WINDOW = 24  # hours
DEFAULT_MIN_AMPLITUDE = 0.05
DEFAULT_NOISE_FILTER = 0.02
DEFAULT_MIN_DURATION = 60  # seconds

ATTR_OSCILLATIONS = "oscillations_24h"
ATTR_AVERAGE_AMPLITUDE = "average_amplitude"
ATTR_MAX_AMPLITUDE = "max_amplitude"
ATTR_LAST_AMPLITUDE = "last_amplitude"
ATTR_TREND = "amplitude_trend"
ATTR_LAST_PEAK = "last_peak_time"
ATTR_LAST_TROUGH = "last_trough_time"
ATTR_STATUS = "alkalinity_status"
