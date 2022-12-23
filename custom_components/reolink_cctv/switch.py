"""This component provides support many for Reolink IP cameras switches."""
import asyncio
import logging
from   typing import Optional

from homeassistant.core                 import HomeAssistant
from homeassistant.components.switch    import SwitchDeviceClass
from homeassistant.helpers.entity       import ToggleEntity, EntityCategory

from .host      import ReolinkHost
from .const     import HOST, DOMAIN
from .entity    import ReolinkCoordinatorEntity

_LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
# Setup switches-platform entry
##########################################################################################################################################################
async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_devices):
    """Set up the Reolink IP Camera switches."""

    devices = []
    host: ReolinkHost = hass.data[DOMAIN][config_entry.entry_id][HOST]

    global_added = False
    for channel in host.api.channels:
        capabilities: list[str] = await host.api.get_switchable_capabilities(channel)
        for capability in capabilities:
            if capability == "audio":
                devices.append(AudioSwitch(hass, config_entry, channel))
            elif capability == "siren":
                devices.append(SirenSwitch(hass, config_entry, channel))
            elif capability == "irLights":
                devices.append(IRLightsSwitch(hass, config_entry, channel))
            elif capability == "doorbellLight":
                devices.append(DoorbellLightSwitch(hass, config_entry, channel))
            elif capability == "spotlight":
                devices.append(SpotLightSwitch(hass, config_entry, channel))

            if not global_added:
                # Let's assume that if we are an NVR - then all channels have THE SAME capabilities-levels.
                if capability == "ftp":
                    devices.append(FTPSwitch(hass, config_entry))
                elif capability == "email":
                    devices.append(EmailSwitch(hass, config_entry))
                elif capability == "push":
                    devices.append(PushSwitch(hass, config_entry))
                elif capability == "recording":
                    devices.append(RecordingSwitch(hass, config_entry))
        if not global_added:
            global_added = True
    #for channel in host.api.channels:

    async_add_devices(devices, update_before_add = True)
#endof async_setup_entry()


##########################################################################################################################################################
# FTP
##########################################################################################################################################################
class FTPSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._channel = channel
        #self._attr_entity_category = EntityCategory.CONFIG
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_ftpSwitch_{self._host.unique_id}"
        else:
            return f"reolink_ftpSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} FTP"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} FTP"
    #endof name


    @property
    def is_on(self):
        """Camera Motion FTP upload Status."""
        return self._host.api.ftp_enabled(self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:folder-upload"
        return "mdi:folder-remove"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable motion ftp recording."""
        await self._host.api.set_ftp(self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable motion ftp recording."""
        await self._host.api.set_ftp(self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class FTPSwitch


##########################################################################################################################################################
# Email
##########################################################################################################################################################
class EmailSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._channel = channel
        #self._attr_entity_category = EntityCategory.CONFIG
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_emailSwitch_{self._host.unique_id}"
        else:
            return f"reolink_emailSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} Email"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} Email"
    #enfof name


    @property
    def is_on(self):
        """Camera Motion email upload Status."""
        return self._host.api.email_enabled(self._channel)
    #enfof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:email"
        return "mdi:email-outline"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable motion email notification."""
        await self._host.api.set_email(self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable motion email notification."""
        await self._host.api.set_email(self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class EmailSwitch


##########################################################################################################################################################
# IR-light
##########################################################################################################################################################
class IRLightsSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._attr_entity_category  = EntityCategory.CONFIG
        self._channel               = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_irLightsSwitch_{self._host.unique_id}"
        else:
            return f"reolink_irLightsSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} IR lights"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} IR lights"
    #endof name


    @property
    def is_on(self):
        return self._host.api.ir_enabled(0 if self._channel is None else self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:flashlight"
        return "mdi:flashlight-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable motion ir lights."""
        await self._host.api.set_ir_lights(0 if self._channel is None else self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable motion ir lights."""
        await self._host.api.set_ir_lights(0 if self._channel is None else self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class IRLightsSwitch


##########################################################################################################################################################
# Doorbell-light
##########################################################################################################################################################
class DoorbellLightSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._attr_entity_category  = EntityCategory.CONFIG
        self._channel               = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_doorbellLightSwitch_{self._host.unique_id}"
        else:
            return f"reolink_doorbellLightSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} doorbell light"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} doorbell light"
    #endof name


    @property
    def is_on(self):
        return self._host.api.doorbell_light_enabled(0 if self._channel is None else self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:flashlight"
        return "mdi:flashlight-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable doorbell light."""
        await self._host.api.set_power_led(0 if self._channel is None else self._channel, True, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable doorbell light."""
        await self._host.api.set_power_led(0 if self._channel is None else self._channel, True, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class DoorbellLightSwitch


##########################################################################################################################################################
# Spotlight
##########################################################################################################################################################
class SpotLightSwitch(ReolinkCoordinatorEntity, ToggleEntity):
    """An implementation of a Reolink IP camera spotlight (WhiteLed) switch"""

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._attr_entity_category  = EntityCategory.CONFIG
        self._channel               = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_SpotlightSwitch_{self._host.unique_id}"
        else:
            return f"reolink_SpotlightSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} Spotlight"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} Spotlight"
    #endof name


    @property
    def is_on(self):
        return self._host.api.whiteled_enabled(0 if self._channel is None else self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:lightbulb-spot"
        else:
            return "mdi:lightbulb-spot-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable spotlight."""
        # Uses a call to a simple turn on routine which sets night mode on, auto, 100% bright.

        await self._host.api.set_spotlight(0 if self._channel is None else self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable spotlight."""
        await self._host.api.set_spotlight(0 if self._channel is None else self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()


    async def set_schedule(self, **kwargs):
        # To set the schedule for when night mode on and auto off.
        # Requires a start and end time in hours and minutes.
        # If not provided will default to start 18:00, end 06:00.
        #
        # If being set will cause night mode and non-auto to be set.
        #
        _starthour = 18
        _startmin = 0
        _endhour = 6
        _endmin = 0

        for key, value in kwargs.items():
            if key == "starthour":
                _starthour = value
            elif key == "startmin":
                _startmin = value
            elif key == "endhour":
                _endhour = value
            elif key == "endmin":
                _endmin = value

        await self._host.api.set_spotlight_lighting_schedule(0 if self._channel is None else self._channel, _endhour, _endmin, _starthour, _startmin)
        await self.request_refresh()
    #endof set_schedule()
#endof class SpotLightSwitch


##########################################################################################################################################################
# Siren
##########################################################################################################################################################
class SirenSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._attr_entity_category  = EntityCategory.CONFIG
        self._channel               = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_SirenSwitch_{self._host.unique_id}"
        else:
            return f"reolink_SirenSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} Siren"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} Siren"
    #endof name


    @property
    def is_on(self):
        # return self._host.api.audio_alarm_state
        return self._host.api.audio_alarm_enabled(self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        """Icon of the switch."""
        if self.is_on:
            return "mdi:alarm"
        else:
            return "mdi:alarm-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Turn On Siren."""
        # Uses call to simple turn on routine which sets night mode on, auto, 100% bright.
        await self._host.api.set_siren(0 if self._channel is None else self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Turn Off Siren."""
        await self._host.api.set_siren(0 if self._channel is None else self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class SirenSwitch


##########################################################################################################################################################
# Push
##########################################################################################################################################################
class PushSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        #self._attr_entity_category = EntityCategory.CONFIG
        self._channel = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_pushSwitch_{self._host.unique_id}"
        else:
            return f"reolink_pushSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} push notifications"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} push notifications"
    #endof name


    @property
    def is_on(self):
        return self._host.api.push_enabled(self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:message"
        return "mdi:message-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable push notifications."""
        await self._host.api.set_push(self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable push notifications."""
        await self._host.api.set_push(self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class PushSwitch


##########################################################################################################################################################
# Recording
##########################################################################################################################################################
class RecordingSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        #self._attr_entity_category = EntityCategory.CONFIG
        self._channel = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_recordingSwitch_{self._host.unique_id}"
        else:
            return f"reolink_recordingSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} recording"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} recording"
    #endof name


    @property
    def is_on(self):
        return self._host.api.recording_enabled(self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:filmstrip"
        return "mdi:filmstrip-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable recording."""
        await self._host.api.set_recording(self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable recording."""
        await self._host.api.set_recording(self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class RecordingSwitch


##########################################################################################################################################################
# Audio
##########################################################################################################################################################
class AudioSwitch(ReolinkCoordinatorEntity, ToggleEntity):

    def __init__(self, hass, config, channel: Optional[int] = None):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ToggleEntity.__init__(self)

        self._attr_entity_category  = EntityCategory.CONFIG
        self._channel               = channel
    #endof __init__()


    @property
    def unique_id(self):
        if self._channel is None:
            return f"reolink_audioSwitch_{self._host.unique_id}"
        else:
            return f"reolink_audioSwitch_{self._host.unique_id}_{self._channel}"
    #endof unique_id


    @property
    def name(self):
        if self._channel is None:
            return f"{self._host.api.nvr_name} record audio"
        else:
            cam_name = self._host.api.camera_name(self._channel)
            return f"{cam_name} record audio"
    #endof name


    @property
    def is_on(self):
        return self._host.api.audio_state(0 if self._channel is None else self._channel)
    #endof is_on


    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH
    #endof device_class


    @property
    def icon(self):
        if self.is_on:
            return "mdi:volume-high"
        return "mdi:volume-off"
    #endof icon


    async def async_turn_on(self, **kwargs):
        """Enable audio recording."""
        await self._host.api.set_audio(0 if self._channel is None else self._channel, True)
        await self.request_refresh()
    #endof async_turn_on()


    async def async_turn_off(self, **kwargs):
        """Disable audio recording."""
        await self._host.api.set_audio(0 if self._channel is None else self._channel, False)
        await self.request_refresh()
    #endof async_turn_off()
#endof class AudioSwitch
