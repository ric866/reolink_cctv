"""This component provides support for Reolink IP VoD support."""
import datetime as dt
import logging
import os

from urllib.parse                       import quote_plus
from dataclasses                        import dataclass
from dateutil                           import relativedelta
from homeassistant.components.camera    import ATTR_FILENAME, DOMAIN as CAMERA_DOMAIN, SERVICE_SNAPSHOT

import  homeassistant.util.dt           as dt_utils
from    homeassistant.core              import CALLBACK_TYPE, HomeAssistant
from    homeassistant.config_entries    import ConfigEntry
from    homeassistant.components.sensor import DEVICE_CLASS_TIMESTAMP, SensorEntity
from    homeassistant.const             import ATTR_ENTITY_ID

from reolink_ip.api import MOTION_DETECTION_TYPE

from .entity    import ReolinkCoordinatorEntity
from .host      import ReolinkHost, searchtime_to_datetime
from .typings   import VoDRecord, VoDRecordThumbnail
from .const     import (
    HOST,
    DOMAIN,
    DOMAIN_DATA,
    LAST_RECORD,
    THUMBNAIL_EXTENSION,
    THUMBNAIL_URL,
    VOD_URL,
    MOTION_COMMON_TYPE,
)

_LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
# ENTRY SETUP
##########################################################################################################################################################
async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_devices):
    """Set up the Reolink IP Cameras' last-record sensors."""
    devices = []
    host: ReolinkHost = hass.data[DOMAIN][config_entry.entry_id][HOST]

    # TODO : add playback (based off of hdd_info) to api capabilities
    if host.api.hdd_info is not None:
        for c in host.api.channels:
            devices.append(LastRecordSensor(hass, config_entry, c))

    async_add_devices(devices, update_before_add = True)
#endof async_setup_entry()


##########################################################################################################################################################
# Last record sensor class
##########################################################################################################################################################
@dataclass
class _Attrs:
    oldest_day: dt.datetime         = None
    most_recent_day: dt.datetime    = None
    last_record: VoDRecord          = None
#endof class _Attrs


class LastRecordSensor(ReolinkCoordinatorEntity, SensorEntity):
    """An implementation of a Reolink IP camera last-record sensor."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry, channel: int):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        SensorEntity.__init__(self)

        self._channel                       = channel
        self._attrs                         = _Attrs()
        self._bus_listener: CALLBACK_TYPE   = None
        self._entry_id                      = config.entry_id
    #endof __init__()


    ##########################################################################
    # Properties
    @property
    def unique_id(self):
        return f"reolink_lastrecord_{self._host.unique_id}_{self._channel}"

    @property
    def name(self):
        return f"{self._host.api.camera_name(self._channel)} last record"

    @property
    def device_class(self):
        return DEVICE_CLASS_TIMESTAMP

    @property
    def state(self):
        if not self._state:
            return None

        date = (
            self._attrs.last_record.start
            if self._attrs.last_record and self._attrs.last_record.start
            else None
        )
        if not date:
            return None

        return date.isoformat()
    #endof state()

    @property
    def icon(self):
        return "mdi:history"

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes

        if self._state:
            if attrs is None:
                attrs = {}

            if self._attrs.oldest_day:
                attrs["oldest_day"] = self._attrs.oldest_day.isoformat()
            if self._attrs.last_record:
                if self._attrs.last_record.event_id:
                    attrs["vod_event_id"] = self._attrs.last_record.event_id
                    if self._attrs.last_record.thumbnail:
                        attrs["has_thumbnail"] = (
                            "true"
                            if self._attrs.last_record.thumbnail.exists
                            else "false"
                        )

                        attrs["thumbnail_path"] = self._attrs.last_record.thumbnail.path
                if self._attrs.last_record.cam_record_url:
                    attrs["last_record_url"] = self._attrs.last_record.cam_record_url
                if self._attrs.last_record.duration:
                    attrs["duration"] = str(self._attrs.last_record.duration)
        return attrs
    #endof extra_state_attributes()


    ##########################################################################
    # Methods
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._bus_listener = self.hass.bus.async_listen(self._host.event_id, self.handle_event)
        #self._hass.async_add_job(self._update_last_record)
    #endof async_added_to_hass()


    async def async_will_remove_from_hass(self):
        if self._bus_listener:
            self._bus_listener()
            self._bus_listener = None
        await super().async_will_remove_from_hass()
    #endof async_will_remove_from_hass()


    async def request_refresh(self):
        """ Force an update of the sensor """
        await super().request_refresh()
        self._hass.async_add_job(self._update_last_record)
    #endof request_refresh()


    async def async_update(self):
        """ Polling update """
        await super().async_update()
        self._hass.async_add_job(self._update_last_record)
    #endof async_update()


    async def _update_last_record(self):
        if not self.hass or not self.enabled:
            return

        end = dt_utils.now()
        start   = self._attrs.most_recent_day
        if not start:
            start = dt.datetime.combine(end.date(), dt.time.min)
            if self._host.playback_days > 0:
                start -= relativedelta.relativedelta(days = int(self._host.playback_days))

        search, _ = await self._host.api.request_vod_files(self._channel, start, end, True)
        if not search or len(search) < 1:
            return

        entry = search[0]
        self._attrs.oldest_day = dt.datetime(
            entry["year"],
            entry["mon"],
            next((i for (i, e) in enumerate(entry["table"], start = 1) if e == "1")),
            tzinfo = end.tzinfo,
        )
        entry = search[-1]
        start = self._attrs.most_recent_day = dt.datetime(
            entry["year"],
            entry["mon"],
            len(entry["table"])
            - next(
                (
                    i
                    for (i, e) in enumerate(reversed(entry["table"]), start = 0)
                    if e == "1"
                )
            ),
            tzinfo = end.tzinfo,
        )
        end = dt.datetime.combine(start.date(), dt.time.max, tzinfo = end.tzinfo)
        _, files = await self._host.api.request_vod_files(self._channel, start, end)
        file = files[-1] if files and len(files) > 0 else None
        if file is None:
            return

        filename = None
        if self._host.api.is_nvr:
            element = file.get("PlaybackTime", None)
            if element is not None:
                filename = "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(element["year"], element["mon"], element["day"], element["hour"], element["min"], element["sec"])
            else:
                filename = ""
                _LOGGER.debug("VOD search command returned a file record without a playback-time: %s", str(file))
        else:
            filename = file.get("name", "")
            if len(filename) == 0:
                _LOGGER.debug("VOD search command returned a file record without a name: %s", str(file))

        end     = searchtime_to_datetime(file["EndTime"], start.tzinfo)
        start   = searchtime_to_datetime(file["StartTime"], end.tzinfo)
        last    = self._attrs.last_record = VoDRecord(str(start.timestamp()), start, end - start, filename)

        last.url = VOD_URL.format(entry_id = self._entry_id, camera_id = self._channel, event_id = quote_plus(filename))
        _, last.cam_record_url = await self._host.api.get_vod_source(self._channel, filename, True)

        thumbnail = last.thumbnail = VoDRecordThumbnail(
            THUMBNAIL_URL.format(entry_id = self._entry_id, camera_id = self._channel, event_id = last.event_id),
            path = os.path.join(self._host.thumbnail_path, f"{self._channel}/{last.event_id}.{THUMBNAIL_EXTENSION}")
        )

        if not os.path.isfile(thumbnail.path):
            directory = os.path.join(self._host.thumbnail_path, f"{self._channel}")
            if not os.path.isdir(directory):
                os.makedirs(directory)
            if self._channel in self._host.cameras:
                service_data = {
                    ATTR_ENTITY_ID: self._host.cameras[self._channel].entity_id,
                    ATTR_FILENAME: thumbnail.path,
                }
                await self._hass.services.async_call(CAMERA_DOMAIN, SERVICE_SNAPSHOT, service_data, blocking = True)

        thumbnail.exists = os.path.isfile(thumbnail.path)

        data: dict          = self._hass.data.setdefault(DOMAIN_DATA, {})
        data                = data.setdefault(self._host.unique_id, {})
        data[LAST_RECORD]   = last

        self._state = True

        if not self.hass or not self.enabled:
            return
        self.async_schedule_update_ha_state()
    #endof _update_last_record()


    async def handle_event(self, event):
        """Handle incoming event for VoD update"""
        if (MOTION_DETECTION_TYPE not in event.data or not event.data[MOTION_DETECTION_TYPE]) and (MOTION_COMMON_TYPE not in event.data or not event.data[MOTION_COMMON_TYPE]):
            return
        await self._hass.async_add_job(self._update_last_record)
    #endof handle_event()
#endof class LastRecordSensor
