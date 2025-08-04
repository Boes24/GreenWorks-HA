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


# Legacy platform setup - not needed for modern integrations
# async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
#     """Set up the lawn_mower component."""
#     component = hass.data[DATA_COMPONENT] = EntityComponent[LawnMowerEntity](
#         _LOGGER, DOMAIN, hass, SCAN_INTERVAL
#     )
#     await component.async_setup(config)
#
#     component.async_register_entity_service(
#         SERVICE_START_MOWING,
#         {},
#         "async_start_mowing",
#         [LawnMowerEntityFeature.START_MOWING],
#     )
#     component.async_register_entity_service(
#         SERVICE_PAUSE, {}, "async_pause", [LawnMowerEntityFeature.PAUSE]
#     )
#     component.async_register_entity_service(
#         SERVICE_DOCK, {}, "async_dock", [LawnMowerEntityFeature.DOCK]
#     )
#
#     return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up lawn mower devices."""
    coordinator = hass.data[DOMAIN]["coordinator" + entry.data[CONF_MOWER_NAME]]
    
    entities = []
    for mower in coordinator.mower:
        if mower.name == entry.data[CONF_MOWER_NAME]:
            entities.append(GreenWorksLawnMower(coordinator, mower))
    
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

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current lawn mower activity."""
        if not self.coordinator.data:
            return None
        
        # Find the current mower data
        current_mower = None
        for mower in self.coordinator.data:
            if mower.serial_number == self.mower.serial_number:
                current_mower = mower
                break
                
        if not current_mower:
            return None
            
        # Map GreenWorks status to Home Assistant activity
        status = current_mower.status.lower() if current_mower.status else ""
        
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
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

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

