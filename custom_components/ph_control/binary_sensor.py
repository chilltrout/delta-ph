"""Support for pH Control binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
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
    CONF_NOISE_FILTER,
    DEFAULT_SETPOINT,
    DEFAULT_NOISE_FILTER,
    ATTR_CURRENT_PH,
    ATTR_SETPOINT,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the pH Control binary sensor from a config entry."""
    config = config_entry.data
    
    source_entity = config.get(CONF_SOURCE_ENTITY)
    setpoint = config.get(CONF_SETPOINT, DEFAULT_SETPOINT)
    noise_filter = config.get(CONF_NOISE_FILTER, DEFAULT_NOISE_FILTER)
    
    # Get any updated options from config entry
    if config_entry.options:
        setpoint = config_entry.options.get(CONF_SETPOINT, setpoint)
        noise_filter = config_entry.options.get(CONF_NOISE_FILTER, noise_filter)

    entities = [
        PHControlBinarySensor(
            hass,
            config_entry.entry_id,
            source_entity,
            setpoint,
            noise_filter,
            "High pH",
            "high",
            True, # On when pH is above setpoint + noise_filter
        ),
        PHControlBinarySensor(
            hass,
            config_entry.entry_id,
            source_entity,
            setpoint,
            noise_filter,
            "Low pH",
            "low",
            False, # On when pH is below setpoint - noise_filter
        ),
    ]
    
    async_add_entities(entities, True)


class PHControlBinarySensor(BinarySensorEntity):
    """Representation of a pH Control Binary Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        source_entity: str,
        setpoint: float,
        noise_filter: float,
        suffix: str,
        condition: str,
        check_above: bool,
    ) -> None:
        """Initialize the pH Control binary sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._setpoint = setpoint
        self._noise_filter = noise_filter
        self._condition = condition
        self._check_above = check_above
        self._current_ph = None
        
        self._attr_name = f"pH {suffix} {source_entity}"
        self._attr_unique_id = f"{entry_id}_{source_entity}_{condition}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        
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
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        if self._current_ph is None:
            return False
            
        if self._check_above:
            return self._current_ph > (self._setpoint + self._noise_filter)
        else:
            return self._current_ph < (self._setpoint - self._noise_filter)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the binary sensor."""
        return {
            ATTR_CURRENT_PH: self._current_ph,
            ATTR_SETPOINT: self._setpoint,
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
        self._current_ph = value
