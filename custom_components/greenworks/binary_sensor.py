"""GreenWorks binary_sensor platform: frost and rain sensors."""

from __future__ import annotations

from typing import Any, cast
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GreenWorksDataCoordinator
from .const import CONF_MOWER_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up GreenWorks binary sensors for a config entry."""
    mower_name: str = cast(str, entry.data.get(CONF_MOWER_NAME, ""))
    key = "coordinator" + mower_name
    coordinator: GreenWorksDataCoordinator = hass.data[DOMAIN][key]

    entities: list[BinarySensorEntity] = []
    entities.append(GreenWorksFrostSensor(coordinator, mower_name))
    entities.append(GreenWorksRainSensor(coordinator, mower_name))

    async_add_entities(entities, update_before_add=True)


class _GreenWorksBaseBinary(CoordinatorEntity[GreenWorksDataCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: GreenWorksDataCoordinator, mower_name: str) -> None:
        super().__init__(coordinator)
        self._mower_name = mower_name

    @property
    def _current_mower(self):
        data = self.coordinator.data or []
        for m in data:
            try:
                if getattr(m, "name", None) == self._mower_name:
                    return m
            except Exception:
                continue
        return None

    @property
    def available(self) -> bool:
        mower = self._current_mower
        base_available = bool(super().available)
        mower_online = bool(getattr(mower, "is_online", True)) if mower is not None else False
        return base_available and mower_online

    @property
    def device_info(self) -> dict[str, Any]:
        mower = self._current_mower
        identifiers = {(
            DOMAIN,
            str(getattr(mower, "sn", None) or getattr(mower, "id", self._mower_name)),
        )}
        return {
            "identifiers": identifiers,
            "manufacturer": "GreenWorks",
            "model": getattr(mower, "model", "GreenWorks Mower"),
            "name": self._mower_name,
        }


class GreenWorksFrostSensor(_GreenWorksBaseBinary):
    _attr_device_class = BinarySensorDeviceClass.COLD

    def __init__(self, coordinator: GreenWorksDataCoordinator, mower_name: str) -> None:
        super().__init__(coordinator, mower_name)
        self._attr_name = f"{mower_name} Frost"
        mower = self._current_mower
        uid = getattr(mower, "sn", None) or getattr(mower, "id", mower_name)
        self._attr_unique_id = f"{uid}_frost"

    @property
    def is_on(self) -> bool | None:
        mower = self._current_mower
        if mower is None:
            return None
        props = getattr(mower, "properties", None)
        if props is None:
            return None
        val = getattr(props, "is_frost_sensor_on", None)
        return bool(val) if val is not None else None


class GreenWorksRainSensor(_GreenWorksBaseBinary):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, coordinator: GreenWorksDataCoordinator, mower_name: str) -> None:
        super().__init__(coordinator, mower_name)
        self._attr_name = f"{mower_name} Rain"
        mower = self._current_mower
        uid = getattr(mower, "sn", None) or getattr(mower, "id", mower_name)
        self._attr_unique_id = f"{uid}_rain"

    @property
    def is_on(self) -> bool | None:
        mower = self._current_mower
        if mower is None:
            return None
        props = getattr(mower, "properties", None)
        if props is None:
            return None
        val = getattr(props, "is_rain_sensor_on", None)
        return bool(val) if val is not None else None
