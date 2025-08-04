"""The lawn mower integration."""

from __future__ import annotations

import logging
from typing import final

from propcache.api import cached_property

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MOWER_NAME,
    DOMAIN,
    LawnMowerActivity,
    LawnMowerEntityFeature,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up lawn mower devices."""
    _LOGGER.debug("Setting up lawn mower for entry: %s", entry.data)
    coordinator = hass.data[DOMAIN]["coordinator" + entry.data[CONF_MOWER_NAME]]
    
    # Ensure we have data before creating entities
    if not coordinator.data:
        _LOGGER.debug("No coordinator data yet, requesting refresh")
        await coordinator.async_request_refresh()
    
    _LOGGER.debug("Got coordinator with %d mowers", len(coordinator.mower))
    
    entities = []
    for mower in coordinator.mower:
        _LOGGER.debug("Checking mower: %s against config: %s", mower.name, entry.data[CONF_MOWER_NAME])
        _LOGGER.debug("Mower object attributes: %s", dir(mower))
        _LOGGER.debug("Mower object vars: %s", vars(mower) if hasattr(mower, '__dict__') else 'No __dict__')
        if mower.name == entry.data[CONF_MOWER_NAME]:
            _LOGGER.debug("Adding mower entity for: %s", mower.name)
            entities.append(GreenWorksLawnMower(coordinator, mower))
    
    if not entities:
        _LOGGER.warning("No mowers found matching name: %s. Available mowers: %s", 
                       entry.data[CONF_MOWER_NAME], 
                       [m.name for m in coordinator.mower])
    
    _LOGGER.debug("Adding %d entities", len(entities))
    async_add_entities(entities)
 



class LawnMowerEntityEntityDescription(EntityDescription):
    """A class that describes lawn mower entities."""


CACHED_PROPERTIES_WITH_ATTR_ = {
    "activity",
    "supported_features",
}


class LawnMowerEntity(Entity):
    """Base class for lawn mower entities."""

    entity_description: LawnMowerEntityEntityDescription
    _attr_activity: LawnMowerActivity | None = None
    _attr_supported_features: LawnMowerEntityFeature = LawnMowerEntityFeature(0)

    @final
    @property
    def state(self) -> str | None:
        """Return the current state."""
        activity = self.activity
        return activity.value if activity else None

    @cached_property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current lawn mower activity."""
        return self._attr_activity

    @cached_property
    def supported_features(self) -> LawnMowerEntityFeature:
        """Flag lawn mower features that are supported."""
        return self._attr_supported_features

    def start_mowing(self) -> None:
        """Start or resume mowing."""
        raise NotImplementedError

    async def async_start_mowing(self) -> None:
        """Start or resume mowing."""
        await self.hass.async_add_executor_job(self.start_mowing)

    def dock(self) -> None:
        """Dock the mower."""
        raise NotImplementedError

    async def async_dock(self) -> None:
        """Dock the mower."""
        await self.hass.async_add_executor_job(self.dock)

    def pause(self) -> None:
        """Pause the lawn mower."""
        raise NotImplementedError

    async def async_pause(self) -> None:
        """Pause the lawn mower."""
        await self.hass.async_add_executor_job(self.pause)


class GreenWorksLawnMower(CoordinatorEntity, LawnMowerEntity):
    """Representation of a GreenWorks lawn mower."""

    def __init__(self, coordinator, mower):
        """Initialize the lawn mower."""
        super().__init__(coordinator)
        self.mower = mower
        
        # Based on GreenWorks Core API, use 'sn' for serial number
        serial_num = getattr(mower, 'sn', None) or \
                    getattr(mower, 'id', None) or \
                    mower.name  # fallback to name
        
        self._attr_unique_id = f"greenworks_{serial_num}"
        self._attr_name = mower.name
        self._attr_icon = "mdi:robot-mower"  # Add an icon
        self._attr_supported_features = (
            LawnMowerEntityFeature.START_MOWING
            | LawnMowerEntityFeature.PAUSE
            | LawnMowerEntityFeature.DOCK
        )
        _LOGGER.debug("Initialized GreenWorks mower: %s with sn: %s, id: %s", 
                     mower.name, getattr(mower, 'sn', 'N/A'), getattr(mower, 'id', 'N/A'))

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current lawn mower activity."""
        _LOGGER.debug("Getting activity for mower %s, coordinator data: %s", 
                     self.mower.name, self.coordinator.data)
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available")
            return LawnMowerActivity.IDLE  # Return IDLE instead of None
        
        # Find the current mower data - match by sn (serial number) or id or name
        current_mower = None
        for mower in self.coordinator.data:
            _LOGGER.debug("Checking mower: %s (sn: %s, id: %s) against %s", 
                         mower.name, getattr(mower, 'sn', 'N/A'), 
                         getattr(mower, 'id', 'N/A'), self.mower.name)
            # Try to match by sn first, then id, then name
            if (getattr(mower, 'sn', None) == getattr(self.mower, 'sn', None) and getattr(mower, 'sn', None)) or \
               (getattr(mower, 'id', None) == getattr(self.mower, 'id', None) and getattr(mower, 'id', None)) or \
               mower.name == self.mower.name:
                current_mower = mower
                break
                
        if not current_mower:
            _LOGGER.warning("Current mower not found in coordinator data for %s", self.mower.name)
            return LawnMowerActivity.IDLE  # Return IDLE instead of None
        
        # Log all available attributes on the current mower
        _LOGGER.debug("Current mower attributes: %s", dir(current_mower))
        _LOGGER.debug("Current mower vars: %s", vars(current_mower) if hasattr(current_mower, '__dict__') else 'No __dict__')
        
        # Check if mower has operating_status with mower_main_state
        operating_status = getattr(current_mower, 'operating_status', None)
        if operating_status:
            _LOGGER.debug("Operating status found: %s", operating_status)
            _LOGGER.debug("Operating status attributes: %s", dir(operating_status))
            _LOGGER.debug("Operating status vars: %s", vars(operating_status) if hasattr(operating_status, '__dict__') else 'No __dict__')
            
            if hasattr(operating_status, 'mower_main_state'):
                state = operating_status.mower_main_state
                _LOGGER.debug("Mower %s main state: %s (type: %s)", current_mower.name, state, type(state))
                
                # Map GreenWorks MowerState enum to Home Assistant activity
                # Based on MowerState enum: STOP_BUTTON_PRESSED=1, PARKED_BY_USER=2, PAUSED=3, 
                # MOWING=4, LEAVING_CHARGING_STATION=5, SEARCHING_FOR_CHARGING_STATION=6, CHARGING=7
                if hasattr(state, 'value'):
                    state_value = state.value
                else:
                    state_value = state
                    
                _LOGGER.debug("State value: %s", state_value)
                    
                if state_value == 4:  # MOWING
                    return LawnMowerActivity.MOWING
                elif state_value == 7:  # CHARGING
                    return LawnMowerActivity.DOCKED
                elif state_value in [1, 2, 3]:  # STOP_BUTTON_PRESSED, PARKED_BY_USER, PAUSED
                    return LawnMowerActivity.PAUSED
                elif state_value in [5, 6]:  # LEAVING_CHARGING_STATION, SEARCHING_FOR_CHARGING_STATION
                    return LawnMowerActivity.DOCKED  # Treating as docked/returning
                else:
                    _LOGGER.debug("Unknown state value %s, defaulting to IDLE", state_value)
                    return LawnMowerActivity.IDLE
            else:
                _LOGGER.debug("Operating status has no mower_main_state attribute")
        else:
            _LOGGER.debug("No operating_status found on mower")
            
        # Fallback to checking status string if available
        status = getattr(current_mower, 'status', '') or ''
        if isinstance(status, str):
            status = status.lower()
        else:
            status = str(status).lower()
            
        _LOGGER.debug("Mower %s fallback status: %s", current_mower.name, status)
        
        if "mowing" in status or "cutting" in status:
            return LawnMowerActivity.MOWING
        elif "charging" in status or "docked" in status:
            return LawnMowerActivity.DOCKED
        elif "paused" in status or "stopped" in status:
            return LawnMowerActivity.PAUSED
        else:
            return LawnMowerActivity.IDLE

    @property
    def state(self) -> str | None:
        """Return the current state."""
        activity = self.activity
        state_value = activity.value if activity else "unknown"
        _LOGGER.debug("Mower %s state: %s (from activity: %s)", self.mower.name, state_value, activity)
        return state_value

    @property
    def battery_level(self) -> int | None:
        """Return the battery level."""
        if not self.coordinator.data:
            return None
        
        # Find the current mower data
        current_mower = None
        for mower in self.coordinator.data:
            if (getattr(mower, 'sn', None) == getattr(self.mower, 'sn', None) and getattr(mower, 'sn', None)) or \
               (getattr(mower, 'id', None) == getattr(self.mower, 'id', None) and getattr(mower, 'id', None)) or \
               mower.name == self.mower.name:
                current_mower = mower
                break
                
        if not current_mower:
            return None
        
        # Get battery level from operating_status
        operating_status = getattr(current_mower, 'operating_status', None)
        if operating_status and hasattr(operating_status, 'battery_status'):
            return operating_status.battery_status
        
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        # Find the current mower data
        current_mower = None
        for mower in self.coordinator.data:
            if (getattr(mower, 'sn', None) == getattr(self.mower, 'sn', None) and getattr(mower, 'sn', None)) or \
               (getattr(mower, 'id', None) == getattr(self.mower, 'id', None) and getattr(mower, 'id', None)) or \
               mower.name == self.mower.name:
                current_mower = mower
                break
                
        if not current_mower:
            return {}
        
        attributes = {}
        
        # From Mower_info class
        if hasattr(current_mower, 'sn'):
            attributes['serial_number'] = current_mower.sn
        if hasattr(current_mower, 'id'):
            attributes['device_id'] = current_mower.id
        if hasattr(current_mower, 'is_online'):
            attributes['is_online'] = current_mower.is_online
        if hasattr(current_mower, 'mac'):
            attributes['mac_address'] = current_mower.mac
        if hasattr(current_mower, 'product_id'):
            attributes['product_id'] = current_mower.product_id
        if hasattr(current_mower, 'firmware_version'):
            attributes['firmware_version'] = current_mower.firmware_version
        if hasattr(current_mower, 'mcu_version'):
            attributes['mcu_version'] = current_mower.mcu_version
        
        # From Mower_operating_status class
        operating_status = getattr(current_mower, 'operating_status', None)
        if operating_status:
            if hasattr(operating_status, 'battery_status'):
                attributes['battery_level'] = operating_status.battery_status
            if hasattr(operating_status, 'mower_main_state'):
                state = operating_status.mower_main_state
                if hasattr(state, 'value'):
                    attributes['mower_state'] = state.value
                    attributes['mower_state_name'] = state.name if hasattr(state, 'name') else str(state)
                else:
                    attributes['mower_state'] = state
            if hasattr(operating_status, 'next_start'):
                attributes['next_start'] = str(operating_status.next_start)
            if hasattr(operating_status, 'request_time'):
                attributes['last_update'] = str(operating_status.request_time)
        
        # From Mower_properties class
        properties = getattr(current_mower, 'properties', None)
        if properties:
            if hasattr(properties, 'is_frost_sensor_on'):
                attributes['frost_sensor'] = properties.is_frost_sensor_on
            if hasattr(properties, 'is_rain_sensor_on'):
                attributes['rain_sensor'] = properties.is_rain_sensor_on
            if hasattr(properties, 'device_blade_usage_time'):
                attributes['blade_usage_time'] = properties.device_blade_usage_time
            if hasattr(properties, 'geofence_latitude'):
                attributes['geofence_latitude'] = properties.geofence_latitude
            if hasattr(properties, 'geofence_longitude'):
                attributes['geofence_longitude'] = properties.geofence_longitude
        
        return attributes

    @property
    def device_info(self):
        """Return device information."""
        # Based on GreenWorks Core API, use 'sn' for serial number
        serial_num = getattr(self.mower, 'sn', None) or \
                    getattr(self.mower, 'id', None) or \
                    self.mower.name  # fallback to name
        
        device_info = {
            "identifiers": {(DOMAIN, str(serial_num))},
            "name": self.mower.name,
            "manufacturer": "GreenWorks",
        }
        
        # Add model info if available
        if hasattr(self.mower, 'product_id'):
            device_info["model"] = f"Product ID: {self.mower.product_id}"
        else:
            device_info["model"] = "Lawn Mower"
            
        # Add serial number
        if hasattr(self.mower, 'sn'):
            device_info["serial_number"] = str(self.mower.sn)
        
        # Add firmware version if available
        if hasattr(self.mower, 'firmware_version'):
            device_info["sw_version"] = str(self.mower.firmware_version)
            
        return device_info

    def start_mowing(self) -> None:
        """Start or resume mowing."""
        try:
            # Based on GreenWorks Core API, use 'sn' or 'id' for API calls
            identifier = getattr(self.mower, 'sn', None) or \
                        getattr(self.mower, 'id', None) or \
                        self.mower.name
            
            self.coordinator.api.start_mowing(identifier)
        except Exception as ex:
            _LOGGER.error("Error starting mowing: %s", ex)

    def pause(self) -> None:
        """Pause the lawn mower."""
        try:
            # Based on GreenWorks Core API, use 'sn' or 'id' for API calls
            identifier = getattr(self.mower, 'sn', None) or \
                        getattr(self.mower, 'id', None) or \
                        self.mower.name
            
            self.coordinator.api.pause_mowing(identifier)
        except Exception as ex:
            _LOGGER.error("Error pausing mowing: %s", ex)

    def dock(self) -> None:
        """Dock the mower."""
        try:
            # Based on GreenWorks Core API, use 'sn' or 'id' for API calls
            identifier = getattr(self.mower, 'sn', None) or \
                        getattr(self.mower, 'id', None) or \
                        self.mower.name
            
            self.coordinator.api.return_to_dock(identifier)
        except Exception as ex:
            _LOGGER.error("Error returning to dock: %s", ex)

