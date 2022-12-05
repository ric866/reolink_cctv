"""Config flow for the Reolink camera component."""
import logging
import voluptuous as vol

from homeassistant                  import config_entries, core, exceptions
from homeassistant.core             import callback
from homeassistant.helpers          import config_validation as cv
from homeassistant.helpers.storage  import STORAGE_DIR
from homeassistant.const            import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_USERNAME,
)

from reolink_ip.exceptions import CredentialsInvalidError, ApiError

from .host import ReolinkHost
from .const import (
    CONF_EXTERNAL_HOST,
    CONF_EXTERNAL_PORT,
    CONF_USE_HTTPS,
    CONF_MOTION_OFF_DELAY,
    CONF_MOTION_FORCE_OFF,
    CONF_PLAYBACK_DAYS,
    CONF_PROTOCOL,
    CONF_STREAM,
    CONF_STREAM_FORMAT,
    CONF_THUMBNAIL_PATH,
    CONF_SUBSCRIPTION_WATCHDOG_INTERVAL,
    DEFAULT_EXTERNAL_HOST,
    DEFAULT_EXTERNAL_PORT,
    DEFAULT_MOTION_OFF_DELAY,
    DEFAULT_MOTION_FORCE_OFF,
    DEFAULT_PLAYBACK_DAYS,
    DEFAULT_PROTOCOL,
    DEFAULT_STREAM,
    DEFAULT_STREAM_FORMAT,
    DEFAULT_TIMEOUT,
    DEFAULT_SUBSCRIPTION_WATCHDOG_INTERVAL,
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)


##########################################################################################################################################################
# Flow handler
##########################################################################################################################################################
class ReolinkFlowHandler(config_entries.ConfigFlow, domain = DOMAIN):
    """Handle a config flow for Reolink device."""

    VERSION = 1

    unique_id           = None
    host_name           = None
    port                = None
    use_https           = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ReolinkOptionsFlowHandler(config_entry)


    async def async_step_user(self, user_input = None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.data = user_input

            try:
                await self.async_obtain_host_settings(self.hass, user_input)

                await self.async_set_unique_id(self.unique_id)
                self._abort_if_unique_id_configured()

                user_input[CONF_PORT] = self.port
                user_input[CONF_USE_HTTPS] = self.use_https
                return self.async_create_entry(title = self.host_name, data = user_input)

            except CannotConnect:
                errors[CONF_HOST] = "cannot_connect"
            except InvalidHost:
                errors[CONF_HOST] = "cannot_connect"
            except CredentialsInvalidError:
                errors[CONF_HOST] = "invalid_auth"
            except ApiError:
                errors[CONF_HOST] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors[CONF_HOST] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME, default = "admin"): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_HOST): str,
        })
        if errors:
            data_schema = data_schema.extend({
                vol.Optional(CONF_PORT): cv.positive_int,
                vol.Optional(CONF_USE_HTTPS): bool,
            })

        return self.async_show_form(
            step_id = "user",
            data_schema = data_schema,
            errors = errors,
        )
    #endof async_step_user()


    async def async_obtain_host_settings(self, hass: core.HomeAssistant, user_input: dict):
        host = ReolinkHost(hass, user_input)

        try:
            if not await host.init():
                _LOGGER.error(f"Error while performing initial setup of {host.api._host}:{host.api._port}: failed to obtain data from device.")
                raise CannotConnect
        except Exception as e:
            err = str(e)
            if err:
                _LOGGER.error(f"Error while performing initial setup of {host.api._host}:{host.api._port}: \"{err}\".")
            else:
                _LOGGER.error(f"Error while performing initial setup of {host.api._host}:{host.api._port}: failed to connect to device.")
            raise CannotConnect
        finally:
            try:
                await host.stop()
            except:
                pass

        self.host_name      = host.api.nvr_name
        self.unique_id      = host.unique_id
        self.port           = host.api.port
        self.use_https      = host.api.use_https
    #endof async_validate_input()


##########################################################################################################################################################
# Option handler
##########################################################################################################################################################
class ReolinkOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Reolink options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry


    async def async_step_init(self, user_input = None):
        """Manage the Reolink options."""

        if user_input is not None:
            return self.async_create_entry(title = "", data = user_input)

        default_thumbnail_path: str = self.hass.config.path(f"{STORAGE_DIR}/{DOMAIN}/{self.config_entry.unique_id}")

        return self.async_show_form(
            step_id = "init",
            data_schema = vol.Schema(
                {                 
                    vol.Optional(
                        CONF_EXTERNAL_HOST,
                        default = self.config_entry.options.get(CONF_EXTERNAL_HOST, DEFAULT_EXTERNAL_HOST),
                    ): cv.string,

                    vol.Optional(
                        CONF_EXTERNAL_PORT,
                        default = self.config_entry.options.get(CONF_EXTERNAL_PORT, DEFAULT_EXTERNAL_PORT),
                    ): cv.string,

                    vol.Required(
                        CONF_PROTOCOL,
                        default = self.config_entry.options.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
                    ): vol.In(["rtmp", "rtsp", "images"]),

                    vol.Required(
                        CONF_STREAM,
                        default = self.config_entry.options.get(CONF_STREAM, DEFAULT_STREAM),
                    ): vol.In(["main", "sub", "ext"]),

                    vol.Required(
                        CONF_STREAM_FORMAT,
                        default = self.config_entry.options.get(CONF_STREAM_FORMAT, DEFAULT_STREAM_FORMAT),
                    ): vol.In(["h264", "h265"]),

                    vol.Required(
                        CONF_MOTION_OFF_DELAY,
                        default = self.config_entry.options.get(CONF_MOTION_OFF_DELAY, DEFAULT_MOTION_OFF_DELAY),
                    ): vol.All(vol.Coerce(int), vol.Range(min = 0)),

                    vol.Required(
                        CONF_MOTION_FORCE_OFF,
                        default = self.config_entry.options.get(CONF_MOTION_FORCE_OFF, DEFAULT_MOTION_FORCE_OFF),
                    ): vol.All(vol.Coerce(int), vol.Range(min = 0)),

                    vol.Required(
                        CONF_SUBSCRIPTION_WATCHDOG_INTERVAL,
                        default = self.config_entry.options.get(CONF_SUBSCRIPTION_WATCHDOG_INTERVAL, DEFAULT_SUBSCRIPTION_WATCHDOG_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min = 0, max = 180)),

                    vol.Required(
                        CONF_PLAYBACK_DAYS,
                        default = self.config_entry.options.get(CONF_PLAYBACK_DAYS, DEFAULT_PLAYBACK_DAYS),
                    ): cv.positive_int,

                    vol.Optional(
                        CONF_THUMBNAIL_PATH,
                        default = self.config_entry.options.get(CONF_THUMBNAIL_PATH, default_thumbnail_path),
                    ): cv.string,

                    vol.Optional(
                        CONF_TIMEOUT,
                        default = self.config_entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    ): vol.All(vol.Coerce(int), vol.Range(min = 1, max = 120)),
                }
            )
        ) #return self.async_show_form
    #endof async_step_init()
#endof class ReolinkOptionsFlowHandler


##########################################################################################################################################################
# Exceptions
##########################################################################################################################################################
class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate device is already configured."""


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""


class InvalidCredentials(exceptions.HomeAssistantError):
    """Error to indicate invalid credentials."""
