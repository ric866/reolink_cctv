"""Reolink CCTV integration for HomeAssistant."""

import asyncio
import logging
from datetime import timedelta

import async_timeout

from homeassistant.config_entries               import ConfigEntry
from homeassistant.core                         import HomeAssistant, Event
from homeassistant.exceptions                   import ConfigEntryNotReady
from homeassistant.helpers.storage              import STORAGE_DIR
from homeassistant.helpers.update_coordinator   import DataUpdateCoordinator
from homeassistant.const import (
    CONF_TIMEOUT,
    EVENT_HOMEASSISTANT_STOP,
)

from .host  import ReolinkHost
from .const import (
    HOST,
    CONF_EXTERNAL_HOST,
    CONF_EXTERNAL_PORT,
    CONF_MOTION_OFF_DELAY,
    CONF_MOTION_FORCE_OFF,
    CONF_PLAYBACK_MONTHS,
    CONF_PROTOCOL,
    CONF_STREAM,
    CONF_THUMBNAIL_PATH,
    CONF_STREAM_FORMAT,
    CONF_SUBSCRIPTION_WATCHDOG_INTERVAL,
    DEFAULT_EXTERNAL_HOST,
    DEFAULT_EXTERNAL_PORT,
    DEFAULT_PROTOCOL,
    DEFAULT_MOTION_FORCE_OFF,
    DEFAULT_MOTION_OFF_DELAY,
    DEFAULT_PLAYBACK_MONTHS,
    DEFAULT_STREAM,
    DEFAULT_STREAM_FORMAT,
    DEFAULT_SUBSCRIPTION_WATCHDOG_INTERVAL,
    DEFAULT_TIMEOUT,
    DEVICE_CONFIG_UPDATE_COORDINATOR,
    SUBSCRIPTION_WATCHDOG_COORDINATOR,
    DOMAIN,
    SERVICE_PTZ_CONTROL,
    SERVICE_SET_BACKLIGHT,
    SERVICE_CLEANUP_THUMBNAILS,
    SERVICE_SET_DAYNIGHT,
    SERVICE_SET_SENSITIVITY,
    MOTION_WATCHDOG_TYPE
)

DEVICE_UPDATE_INTERVAL  = timedelta(minutes = 1)
PLATFORMS               = ["camera", "switch", "binary_sensor", "sensor"]
_LOGGER                 = logging.getLogger(__name__)


##########################################################################################################################################################
# COMPONENT SETUP
##########################################################################################################################################################
async def async_setup(hass: HomeAssistant, config: dict):  # pylint: disable=unused-argument
    """Set up the Reolink component."""
    hass.data.setdefault(DOMAIN, {})

    # Ensure default storage path is writable by scripts.
    default_thumbnail_path = hass.config.path(f"{STORAGE_DIR}/{DOMAIN}")
    if default_thumbnail_path not in hass.config.allowlist_external_dirs:
        hass.config.allowlist_external_dirs.add(default_thumbnail_path)

    return True
#endof async_setup()


##########################################################################################################################################################
# MAIN ENTRY SETUP (HOST)
##########################################################################################################################################################
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Reolink from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    host = ReolinkHost(hass, entry.data, entry.options)

    try:
        if not await host.init():
            raise ConfigEntryNotReady(f"Error while trying to setup {host.api._host}:{host.api._port}: failed to obtain required data from device.")
    except Exception as e:
        err = str(e)
        raise ConfigEntryNotReady(f"Error while trying to setup {host.api._host}:{host.api._port}: failed to connect to device: \"{err}\".")

    host.sync_functions.append(entry.add_update_listener(entry_update_listener))

    hass.data[DOMAIN][entry.entry_id] = {HOST: host}
    await host.subscribe()

    async def async_device_config_update():
        """Perform the update of the host config-state cache, and renew the ONVIF-subscription."""
        async with async_timeout.timeout(host.api.timeout):
            await host.renew()
        async with async_timeout.timeout(host.api.timeout):
            await host.update_states() # Login session is implicitly updated here, so no need to explicitly do it in a timer

    coordinator_device_config_update = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name = "reolink.{}".format(host.api.nvr_name),
        update_method = async_device_config_update,
        update_interval = DEVICE_UPDATE_INTERVAL
    )
    # Fetch initial data so we have data when entities subscribe
    await coordinator_device_config_update.async_refresh()
    #await coordinator_device_config_update.async_config_entry_first_refresh()

    async def async_subscription_watchdog():
        # Perform subscription state check.
        if not host.api.subscribed:
            _LOGGER.info("WATCHDOG: No active subscription for host %s:%s. Force-refreshing motion states...", host.api.host, host.api.port)
            for c in host.api.channels:
                if c in host.sensor_motion_detection and host.sensor_motion_detection[c] is not None:
                    async with async_timeout.timeout(host.api.timeout):
                        host.sensor_motion_detection[c].handle_event(Event(host.event_id, {MOTION_WATCHDOG_TYPE: True}))
            #hass.bus.async_fire(host.event_id, {MOTION_WATCHDOG_TYPE: True})

    coordinator_subscription_watchdog = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name = "reolink.{}.watchdog".format(host.api.nvr_name),
        update_method = async_subscription_watchdog,
        update_interval = timedelta(seconds = host.subscription_watchdog_interval),
    )
    def dummy_callback():
        pass
    host.sync_functions.append(coordinator_subscription_watchdog.async_add_listener(dummy_callback))
    #coordinator_subscription_watchdog = async_track_time_interval(hass, async_subscription_watchdog, timedelta(seconds = host.subscription_watchdog_interval))

    hass.data[DOMAIN][entry.entry_id][DEVICE_CONFIG_UPDATE_COORDINATOR]     = coordinator_device_config_update
    hass.data[DOMAIN][entry.entry_id][SUBSCRIPTION_WATCHDOG_COORDINATOR]    = coordinator_subscription_watchdog

    for component in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, component))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, host.stop)

    await entry_update_listener(hass, entry)

    return True
#endof async_setup_entry()


##########################################################################################################################################################
# Config update callback
##########################################################################################################################################################
async def entry_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Update the configuration of the host entity."""
    host: ReolinkHost = hass.data[DOMAIN][entry.entry_id][HOST]

    host.motion_off_delay   = entry.options.get(CONF_MOTION_OFF_DELAY, DEFAULT_MOTION_OFF_DELAY)
    host.motion_force_off   = entry.options.get(CONF_MOTION_FORCE_OFF, DEFAULT_MOTION_FORCE_OFF)
    host.playback_months    = entry.options.get(CONF_PLAYBACK_MONTHS, DEFAULT_PLAYBACK_MONTHS)
    host.thumbnail_path     = hass.config.path(f"{STORAGE_DIR}/{DOMAIN}/{entry.unique_id}") if (CONF_THUMBNAIL_PATH not in entry.options or not entry.options[CONF_THUMBNAIL_PATH]) else entry.options[CONF_THUMBNAIL_PATH]
    host.api.external_host  = entry.options.get(CONF_EXTERNAL_HOST, DEFAULT_EXTERNAL_HOST)
    host.api.external_port  = entry.options.get(CONF_EXTERNAL_PORT, DEFAULT_EXTERNAL_PORT)
    host.api.timeout        = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    host.api.protocol       = entry.options.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
    host.api.stream         = entry.options.get(CONF_STREAM, DEFAULT_STREAM)
    host.api.stream_format  = entry.options.get(CONF_STREAM_FORMAT, DEFAULT_STREAM_FORMAT)

    coordinator_subscription_watchdog: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][SUBSCRIPTION_WATCHDOG_COORDINATOR]

    host.subscription_watchdog_interval = entry.options.get(CONF_SUBSCRIPTION_WATCHDOG_INTERVAL, DEFAULT_SUBSCRIPTION_WATCHDOG_INTERVAL)

    if coordinator_subscription_watchdog.update_interval != host.subscription_watchdog_interval:
        if host.subscription_watchdog_interval is None or host.subscription_watchdog_interval <= 0:
            coordinator_subscription_watchdog.update_interval = None
            _LOGGER.debug("ONVIF-subscription watchdog disabled.")
        else:
            coordinator_subscription_watchdog.update_interval = timedelta(seconds = host.subscription_watchdog_interval)
            _LOGGER.debug("ONVIF-subscription watchdog interval changed to %s seconds.", coordinator_subscription_watchdog.update_interval)
        await coordinator_subscription_watchdog.async_refresh()
#endof entry_update_listener()


##########################################################################################################################################################
# Unload entry callback
##########################################################################################################################################################
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    host: ReolinkHost = hass.data[DOMAIN][entry.entry_id][HOST]

    await host.stop()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    if len(hass.data[DOMAIN]) == 0:
        hass.services.async_remove(DOMAIN, SERVICE_SET_SENSITIVITY)
        hass.services.async_remove(DOMAIN, SERVICE_SET_DAYNIGHT)
        hass.services.async_remove(DOMAIN, SERVICE_SET_BACKLIGHT)
        hass.services.async_remove(DOMAIN, SERVICE_PTZ_CONTROL)
        hass.services.async_remove(DOMAIN, SERVICE_CLEANUP_THUMBNAILS)

    return unload_ok
#endof async_unload_entry()
