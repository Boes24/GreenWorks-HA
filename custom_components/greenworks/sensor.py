from datetime import timedelta
import logging

from .__init__ import GreenWorksDataCoordinator

from homeassistant import core

from homeassistant.components.sensor import SensorEntity

from homeassistant.const import UnitOfTemperature

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MOWER_NAME

_LOGGER = logging.getLogger(__name__)

UPDATE_DELAY = timedelta(seconds=120)


async def async_setup_entry(hass: core.HomeAssistant, entry, async_add_entities):
    dataservice = hass.data[DOMAIN].get("coordinator"+entry.data[CONF_MOWER_NAME])
    if not dataservice:
        _LOGGER.error("No data service found for the specified mower")
        return
    
    entities = []
    entities.append(MowerBatterySensor(dataservice))
    entities.append(MowerMainStateSensor(dataservice))
    entities.append(MowerNextStartSensor(dataservice))
    entities.append(MowerFrostSensor(dataservice))
    entities.append(MowerRainSensor(dataservice))
    entities.append(MowerBladeUsageSensor(dataservice))

    _LOGGER.debug("Adding entities for mower: %s", entry.data[CONF_MOWER_NAME])
    async_add_entities(entities)


class MowerBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mower Battery Sensor."""

    def __init__(self, dataservice: GreenWorksDataCoordinator):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Battery Level"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._dataservice.get_first_mower().operating_status.battery_status
    

class MowerMainStateSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mower Main State Sensor."""

    def __init__(self, dataservice: GreenWorksDataCoordinator):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Current State"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._dataservice.get_first_mower().operating_status.mower_main_state
    
class MowerNextStartSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mower Next Start Sensor."""

    def __init__(self, dataservice: GreenWorksDataCoordinator):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Next Start"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._dataservice.get_first_mower().operating_status.next_start
    
class MowerFrostSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mower Frost Sensor."""

    def __init__(self, dataservice: GreenWorksDataCoordinator):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Frost Sensor"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._dataservice.get_first_mower().properties.is_frost_sensor_on
    
class MowerRainSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mower Rain Sensor."""

    def __init__(self, dataservice: GreenWorksDataCoordinator):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Rain Sensor"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._dataservice.get_first_mower().properties.is_rain_sensor_on
    

class MowerBladeUsageSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mower Blade Usage Sensor."""

    def __init__(self, dataservice: GreenWorksDataCoordinator):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Blade Usage Time"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._dataservice.get_first_mower().operating_status.blade_usage

    