"""Green Works integration for Home Assistant."""

from datetime import timedelta
import logging

from homeassistant import config_entries, core
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TIME_ZONE
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from GreenWorksAPI.GreenWorksAPI import GreenWorksAPI, Mower, UnauthorizedException


from .const import CONF_MOWER_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up Green Works from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        api = await hass.async_add_executor_job(
            GreenWorksAPI, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD], entry.data[CONF_TIME_ZONE]
        )
    except UnauthorizedException as err:
        raise ConfigEntryAuthFailed(err) from err

    coordinator = GreenWorksDataCoordinator(hass, api, entry.data[CONF_MOWER_NAME])
    hass.data[DOMAIN]["coordinator" + entry.data[CONF_MOWER_NAME]] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

class GreenWorksDataCoordinator(DataUpdateCoordinator):
    """Get and update the latest data."""

    def __init__(self, hass: core.HomeAssistant, api: GreenWorksAPI, mower_name) -> None:
        """Initialize the GreenWorksDataCoordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="GreenWorksData",
            update_interval=timedelta(seconds=120),
        )
        self.api = api
        self.mower_name = mower_name
        self._mower:list[Mower]

    async def _async_update_data(self):
        try:
            self._mower = await self.hass.async_add_executor_job(self.api.get_devices)
        except KeyError as ex:
            raise UpdateFailed("Problems calling GreenWorks") from ex

    def get_first_mower(self) -> Mower:
        """Return the first mower of all users mowers."""
        return self._mower[0]