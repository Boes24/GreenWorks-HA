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
        self._attr_unique_id = f"greenworks_{mower.serial_number}"
        self._attr_name = mower.name
        self._attr_supported_features = (
            LawnMowerEntityFeature.START_MOWING
            | LawnMowerEntityFeature.PAUSE
            | LawnMowerEntityFeature.DOCK
        )
        _LOGGER.debug("Initialized GreenWorks mower: %s with serial: %s", mower.name, mower.serial_number)

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current lawn mower activity."""
        _LOGGER.debug("Getting activity for mower %s, coordinator data: %s", 
                     self.mower.name, self.coordinator.data)
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available")
            return None
        
        # Find the current mower data
        current_mower = None
        for mower in self.coordinator.data:
            _LOGGER.debug("Checking mower: %s (serial: %s) against %s", 
                         mower.name, mower.serial_number, self.mower.serial_number)
            if mower.serial_number == self.mower.serial_number:
                current_mower = mower
                break
                
        if not current_mower:
            _LOGGER.debug("Current mower not found in coordinator data")
            return None
            
        # Map GreenWorks status to Home Assistant activity
        status = current_mower.status.lower() if current_mower.status else ""
        _LOGGER.debug("Mower %s status: %s", current_mower.name, status)
        
        if "mowing" in status or "cutting" in status:
            return LawnMowerActivity.MOWING
        elif "charging" in status or "docked" in status:
            return LawnMowerActivity.DOCKED
        elif "paused" in status or "stopped" in status:
            return LawnMowerActivity.PAUSED
        elif "returning" in status:
            return LawnMowerActivity.DOCKED  # Treating returning as docked
        elif "error" in status:
            return LawnMowerActivity.ERROR
        else:
            return LawnMowerActivity.IDLE

    @property
    def state(self) -> str | None:
        """Return the current state."""
        activity = self.activity
        return activity.value if activity else None

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
            if mower.serial_number == self.mower.serial_number:
                current_mower = mower
                break
                
        if not current_mower:
            return {}
            
        attributes = {
            "serial_number": current_mower.serial_number,
            "model": getattr(current_mower, 'model', 'Unknown'),
            "battery_level": getattr(current_mower, 'battery_level', None),
            "cutting_height": getattr(current_mower, 'cutting_height', None),
            "status": getattr(current_mower, 'status', 'Unknown'),
        }
        
        # Only include non-None values
        return {k: v for k, v in attributes.items() if v is not None}

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.mower.serial_number)},
            "name": self.mower.name,
            "manufacturer": "GreenWorks",
            "model": getattr(self.mower, 'model', 'Lawn Mower'),
            "serial_number": self.mower.serial_number,
        }

    def start_mowing(self) -> None:
        """Start or resume mowing."""
        try:
            self.coordinator.api.start_mowing(self.mower.serial_number)
        except Exception as ex:
            _LOGGER.error("Error starting mowing: %s", ex)

    def pause(self) -> None:
        """Pause the lawn mower."""
        try:
            self.coordinator.api.pause_mowing(self.mower.serial_number)
        except Exception as ex:
            _LOGGER.error("Error pausing mowing: %s", ex)

    def dock(self) -> None:
        """Dock the mower."""
        try:
            self.coordinator.api.return_to_dock(self.mower.serial_number)
        except Exception as ex:
            _LOGGER.error("Error returning to dock: %s", ex)

