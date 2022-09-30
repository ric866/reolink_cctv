""" Additional triggers for ReoLink Camera """

#import  logging
import  voluptuous  as vol
from    typing      import  cast

from homeassistant.core                                 import HomeAssistant
from homeassistant.components.automation                import AutomationActionType             #deprecated in 2022.9
#from homeassistant.helpers.trigger                      import TriggerActionType, TriggerInfo  #since 2022.9
from homeassistant.components.device_automation         import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers    import state                as state_trigger
from homeassistant.components.sensor                    import DOMAIN               as SENSOR_DOMAIN
from homeassistant.helpers                              import config_validation    as cv
from homeassistant.helpers.typing                       import ConfigType
from homeassistant.helpers.entity_component             import EntityComponent
from homeassistant.const                                import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
    CONF_NAME,
    DEVICE_CLASS_TIMESTAMP,
)

from .sensor    import LastRecordSensor
from .utils     import async_get_device_entries
from .const     import DOMAIN

NEW_VOD         = "new_vod"
TRIGGER_TYPES   = {NEW_VOD}
TRIGGER_SCHEMA  = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE):        cv.string,
        vol.Required(CONF_NAME):        vol.In(TRIGGER_TYPES),
        vol.Required(CONF_ENTITY_ID):   cv.entity_domain(SENSOR_DOMAIN),
    }
)

# _LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
#
##########################################################################################################################################################
async def async_get_triggers(hass: HomeAssistant, device_id: str):
    """ List of device triggers """

    triggers = []

    device, device_entries = await async_get_device_entries(hass, device_id)
    if not device or not device_entries or len(device_entries) < 1:
        return triggers

    sensor_component: EntityComponent = hass.data[SENSOR_DOMAIN]

    for entry in device_entries:
        if entry.domain != SENSOR_DOMAIN or entry.original_device_class != DEVICE_CLASS_TIMESTAMP:
            continue

        sensor = cast(LastRecordSensor, sensor_component.get_entity(entry.entity_id))
        triggers.append(
            {
                CONF_PLATFORM:  "device",
                CONF_DOMAIN:    DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE:      f"{sensor.name}: new video file",
                CONF_NAME:      NEW_VOD
            }
        )

    return triggers
#endof async_get_triggers()


##########################################################################################################################################################
#
##########################################################################################################################################################
async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,   #TriggerActionType          #since 2022.9
    automation_info: dict,          #trigger_info: TriggerInfo  #since 2022.9
):
    """ Attach a trigger """

    if config[CONF_NAME] == NEW_VOD and CONF_ENTITY_ID in config and config[CONF_ENTITY_ID] is not None:
        state_config = ConfigType(
            {
                CONF_PLATFORM:  "state",
                CONF_ENTITY_ID: config[CONF_ENTITY_ID],
            }
        )

        return await state_trigger.async_attach_trigger(
            hass,
            state_config,
            action,
            automation_info,
            platform_type = config[CONF_PLATFORM],
        )
#endof async_attach_trigger()
