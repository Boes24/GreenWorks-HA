"""GreenWorks sensor platform: exposes battery and schedule details as sensors."""

from __future__ import annotations

from typing import Any, cast
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up GreenWorks sensors for a config entry."""
    mower_name: str = cast(str, entry.data.get(CONF_MOWER_NAME, ""))
    key = "coordinator" + mower_name
    coordinator: GreenWorksDataCoordinator = hass.data[DOMAIN][key]

    entities: list[SensorEntity] = []
    entities.append(GreenWorksBatterySensor(coordinator, mower_name))
    entities.append(GreenWorksNextStartSensor(coordinator, mower_name))
    entities.append(GreenWorksBladeUsageSensor(coordinator, mower_name))

    async_add_entities(entities, update_before_add=True)


class _GreenWorksBaseSensor(CoordinatorEntity[GreenWorksDataCoordinator], SensorEntity):
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


class GreenWorksBatterySensor(_GreenWorksBaseSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator: GreenWorksDataCoordinator, mower_name: str) -> None:
        super().__init__(coordinator, mower_name)
        self._attr_name = f"{mower_name} Battery"
        # Use SN or id for uniqueness
        mower = self._current_mower
        uid = getattr(mower, "sn", None) or getattr(mower, "id", mower_name)
        self._attr_unique_id = f"{uid}_battery"

    @property
    def native_value(self) -> int | None:
        mower = self._current_mower
        if mower is None:
            return None
        operating_status = getattr(mower, "operating_status", None)
        if operating_status is None:
            return None
        val = getattr(operating_status, "battery_status", None)
        try:
            if val is None:
                return None
            # Normalize "-1" or invalid to None
            val_int = int(val)
            if val_int < 0 or val_int > 100:
                return None
            return val_int
        except Exception:
            return None


class GreenWorksNextStartSensor(_GreenWorksBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: GreenWorksDataCoordinator, mower_name: str) -> None:
        super().__init__(coordinator, mower_name)
        self._attr_name = f"{mower_name} Next Start"
        mower = self._current_mower
        uid = getattr(mower, "sn", None) or getattr(mower, "id", mower_name)
        self._attr_unique_id = f"{uid}_next_start"

    @property
    def native_value(self):  # datetime | None, but keep flexible for HA versions
        mower = self._current_mower
        if mower is None:
            return None
        operating_status = getattr(mower, "operating_status", None)
        if operating_status is None:
            return None
        return getattr(operating_status, "next_start", None)


class GreenWorksBladeUsageSensor(_GreenWorksBaseSensor):
    """Blade usage time sensor. Exposes raw string from properties."""

    def __init__(self, coordinator: GreenWorksDataCoordinator, mower_name: str) -> None:
        super().__init__(coordinator, mower_name)
        self._attr_name = f"{mower_name} Blade Usage"
        mower = self._current_mower
        uid = getattr(mower, "sn", None) or getattr(mower, "id", mower_name)
        self._attr_unique_id = f"{uid}_blade_usage"

    @property
    def icon(self) -> str | None:
        return "mdi:knife"

    @property
    def native_value(self) -> str | None:
        mower = self._current_mower
        if mower is None:
            return None
        props = getattr(mower, "properties", None)
        if props is None:
            return None
        val = getattr(props, "device_blade_usage_time", None)
        if val is None:
            return None
        # Return raw string; format is vendor-defined
        return str(val)
