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
        self._channel           = None
    #endof __init__()


    @property
    def device_info(self):
        """Information about this entity/device."""
        conf_url = f"https://{self._host.api._host}:{self._host.api._port}" if self._host.api._use_https else f"http://{self._host.api._host}:{self._host.api._port}"
        if self._host.api.is_nvr and self._channel is not None:
            return {
                "identifiers":          {(DOMAIN, f"{self._host.unique_id}_ch{self._channel}")},
                "via_device":           (DOMAIN, self._host.unique_id),
                "name":                 self._host.api.camera_name(self._channel),
                "model":                self._host.api.camera_model(self._channel),
                "manufacturer":         self._host.api.manufacturer,
                "configuration_url":    conf_url,
            }

        return {
            "identifiers":          {(DOMAIN, self._host.unique_id)},
            "connections":          {(CONNECTION_NETWORK_MAC, self._host.api.mac_address)},
            "name":                 self._host.api.nvr_name,
            "sw_version":           self._host.api.sw_version,
            "hw_version":           self._host.api.hardware_version,
            "model":                self._host.api.model,
            "manufacturer":         self._host.api.manufacturer,
            "configuration_url":    conf_url,
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
