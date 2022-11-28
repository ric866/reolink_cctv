"""Reolink parent entity class."""

from homeassistant.core                         import HomeAssistant
from homeassistant.helpers.device_registry      import CONNECTION_NETWORK_MAC
from homeassistant.helpers.update_coordinator   import CoordinatorEntity

from .const import DOMAIN, HOST, DEVICE_CONFIG_UPDATE_COORDINATOR
from .host  import ReolinkHost


class ReolinkCoordinatorEntity(CoordinatorEntity):
    """Parent class for Reolink Entities."""

    def __init__(self, hass: HomeAssistant, config):
        super().__init__(hass.data[DOMAIN][config.entry_id][DEVICE_CONFIG_UPDATE_COORDINATOR])

        self._host: ReolinkHost = hass.data[DOMAIN][config.entry_id][HOST]
        self._hass              = hass
        self._state             = False
    #endof __init__()


    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers":          {(DOMAIN, self._host.unique_id)},
            "connections":          {(CONNECTION_NETWORK_MAC, self._host.api.mac_address)},
            "name":                 self._host.api.nvr_name,
            "sw_version":           self._host.api.sw_version,
            "hw_version":           self._host.api.hardware_version,
            "model":                self._host.api.model,
            "manufacturer":         self._host.api.manufacturer,
            "configuration_url":    f"https://{self._host.api._host}:{self._host.api._port}" if self._host.api._use_https else f"http://{self._host.api._host}:{self._host.api._port}"
        }
    #endof device_info


    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._host.api.session_active
    #endof available


    async def request_refresh(self):
        """Call the coordinator to update the API."""
        await self.coordinator.async_request_refresh()
        #await self.async_write_ha_state()
    #endof request_refresh()
#endof class ReolinkCoordinatorEntity
