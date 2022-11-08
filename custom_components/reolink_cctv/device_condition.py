""" Additional conditions for ReoLink Camera """

# import  logging
from    typing      import cast
import  voluptuous  as vol

from homeassistant.core                     import HomeAssistant, callback
from homeassistant.helpers                  import condition, config_validation as cv
from homeassistant.components.sensor        import DOMAIN                       as SENSOR_DOMAIN
from homeassistant.helpers.typing           import ConfigType, TemplateVarsType
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const                    import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_CONDITION,
    CONF_ENTITY_ID,
    CONF_FOR,
    CONF_TYPE,
    CONF_NAME,
    DEVICE_CLASS_TIMESTAMP,
)

from .sensor    import LastRecordSensor
from .utils     import async_get_device_entries
from .const     import DOMAIN

NO_THUMBNAIL  = "vod_no_thumbnail"
HAS_THUMBNAIL = "vod_has_thumbnail"

CONDITION_NAMES  = {NO_THUMBNAIL, HAS_THUMBNAIL}
CONDITION_SCHEMA = cv.DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE):        cv.string,
        vol.Required(CONF_NAME):        vol.In(CONDITION_NAMES),
        vol.Required(CONF_ENTITY_ID):   cv.entity_domain(SENSOR_DOMAIN)
        #vol.Optional(CONF_FOR):         cv.time,
    }
)

# _LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
#
##########################################################################################################################################################
async def async_get_conditions(hass: HomeAssistant, device_id: str):
    """List conditions for NVR/camera devices."""

    conditions = []

    device, device_entries = await async_get_device_entries(hass, device_id)
    if not device or not device_entries or len(device_entries) < 1:
        return conditions

    sensor_component: EntityComponent = hass.data[SENSOR_DOMAIN]

    for entry in device_entries:
        if entry.domain != SENSOR_DOMAIN or entry.original_device_class != DEVICE_CLASS_TIMESTAMP:
            continue

        sensor = cast(LastRecordSensor, sensor_component.get_entity(entry.entity_id))
        conditions.append(
            {
                CONF_CONDITION:  "device",
                CONF_DOMAIN:    DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE:      f"{sensor.name}: no thumbnail",
                CONF_NAME:      NO_THUMBNAIL
                #CONF_FOR:       None,
            }
        )
        conditions.append(
            {
                CONF_CONDITION:  "device",
                CONF_DOMAIN:    DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE:      f"{sensor.name}: has thumbnail",
                CONF_NAME:      HAS_THUMBNAIL
                #CONF_FOR:       None,
            },
        )

    return conditions
#endof async_get_conditions()


##########################################################################################################################################################
#
##########################################################################################################################################################
@callback
def async_condition_from_config(config: ConfigType, config_validation: bool) -> condition.ConditionCheckerType:
    """Create a function to test an NVR/camera device condition."""

    if config_validation:
        config = CONDITION_SCHEMA(config)

    config_name = config[CONF_NAME]
    if config_name in CONDITION_NAMES:
        if config_name == NO_THUMBNAIL:
            state = "false"
        else:
            state = "true"

        sensor_entity_id: str   = config[CONF_ENTITY_ID]
        for_period              = config.get(CONF_FOR)
        attribute               = "has_thumbnail"

        # @trace_condition_function
        def test_is_state(hass: HomeAssistant, variables: TemplateVarsType):
            """ Test thumbnail state """
            return condition.state(
                hass,
                sensor_entity_id,
                state,
                for_period,
                attribute,
            )

        return test_is_state
#endof async_condition_from_config()
