"""Constants for the Reolink Camera integration."""

DOMAIN                                  = "reolink_cctv"
DOMAIN_DATA                             = "reolink_cctv_devices"
EVENT_DATA_RECEIVED                     = "reolink_cctv-event"
DEVICE_CONFIG_UPDATE_COORDINATOR        = "coordinator"
SUBSCRIPTION_WATCHDOG_COORDINATOR       = "subscription_watchdog_coordinator"
HOST                                    = "host"
SESSION_RENEW_THRESHOLD                 = 300
MEDIA_SOURCE                            = "media_source"
THUMBNAIL_VIEW                          = "thumbnail_view"
SHORT_TOKENS                            = "short_tokens"
LONG_TOKENS                             = "long_tokens"
LAST_RECORD                             = "last_record"

CONF_EXTERNAL_HOST                      = "external_host"
CONF_EXTERNAL_PORT                      = "external_port"
CONF_USE_HTTPS                          = "use_https"
CONF_STREAM                             = "stream"
CONF_STREAM_FORMAT                      = "stream_format"
CONF_PROTOCOL                           = "protocol"
CONF_CHANNELS                           = "channels"
CONF_MOTION_OFF_DELAY                   = "motion_off_delay"
CONF_MOTION_FORCE_OFF                   = "motion_force_off"
CONF_PLAYBACK_MONTHS                    = "playback_months"
CONF_THUMBNAIL_PATH                     = "playback_thumbnail_path"
CONF_SUBSCRIPTION_WATCHDOG_INTERVAL     = "subscription_watchdog_interval"

DEFAULT_EXTERNAL_HOST                   = ""
DEFAULT_EXTERNAL_PORT                   = ""
DEFAULT_USE_HTTPS                       = False
DEFAULT_CHANNELS                        = [0]
DEFAULT_MOTION_OFF_DELAY                = 5
DEFAULT_MOTION_FORCE_OFF                = 0
DEFAULT_PROTOCOL                        = "rtmp"
DEFAULT_STREAM                          = "sub"
DEFAULT_STREAM_FORMAT                   = "h264"
DEFAULT_SUBSCRIPTION_WATCHDOG_INTERVAL  = 60

DEFAULT_TIMEOUT                         = 60
DEFAULT_PLAYBACK_MONTHS                 = 2
DEFAULT_THUMBNAIL_OFFSET                = 6

SUPPORT_PTZ                             = 1024
SUPPORT_PLAYBACK                        = 2048

SERVICE_PTZ_CONTROL                     = "ptz_control"
SERVICE_SET_BACKLIGHT                   = "set_backlight"
SERVICE_SET_DAYNIGHT                    = "set_daynight"
SERVICE_SET_SENSITIVITY                 = "set_sensitivity"

SERVICE_COMMIT_THUMBNAILS               = "commit_thumbnails"
SERVICE_CLEANUP_THUMBNAILS              = "cleanup_thumbnails"

THUMBNAIL_EXTENSION                     = "jpg"

MOTION_WATCHDOG_TYPE                    = "motion_watchdog"
MOTION_COMMON_TYPE                      = "motion_common"

THUMBNAIL_URL   = "/api/" + DOMAIN + "/media_proxy/{entry_id}/{camera_id}/{event_id}.jpg"
VOD_URL         = "/api/" + DOMAIN + "/vod/{entry_id}/{camera_id}/{event_id}"
