"""This component provides support for Reolink IP cameras."""
import logging

from datetime   import datetime
from typing     import Union

import voluptuous as vol

from homeassistant.core                 import HomeAssistant
from homeassistant.components.camera    import SUPPORT_STREAM, Camera
from homeassistant.components.ffmpeg    import DATA_FFMPEG
from homeassistant.helpers              import config_validation as cv, entity_platform

from .const import (
    DOMAIN,
    DOMAIN_DATA,
    HOST,
    LAST_RECORD,
    SERVICE_PTZ_CONTROL,
    SERVICE_CLEANUP_THUMBNAILS,
    SERVICE_SET_BACKLIGHT,
    SERVICE_SET_DAYNIGHT,
    SERVICE_SET_SENSITIVITY,
    SUPPORT_PLAYBACK,
    SUPPORT_PTZ,
)
from .entity  import ReolinkCoordinatorEntity
from .typings import VoDRecord
from .host    import ReolinkHost

_LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
# CAMERA ENTRY SETUP
##########################################################################################################################################################
async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_devices):
    """Set up a Reolink IP Camera."""

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_SET_SENSITIVITY,
        {
            vol.Required("sensitivity"): cv.positive_int,
            vol.Optional("preset"): cv.positive_int
        },
        SERVICE_SET_SENSITIVITY,
    )

    platform.async_register_entity_service(
        SERVICE_SET_DAYNIGHT,
        {
            vol.Required("mode"): cv.string
        },
        SERVICE_SET_DAYNIGHT,
    )

    platform.async_register_entity_service(
        SERVICE_SET_BACKLIGHT,
        {
            vol.Required("mode"): cv.string
        },
        SERVICE_SET_BACKLIGHT,
    )

    platform.async_register_entity_service(
        SERVICE_PTZ_CONTROL,
        {
            vol.Required("command"): cv.string,
            vol.Optional("preset"): cv.positive_int,
            vol.Optional("speed"): cv.positive_int
        },
        SERVICE_PTZ_CONTROL,
        [SUPPORT_PTZ],
    )

    platform.async_register_entity_service(
        SERVICE_CLEANUP_THUMBNAILS,
        {
            vol.Optional("older_than"): cv.datetime
        },
        SERVICE_CLEANUP_THUMBNAILS,
        [SUPPORT_PLAYBACK],
    )

    host: ReolinkHost = hass.data[DOMAIN][config_entry.entry_id][HOST]

    cameras = []
    for channel in host.api.channels:
        streams = ["main", "sub", "images"]
        if host.api.protocol == "rtmp":
            streams.append("ext")

        for stream in streams:
            cameras.append(ReolinkCamera(hass, config_entry, channel, stream))

    async_add_devices(cameras, update_before_add = True)
#endof async_setup_entry()


##########################################################################################################################################################
# Camera class
##########################################################################################################################################################
class ReolinkCamera(ReolinkCoordinatorEntity, Camera):
    """An implementation of a Reolink IP camera."""

    def __init__(self, hass, config, channel, stream):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        Camera.__init__(self)

        if self.enabled and channel not in self._host.cameras:
            self._host.cameras[channel] = self

        self._channel = channel
        self._stream = stream
        self._ffmpeg = self._hass.data[DATA_FFMPEG]

        self._attr_name = f"{self._host.api.camera_name(self._channel)} {self._stream}"
        self._attr_unique_id = f"reolink_camera_{self._host.unique_id}_{self._channel}_{self._stream}"
        self._attr_entity_registry_enabled_default = stream == "main"

        self._ptz_commands = {
            "AUTO":         "Auto",
            "DOWN":         "Down",
            "FOCUSDEC":     "FocusDec",
            "FOCUSINC":     "FocusInc",
            "LEFT":         "Left",
            "LEFTDOWN":     "LeftDown",
            "LEFTUP":       "LeftUp",
            "RIGHT":        "Right",
            "RIGHTDOWN":    "RightDown",
            "RIGHTUP":      "RightUp",
            "STOP":         "Stop",
            "TOPOS":        "ToPos",
            "UP":           "Up",
            "ZOOMDEC":      "ZoomDec",
            "ZOOMINC":      "ZoomInc",
        }
        self._daynight_modes = {
            "AUTO":             "Auto",
            "COLOR":            "Color",
            "BLACKANDWHITE":    "Black&White",
        }

        self._backlight_modes = {
            "BACKLIGHTCONTROL":     "BackLightControl",
            "DYNAMICRANGECONTROL":  "DynamicRangeControl",
            "OFF":                  "Off",
        }
    #ndof __init__()

    @property
    def ptz_supported(self):
        return self._host.api.ptz_supported(self._channel)


    @property
    def playback_support(self):
        """ Return whethere the camera has VoDs. """
        return self._host.api.hdd_info is not None


    @property
    def motion_detection_enabled(self):
        return self._host.motion_detection_enabled and self._channel in self._host.motion_detection_enabled and self._host.motion_detection_enabled[self._channel]


    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        if attrs is None:
            attrs = {}

        if self._host.api.ptz_supported(self._channel):
            attrs["ptz_presets"] = self._host.api.ptz_presets(self._channel)

        for key, value in self._backlight_modes.items():
            if value == self._host.api.backlight_state(self._channel):
                attrs["backlight_state"] = key

        for key, value in self._daynight_modes.items():
            if value == self._host.api.daynight_state(self._channel):
                attrs["daynight_state"] = key

        if self._host.api.sensitivity_presets:
            attrs["sensitivity"] = self.get_sensitivity_presets()

        if self.playback_support:
            data: dict = self.hass.data.get(DOMAIN_DATA)
            data = data.get(self._host.unique_id) if data else None
            last: VoDRecord = data.get(LAST_RECORD) if data else None
            if last and last.url:
                attrs["video_url"] = last.url
                if last.thumbnail and last.thumbnail.exists:
                    attrs["video_thumbnail"] = last.thumbnail.url

        return attrs
    #endof extra_state_attributes()


    @property
    def supported_features(self):
        features = SUPPORT_STREAM
        if self.ptz_supported:
            features += SUPPORT_PTZ
        if self.playback_support:
            features += SUPPORT_PLAYBACK
        return features
    #endof supported_features()


    async def stream_source(self):
        return await self._host.api.get_stream_source(self._channel, self._stream)
    #endof stream_source()


    async def async_camera_image(self, width: Union[int, None] = None, height: Union[int, None] = None) -> Union[bytes, None]:
        """Return a still image response from the camera."""
        return await self._host.api.get_snapshot(self._channel)
    #endof async_camera_image()


    async def ptz_control(self, command, **kwargs):
        """Pass PTZ command to the camera."""
        if not self.ptz_supported:
            _LOGGER.error("PTZ is not supported on %s camera.", self.name)
            return

        await self._host.api.set_ptz_command(self._channel, command = self._ptz_commands[command], **kwargs)
    #endof ptz_control()


    #TODO: USELESS so far, because Reolink has not means to get a shot from a specific time of a recording.
    #      Thus all these thumbnails will be THE SAME current-time shots, which are nothing to do with a specific recording.
    async def commit_thumbnails(self, **kwargs):
        """ Query camera for VoDs and emit results """
        if not self.playback_support:
            _LOGGER.error("Video Playback is not supported on %s camera.", self.name)
            return

        await self._host.store_vod_thumbnails(self._channel, **kwargs)
    #endof commit_thumbnails()


    async def cleanup_thumbnails(self, **kwargs):
        """ Clear camera VoDs older than the date """
        if not self.playback_support:
            _LOGGER.error("Video Playback is not supported on %s camera.", self.name)
            return

        await self._host.cleanup_vod_thumbnails(self._channel)
    #endof cleanup_thumbnails()


    def get_sensitivity_presets(self):
        """Get formatted sensitivity presets."""
        presets = list()
        preset  = dict()

        for api_preset in self._host.api.sensitivity_presets(self._channel):
            preset["id"] = api_preset["id"]
            preset["sensitivity"] = api_preset["sensitivity"]

            time_string = f'{api_preset["beginHour"]}:{api_preset["beginMin"]}'
            begin = datetime.strptime(time_string, "%H:%M")
            preset["begin"] = begin.strftime("%H:%M")

            time_string = f'{api_preset["endHour"]}:{api_preset["endMin"]}'
            end = datetime.strptime(time_string, "%H:%M")
            preset["end"] = end.strftime("%H:%M")

            presets.append(preset.copy())

        return presets
    #endof get_sensitivity_presets()


    async def set_sensitivity(self, sensitivity, **kwargs):
        """Set the sensitivity to the camera."""
        if "preset" in kwargs:
            kwargs["preset"] += 1  # The camera preset ID's on the GUI are always +1
        await self._host.api.set_sensitivity(self._channel, value = sensitivity, **kwargs)


    async def set_daynight(self, mode):
        """Set the day and night mode to the camera."""
        await self._host.api.set_daynight(self._channel, value = self._daynight_modes[mode])


    async def set_backlight(self, mode):
        """Set the backlight mode to the camera."""
        await self._host.api.set_backlight(self._channel, value = self._backlight_modes[mode])


    async def async_enable_motion_detection(self):
        """Predefined camera service implementation."""
        if self._host.motion_detection_enabled:
            self._host.motion_detection_enabled[self._channel] = True

    async def async_disable_motion_detection(self):
        """Predefined camera service implementation."""
        if self._host.motion_detection_enabled:
            self._host.motion_detection_enabled[self._channel] = False
#endof class ReolinkCamera
