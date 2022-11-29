"""This component provides support for Reolink motion events."""
import datetime
import logging

from homeassistant.core                     import HomeAssistant, Event
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.event            import async_track_point_in_utc_time
from homeassistant.util                     import dt

from reolink_ip.api import (
    MOTION_DETECTION_TYPE,
    FACE_DETECTION_TYPE,
    PERSON_DETECTION_TYPE,
    VEHICLE_DETECTION_TYPE,
    PET_DETECTION_TYPE,
    VISITOR_DETECTION_TYPE
)

from .host   import ReolinkHost
from .entity import ReolinkCoordinatorEntity
from .const  import (
    HOST,
    DOMAIN,
    MOTION_WATCHDOG_TYPE,
    MOTION_COMMON_TYPE,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_CLASS = MOTION_DETECTION_TYPE


##########################################################################################################################################################
# Entry SETUP
##########################################################################################################################################################
async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_devices):
    """Set up the Reolink IP camera motion/AI sensors."""

    host: ReolinkHost = hass.data[DOMAIN][config_entry.entry_id][HOST]

    new_sensors = []
    for c in host.api.channels:
        host.sensor_motion_detection[c] = MotionSensor(hass, config_entry, c)
        new_sensors.append(host.sensor_motion_detection[c])

        if host.api.is_ia_enabled(c):
            _LOGGER.debug("Camera %s (channel %s, device model %s) is AI-enabled so object detection sensors will be created.", host.api.camera_name(c), c, host.api.camera_model(c))

            if host.api.ai_supported(c, FACE_DETECTION_TYPE):
                host.sensor_face_detection[c]       = ObjectDetectedSensor(hass, config_entry, FACE_DETECTION_TYPE, c)
                new_sensors.append(host.sensor_face_detection[c])
            if host.api.ai_supported(c, PERSON_DETECTION_TYPE):
                host.sensor_person_detection[c]     = ObjectDetectedSensor(hass, config_entry, PERSON_DETECTION_TYPE, c)
                new_sensors.append(host.sensor_person_detection[c])
            if host.api.ai_supported(c, VEHICLE_DETECTION_TYPE):
                host.sensor_vehicle_detection[c]    = ObjectDetectedSensor(hass, config_entry, VEHICLE_DETECTION_TYPE, c)
                new_sensors.append(host.sensor_vehicle_detection[c])
            if host.api.ai_supported(c, PET_DETECTION_TYPE):
                host.sensor_pet_detection[c]        = ObjectDetectedSensor(hass, config_entry, PET_DETECTION_TYPE, c)
                new_sensors.append(host.sensor_pet_detection[c])

        if host.api.is_doorbell_enabled(c):
            _LOGGER.debug("Camera %s (channel %s, device model %s) supports doorbell so visitor sensors will be created.", host.api.camera_name(c), c, host.api.camera_model(c))

            host.sensor_visitor_detection[c] = VisitorSensor(hass, config_entry, c)
            new_sensors.append(host.sensor_visitor_detection[c])

    async_add_devices(new_sensors, update_before_add = True)
#endof async_setup_entry()


##########################################################################################################################################################
# BASE motion sensor class
##########################################################################################################################################################
class ReolinkBinarySensorEntity(BinarySensorEntity):
    """An implementation of a base binary-sensor class for Reolink IP camera motion sensors."""

    # Needed only as a workaround for lack of proper ONVIF SWN notifications on some Reolink cameras (like E1 for example).
    # Motion sensors need to reliably go back to "Clear" somehow, after detection happened...

    def __init__(self):
        BinarySensorEntity.__init__(self)
        self._cancel_scheduled_clear = None
    #endof __init__()


    async def register_clear_callback(self):
        if self._state:
            if self._host.motion_force_off > 0:
                async def scheduled_clear(now):
                    """Timer callback for sensor resetting."""
                    _LOGGER.debug("CALLED SCEDULED CLEAR: %s", self._name)
                    self._cancel_scheduled_clear = None
                    await self.handle_event(Event(self._host.event_id, {MOTION_WATCHDOG_TYPE: False}))

                if self._cancel_scheduled_clear is not None:
                    _LOGGER.debug("CANCELLED PREVIOUS SCEDULED CLEAR: %s", self._name)
                    self._cancel_scheduled_clear()

                self._cancel_scheduled_clear = async_track_point_in_utc_time(
                    self.hass,
                    scheduled_clear,
                    dt.utcnow() + datetime.timedelta(seconds = self._host.motion_force_off),
                )
                _LOGGER.debug("REGISTERED SCEDULED CLEAR: %s", self._name)
        elif self._cancel_scheduled_clear is not None:
            self._cancel_scheduled_clear()
            self._cancel_scheduled_clear = None
            _LOGGER.debug("CANCELLED SCEDULED CLEAR: %s", self._name)
    #endof register_clear_callback()
#endof class ReolinkBinarySensorEntity


##########################################################################################################################################################
# Motion sensor class
##########################################################################################################################################################
class MotionSensor(ReolinkCoordinatorEntity, ReolinkBinarySensorEntity):
    """Implementation of a Reolink IP camera motion sensor."""

    def __init__(self, hass, config, channel: int):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ReolinkBinarySensorEntity.__init__(self)

        self._channel: int      = channel
        self._last_motion_time  = datetime.datetime.min
        self._unique_id         = f"reolink_motion_{self._host.unique_id}_{self._channel}"
        self._name              = f"{self._host.api.camera_name(channel)} motion"
    #endof __init__()


    ##############################################################################
    # Parent overrides
    @property
    def unique_id(self):
        return self._unique_id


    @property
    def name(self):
        return self._name


    @property
    def is_on(self):
        if self._state or self._host.motion_off_delay == 0:
            return self._state

        if (datetime.datetime.now() - self._last_motion_time).total_seconds() < self._host.motion_off_delay:
            return True
        else:
            return False
    #endof is_on


    @property
    def available(self) -> bool:
        if not self._host.motion_detection_enabled or self._channel not in self._host.motion_detection_enabled or not self._host.motion_detection_enabled[self._channel]:
            return False
        else:
            return self._host.api.session_active and (self._host.api.subscribed or self.is_on)
    #endof available


    @property
    def device_class(self):
        return DEFAULT_DEVICE_CLASS


    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        if attrs is None:
            attrs = {}

        attrs["bus_event_id"] = self._host.event_id

        if self._host.api.is_ia_enabled(self._channel):
            for key, value in self._host.api.ai_detected(self._channel).items():
                attrs[key] = value

        return attrs
    #endof extra_state_attributes


    async def async_added_to_hass(self) -> None:
        """Entity created."""
        await super().async_added_to_hass()
        self.hass.bus.async_listen(self._host.event_id, self.handle_event)
    #endof async_added_to_hass()


    # async def request_refresh(self):
    #     """Call the coordinator to update the API."""
    #     await self.coordinator.async_request_refresh()
    #     #await self.async_write_ha_state()


    ##############################################################################
    # Class methods
    async def handle_event(self, event):
        """Handle incoming event for motion detection."""
        if not self.enabled:
            return

        motion_event_state          = None
        motion_common_event_state   = None
        motion_watchdog_event_state = None
        if MOTION_DETECTION_TYPE in event.data:
            motion_event_state = event.data[MOTION_DETECTION_TYPE]
        elif MOTION_COMMON_TYPE in event.data:
            motion_common_event_state = event.data[MOTION_COMMON_TYPE]
        elif MOTION_WATCHDOG_TYPE in event.data:
            motion_watchdog_event_state = event.data[MOTION_WATCHDOG_TYPE]
        else:
            return

        if motion_common_event_state is not None:
            _LOGGER.info("COMMON-MOTION received %s: %s", motion_common_event_state, self._host.api.camera_name(self._channel))

            if motion_common_event_state:
                await self._host.api.get_all_motion_states(self._channel)
                if self._host.api.is_nvr:
                    self._state = self._host.api.motion_detected(self._channel)
                else:
                    self._state = True
            else:
                self._state = False

            if self._state:
                _LOGGER.info("MOTION TRIGGERED: %s", self._host.api.camera_name(self._channel))
                self._last_motion_time = datetime.datetime.now()

            self.async_schedule_update_ha_state()
            #await self.async_write_ha_state()

            if self._host.api.is_ia_enabled(self._channel):
                if self._channel in self._host.sensor_face_detection and self._host.sensor_face_detection[self._channel]:
                    await self._host.sensor_face_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_common_event_state}))
                if self._channel in self._host.sensor_person_detection and self._host.sensor_person_detection[self._channel]:
                    await self._host.sensor_person_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_common_event_state}))
                if self._channel in self._host.sensor_vehicle_detection and self._host.sensor_vehicle_detection[self._channel]:
                    await self._host.sensor_vehicle_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_common_event_state}))
                if self._channel in self._host.sensor_pet_detection and self._host.sensor_pet_detection[self._channel]:
                    await self._host.sensor_pet_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_common_event_state}))
        elif motion_event_state is not None:
            _LOGGER.info("MOTION received %s: %s", motion_event_state, self._host.api.camera_name(self._channel))

            if self._host.api.is_nvr:
                if motion_event_state:
                    await self._host.api.get_motion_state(self._channel)
                    self._state = self._host.api.motion_detected(self._channel)
                else:
                    self._state = False
            else:
                self._state = motion_event_state

            if self._state:
                _LOGGER.info("MOTION TRIGGERED: %s", self._host.api.camera_name(self._channel))
                self._last_motion_time = datetime.datetime.now()

            self.async_schedule_update_ha_state()
            #await self.async_write_ha_state()
        elif motion_watchdog_event_state is not None:
            _LOGGER.info("WATCHDOG-MOTION received %s: %s", motion_watchdog_event_state, self._host.api.camera_name(self._channel))

            await self._host.api.get_all_motion_states(self._channel)
            self._state = self._host.api.motion_detected(self._channel)

            if self._state:
                _LOGGER.info("MOTION TRIGGERED: %s", self._host.api.camera_name(self._channel))
                self._last_motion_time = datetime.datetime.now()

            self.async_schedule_update_ha_state()
            #await self.async_write_ha_state()

            if motion_watchdog_event_state and self._host.api.is_ia_enabled(self._channel):
                if self._channel in self._host.sensor_face_detection and self._host.sensor_face_detection[self._channel]:
                    await self._host.sensor_face_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_watchdog_event_state}))
                if self._channel in self._host.sensor_person_detection and self._host.sensor_person_detection[self._channel]:
                    await self._host.sensor_person_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_watchdog_event_state}))
                if self._channel in self._host.sensor_vehicle_detection and self._host.sensor_vehicle_detection[self._channel]:
                    await self._host.sensor_vehicle_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_watchdog_event_state}))
                if self._channel in self._host.sensor_pet_detection and self._host.sensor_pet_detection[self._channel]:
                    await self._host.sensor_pet_detection[self._channel].handle_event(Event(self._host.event_id, {"ai_refresh": motion_watchdog_event_state}))

        await self.register_clear_callback()
    #endof handle_event()
#endof class MotionSensor


##########################################################################################################################################################
# AI sensor class
##########################################################################################################################################################
class ObjectDetectedSensor(ReolinkCoordinatorEntity, ReolinkBinarySensorEntity):
    """An implementation of a Reolink IP camera object motion sensor."""

    def __init__(self, hass, config, object_type: str, channel: int):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ReolinkBinarySensorEntity.__init__(self)

        self._channel: int              = channel
        self._object_type               = object_type
        self._last_motion_time          = datetime.datetime.min
        self._unique_id                 = f"reolink_object_{object_type}_detected_{self._host.unique_id}_{channel}"
        self._name                      = f"{self._host.api.camera_name(channel)} {object_type} detected"
    #endof __init__()

    ##############################################################################
    # Parent overrides
    @property
    def icon(self):
        """Icon of the sensor."""

        if self._object_type == PET_DETECTION_TYPE:
            if self.is_on:
                return "mdi:dog-side"
            else:
                return "mdi:dog-side-off"
        elif self._object_type == VEHICLE_DETECTION_TYPE:
            if self.is_on:
                return "mdi:car"
            else:
                return "mdi:car-off"
        elif self._object_type == FACE_DETECTION_TYPE:
            if self.is_on:
                return "mdi:face-recognition"
            else:
                return "mdi:motion-sensor-off"
        elif self.is_on:
            return "mdi:motion-sensor"

        return "mdi:motion-sensor-off"

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of this sensor."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if self._state or self._host.motion_off_delay == 0:
            return self._state

        if (datetime.datetime.now() - self._last_motion_time).total_seconds() < self._host.motion_off_delay:
            return True
        else:
            return False

    @property
    def available(self) -> bool:
        if not self._host.motion_detection_enabled or self._channel not in self._host.motion_detection_enabled or not self._host.motion_detection_enabled[self._channel]:
            return False
        else:
            return self._host.api.session_active and (self._host.api.subscribed or self.is_on)

    @property
    def device_class(self):
        """Return the class of this device."""
        return DEFAULT_DEVICE_CLASS


    async def async_added_to_hass(self) -> None:
        """Entity created."""
        await super().async_added_to_hass()
        self.hass.bus.async_listen(self._host.event_id, self.handle_event)


    ##############################################################################
    # Methods
    async def handle_event(self, event):
        """Handle incoming event for AI motion detection."""
        if not self.enabled:
            return

        ai_refresh_event_state      = None
        event_state                 = None
        motion_watchdog_event_state = None
        if "ai_refresh" in event.data:
            ai_refresh_event_state = event.data["ai_refresh"]
        elif self._object_type in event.data:
            event_state = event.data[self._object_type]
        elif MOTION_WATCHDOG_TYPE in event.data:
            motion_watchdog_event_state = event.data[MOTION_WATCHDOG_TYPE]
            if motion_watchdog_event_state:
                return
        else:
            return

        if ai_refresh_event_state is not None:
            if ai_refresh_event_state:
                self._state = self._host.api.ai_detected(self._channel, self._object_type)
            else:
                self._state = False
        elif motion_watchdog_event_state is not None:
            _LOGGER.info("WATCHDOG-AI received %s: %s:%s", motion_watchdog_event_state, self._host.api.camera_name(self._channel), self._object_type)

            await self._host.api.get_ai_state(self._channel)
            self._state = self._host.api.ai_detected(self._channel, self._object_type)
        else:
            _LOGGER.info("MOTION-AI received %s: %s:%s", event_state, self._host.api.camera_name(self._channel), self._object_type)
            if self._host.api.is_nvr:
                self._state = self._host.api.ai_detected(self._channel, self._object_type)
            else:
                self._state = event_state

        if self._state:
            _LOGGER.info("MOTION-AI TRIGGERED: %s:%s", self._host.api.camera_name(self._channel), self._object_type)
            self._last_motion_time = datetime.datetime.now()

        self.async_schedule_update_ha_state()
        #await self.async_write_ha_state()

        await self.register_clear_callback()
    #endof handle_event()
#endof class ObjectDetectedSensor


##########################################################################################################################################################
# Visitor sensor class
##########################################################################################################################################################
class VisitorSensor(ReolinkCoordinatorEntity, ReolinkBinarySensorEntity):
    """Implementation of a Reolink IP camera doorbell button sensor."""

    def __init__(self, hass, config, channel: int):
        ReolinkCoordinatorEntity.__init__(self, hass, config)
        ReolinkBinarySensorEntity.__init__(self)

        self._channel: int          = channel
        self._last_detection_time   = datetime.datetime.min
        self._unique_id             = f"reolink_visitor_{self._host.unique_id}_{self._channel}"
        self._name                  = f"{self._host.api.camera_name(channel)} visitor"
    #endof __init__()


    ##############################################################################
    # Parent overrides
    @property
    def icon(self):
        return "mdi:doorbell"

    @property
    def unique_id(self):
        return self._unique_id


    @property
    def name(self):
        return self._name


    @property
    def is_on(self):
        if self._state or self._host.motion_off_delay == 0:
            return self._state

        if (datetime.datetime.now() - self._last_detection_time).total_seconds() < self._host.motion_off_delay:
            return True
        else:
            return False
    #endof is_on


    @property
    def available(self) -> bool:
        return self._host.api.session_active and (self._host.api.subscribed or self.is_on)
    #endof available


    @property
    def device_class(self):
        return VISITOR_DETECTION_TYPE


    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        if attrs is None:
            attrs = {}

        attrs["bus_event_id"] = self._host.event_id
        return attrs
    #endof extra_state_attributes


    async def async_added_to_hass(self) -> None:
        """Entity created."""
        await super().async_added_to_hass()
        self.hass.bus.async_listen(self._host.event_id, self.handle_event)
    #endof async_added_to_hass()


    # async def request_refresh(self):
    #     """Call the coordinator to update the API."""
    #     await self.coordinator.async_request_refresh()
    #     #await self.async_write_ha_state()


    ##############################################################################
    # Class methods
    async def handle_event(self, event):
        """Handle incoming event for visitor pressed a doorbell button."""
        if not self.enabled:
            return

        visitor_event_state = None
        if VISITOR_DETECTION_TYPE in event.data:
            visitor_event_state = event.data[VISITOR_DETECTION_TYPE]
        else:
            return

        if visitor_event_state is not None:
            _LOGGER.info("VISITOR received %s: %s", visitor_event_state, self._host.api.camera_name(self._channel))

            self._state = visitor_event_state

            if self._state:
                _LOGGER.info("VISITOR TRIGGERED: %s", self._host.api.camera_name(self._channel))
                self._last_detection_time = datetime.datetime.now()

            self.async_schedule_update_ha_state()
            #await self.async_write_ha_state()

        await self.register_clear_callback()
    #endof handle_event()
#endof class VisitorSensor
