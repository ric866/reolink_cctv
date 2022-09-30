""" custom helper actions """

#import  logging
import  os
import  voluptuous  as      vol
from    typing      import  Optional, cast

from homeassistant.core                     import Context, HomeAssistant
from homeassistant.components.camera        import ATTR_FILENAME, DOMAIN as CAMERA_DOMAIN, SERVICE_SNAPSHOT
from homeassistant.helpers                  import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const                    import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
    CONF_NAME
)

from .camera    import ReolinkCamera
from .utils     import async_get_device_entries
from .const     import DOMAIN, THUMBNAIL_EXTENSION

VOD_THUMB_CAP   = "capture_vod_thumbnail"
ACTION_SCHEMA   = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE):        cv.string,
        vol.Required(CONF_NAME):        cv.string,
        vol.Required(CONF_ENTITY_ID):   cv.entities_domain(CAMERA_DOMAIN),
    }
)

# _LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
#
##########################################################################################################################################################
async def async_get_actions(hass: HomeAssistant, device_id: str):
    """Provide a list of NVR/camera device actions."""

    actions = []

    device, device_entries = await async_get_device_entries(hass, device_id)
    if not device or not device_entries or len(device_entries) < 1:
        return actions

    cam_component: EntityComponent = hass.data[CAMERA_DOMAIN]

    for entry in device_entries:
        if entry.domain == CAMERA_DOMAIN:
            camera = cast(ReolinkCamera, cam_component.get_entity(entry.entity_id))
            actions.append(
                {
                    CONF_DOMAIN:    DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE:      f"{camera.name} snapshot",
                    CONF_NAME:      VOD_THUMB_CAP
                }
            )
    return actions
#endof async_get_actions()


##########################################################################################################################################################
#
##########################################################################################################################################################
async def async_call_action_from_config(hass: HomeAssistant, config: dict, variables: dict, context: Optional[Context]):
    """Execute an NVR/camera device action."""

    if config[CONF_NAME] == VOD_THUMB_CAP:
        camera_entity_id: str = config.get(CONF_ENTITY_ID)
        # if not camera_entity_id:
        #     _, device_entries = await async_get_device_entries(hass, config[CONF_DEVICE_ID])
        #     for entry in device_entries:
        #         if entry.domain == CAMERA_DOMAIN:
        #             camera_entity_id = entry.entity_id
        #         if camera_entity_id is not None:
        #             break

        if camera_entity_id is not None:
            cam_component: EntityComponent = hass.data[CAMERA_DOMAIN]
            camera = cast(ReolinkCamera, cam_component.get_entity(camera_entity_id))

            if camera is not None:
                file_path = os.path.join(camera._host.thumbnail_path, f"{camera._channel}/snapshot.{THUMBNAIL_EXTENSION}")
                service_data = {
                    ATTR_ENTITY_ID: camera_entity_id,
                    ATTR_FILENAME:  file_path,
                }

                if os.path.isfile(file_path):
                    os.remove(file_path)

                return await hass.services.async_call(
                    CAMERA_DOMAIN,
                    SERVICE_SNAPSHOT,
                    service_data,
                    blocking = True,
                    context = context,
                )
#endof async_call_action_from_config()
