"""Reolink Camera Media Source Implementation."""

import datetime as dt
import logging
import os
import secrets

from typing         import Optional
from urllib.parse   import quote_plus, unquote_plus
from aiohttp        import web
from dateutil       import relativedelta

import homeassistant.util.dt as dt_utils

from homeassistant.components.stream.const          import HLS_PROVIDER
from homeassistant.components.http.const            import KEY_AUTHENTICATED
from homeassistant.core                             import HomeAssistant, callback
from homeassistant.helpers.event                    import async_call_later
from homeassistant.components.http                  import HomeAssistantView
from homeassistant.components.stream                import create_stream
from homeassistant.components.media_player.errors   import BrowseError
from homeassistant.components.media_source.const    import MEDIA_MIME_TYPES
from homeassistant.components.media_source.error    import MediaSourceError, Unresolvable
from homeassistant.components.media_source.models   import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.components.media_player.const    import (
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_VIDEO,
    MEDIA_TYPE_VIDEO,
)

# from . import typings
from .host  import ReolinkHost, searchtime_to_datetime
from .const import (
    HOST,
    DOMAIN,
    DOMAIN_DATA,
    LONG_TOKENS,
    MEDIA_SOURCE,
    SHORT_TOKENS,
    THUMBNAIL_EXTENSION,
    THUMBNAIL_URL,
    VOD_URL,
)

_LOGGER         = logging.getLogger(__name__)
NAME            = "Reolink IP NVR/camera"
STORAGE_VERSION = 1


##########################################################################################################################################################
#
##########################################################################################################################################################
async def async_get_media_source(hass: HomeAssistant):
    """Set up Reolink media source."""

    _LOGGER.debug("Creating Reolink media source")

    source = ReolinkMediaSource(hass)
    hass.http.register_view(ReolinkSourceThumbnailView(hass))
    hass.http.register_view(ReolinkSourceVODView(hass))

    return source
#endof async_get_media_source()


##########################################################################################################################################################
#
##########################################################################################################################################################
class ReolinkMediaSource(MediaSource):
    """Provide Reolink camera recordings as media sources."""

    name: str = NAME

    def __init__(self, hass: HomeAssistant):
        super().__init__(DOMAIN)

        self.hass                       = hass
        self._last_token: dt.datetime   = None
        # self._stream_prefs: DynamicStreamSettings = DynamicStreamSettings()
    #endof __init__()


    ##############################################################################
    # Properties
    @property
    def _short_security_token(self):
        def clear_token():
            tokens.remove(token)

        data: dict          = self.hass.data.setdefault(DOMAIN_DATA, {})
        data                = data.setdefault(MEDIA_SOURCE, {})
        tokens: list[str]   = data.setdefault(SHORT_TOKENS, [])

        if len(tokens) < 1 or (self._last_token and (self._last_token - dt_utils.now()).seconds >= 1800):
            self._last_token = dt_utils.now()
            tokens.append(secrets.token_hex())
            async_call_later(self.hass, 3600, clear_token)

        token = next(iter(tokens), None)
        return token
    #endof _short_security_token()


    ##############################################################################
    # Overrides
    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a media item to a playable item."""
        _, entry_id, camera_id, event_id = async_parse_identifier(item)

        data: dict          = self.hass.data[self.domain]
        entry: dict         = data.get(entry_id) if entry_id else None
        host: ReolinkHost   = entry.get(HOST) if entry else None
        if not host:
            raise BrowseError("Host entry {} in domain {} does not exist.".format(entry_id, self.domain))

        file = unquote_plus(event_id)
        if not file:
            raise BrowseError("Empty event passed to async_resolve_media().")

        mime_type, url = await host.api.get_vod_source(int(camera_id), file)

        try:
            from homeassistant.components.camera import DynamicStreamSettings
            from homeassistant.components.camera import CameraPreferences
            from homeassistant.components.camera import DATA_CAMERA_PREFS
            prefs: CameraPreferences = self.hass.data[DATA_CAMERA_PREFS]
            stream_prefs: DynamicStreamSettings = await prefs.get_dynamic_stream_settings(host.cameras[int(camera_id)].entity_id)
            stream = create_stream(self.hass, url, {}, dynamic_stream_settings = stream_prefs)
        except ImportError: #ModuleNotFoundError:
            stream = create_stream(self.hass, url, {})

        stream.add_provider(HLS_PROVIDER, timeout = 3600)
        url: str = stream.endpoint_url(HLS_PROVIDER)
        # #HACK: The media browser seems to have a problem with the master_playlist (it does not load the referenced playlist)
        # so we will just force the reference playlist instead, this seems to work though technically wrong
        url = url.replace("master_", "")

        return PlayMedia(url, mime_type)
    #endof async_resolve_media()


    async def async_browse_media(self, item: MediaSourceItem, media_types: tuple[str] = MEDIA_MIME_TYPES) -> BrowseMediaSource:
        try:
            source, entry_id, camera_id, event_id = async_parse_identifier(item)
        except Unresolvable as e:
            raise BrowseError(str(e)) from e

        _LOGGER.debug("Browsing %s, %s, %s, %s", source, entry_id, camera_id, event_id)

        data: dict          = self.hass.data[self.domain]
        entry: dict         = data.get(entry_id) if entry_id else None
        host: ReolinkHost   = entry.get(HOST) if entry else None
        if entry_id and not host:
            raise BrowseError("Host entry {} in domain {} does not exist.".format(entry_id, self.domain))

        if event_id and "/" not in event_id:
            raise BrowseError("Event {} does not exist.".format(event_id))

        return await self._async_browse_media(source, entry_id, camera_id, event_id, host)
    #endof async_browse_media()


    ##############################################################################
    # Methods
    async def _async_browse_media(
        self,
        source: str,
        entry_id: str       = None,
        camera_id: str      = None,
        event_id: str       = None,
        host: ReolinkHost   = None
    ) -> BrowseMediaSource:
        """ Actual browse after input validation """

        start_date: dt.datetime = None

        def create_item(title: str, path: str, thumbnail: bool = False):
            nonlocal self, entry_id, camera_id, event_id, start_date

            if not title or not path:
                if event_id and "/" in event_id:
                    year, *rest = event_id.split("/", 3)
                    month = rest[0] if len(rest) > 0 else None
                    day = rest[1] if len(rest) > 1 else None

                    start_date = dt.datetime.combine(
                        dt.date(
                            int(year),
                            int(month) if month else 1,
                            int(day) if day else 1,
                        ),
                        dt.time.min,
                        dt_utils.now().tzinfo,
                    )

                    title = f"{start_date.date()}"
                    path = f"{source}/{entry_id}/{camera_id}/{event_id}"
                elif host:
                    title = host.api.camera_name(int(camera_id))
                    path = f"{source}/{entry_id}/{camera_id}"
                else:
                    title = self.name
                    path = source + "/"

            media_class = (
                MEDIA_CLASS_DIRECTORY
                if not event_id or "/" in event_id
                else MEDIA_CLASS_VIDEO
            )

            media = BrowseMediaSource(
                domain              = self.domain,
                identifier          = path,
                media_class         = media_class,
                media_content_type  = MEDIA_TYPE_VIDEO,
                title               = title,
                can_play            = not bool(media_class == MEDIA_CLASS_DIRECTORY),
                can_expand          = bool(media_class == MEDIA_CLASS_DIRECTORY),
            )

            if thumbnail:
                url = THUMBNAIL_URL.format(entry_id = entry_id, camera_id = camera_id, event_id = event_id)
                # cannot do authsign as we are in a websocket and isloated from auth and context
                # we will continue to use custom tokens
                # request = current_request.get()
                # refresh_token_id = request.get(KEY_HASS_REFRESH_TOKEN_ID)
                # if not refresh_token_id:
                #     _LOGGER.debug("no token? %s", list(request.keys()))

                # # leave expiration 30 seconds?
                # media.thumbnail = async_sign_path(
                #     self.hass, refresh_token_id, url, dt.timedelta(seconds = 30)
                # )
                media.thumbnail = f"{url}?token={self._short_security_token}"

            if not media.can_play and not media.can_expand:
                _LOGGER.debug("Entry id %s: camera %s with event %s without media url found", entry_id, camera_id, event_id)
                raise IncompatibleMediaSource

            return media
        #endof create_item()


        def create_root_children():
            nonlocal host, entry_id, camera_id

            children = []
            data: dict[str, dict] = self.hass.data[self.domain]
            for cur_entry_id in data:
                entry = data[cur_entry_id]
                if not isinstance(entry, dict) or HOST not in entry:
                    continue
                host = entry[HOST]
                if host.api.hdd_info is None:
                    continue
                entry_id = cur_entry_id
                for channel in host.api.channels:
                    camera_id = channel
                    child = create_item(None, None)
                    children.append(child)

            return children
        #endof create_root_children()


        async def create_day_children():
            nonlocal camera_id, event_id

            children    = []
            end_date    = dt_utils.now()
            start_date  = dt.datetime.combine(end_date.date(), dt.time.min)
            if host.playback_days > 0:
                start_date -= relativedelta.relativedelta(days = int(host.playback_days))

            # Cleanup older thumbnail files, to not overfill the drive...
            start_date_timestamp = start_date.timestamp()
            directory = os.path.join(host.thumbnail_path, f"{camera_id}")
            if not os.path.isdir(directory):
                os.makedirs(directory)
            else:
                for f in os.listdir(directory):
                    f = os.path.join(directory, f)
                    if os.stat(f).st_mtime < start_date_timestamp:
                        os.remove(f)

            search, _ = await host.api.request_vod_files(int(camera_id), start_date, end_date, True)

            if not search is None:
                for status in search:
                    year  = status["year"]
                    month = status["mon"]
                    for day, flag in enumerate(status["table"], start = 1):
                        if flag == "1":
                            event_id = f"{year}/{month}/{day}"
                            child = create_item(None, None)
                            children.append(child)

            children.reverse()
            return children
        #endof create_day_children()


        async def create_vod_children():
            nonlocal host, start_date, entry_id, camera_id, event_id

            children = []
            end_date = dt.datetime.combine(start_date.date(), dt.time.max, start_date.tzinfo)

            directory = os.path.join(host.thumbnail_path, f"{camera_id}")

            _, files = await host.api.request_vod_files(int(camera_id), start_date, end_date)

            for file in files:
                end_date    = searchtime_to_datetime(file["EndTime"], end_date.tzinfo)
                start_date  = searchtime_to_datetime(file["StartTime"], end_date.tzinfo)
                event_id    = str(start_date.timestamp())

                filename = None
                if host.api.is_nvr:
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

                evt_id = f"{entry_id}/{camera_id}/{quote_plus(filename)}"
                # self._file_cache[evt_id] = filename

                thumbnail_file = os.path.join(directory, f"{event_id}.{THUMBNAIL_EXTENSION}")
                # Could fill-in possible lack of thumbnails, but these would be just current-time shots...
                # if not os.path.isfile(thumbnail_file):
                #     if camera_id in host.cameras:
                #         service_data = {
                #             ATTR_ENTITY_ID: host.cameras[camera_id].entity_id,
                #             ATTR_FILENAME: thumbnail_file,
                #         }
                #         await self.hass.services.async_call(CAMERA_DOMAIN, SERVICE_SNAPSHOT, service_data, blocking = True)

                thumbnail = os.path.isfile(thumbnail_file)

                time        = start_date.time()
                duration    = end_date - start_date
                #size        = file["size"]
                child       = create_item(f"{time} {duration}", f"{source}/{evt_id}", thumbnail)
                children.append(child)

            children.reverse()

            return children
        #endof create_vod_children()


        if host and event_id and "/" not in event_id:
            event = host.in_memory_events[event_id]
            start_date = event.start

        media = create_item(None, None)

        if not media.can_expand:
            return media

        if not entry_id:
            media.children = create_root_children()
            return media

        if not start_date:
            media.children = await create_day_children()
        else:
            media.children = await create_vod_children()

        return media
    #endof _async_browse_media
#endof class ReolinkMediaSource


##########################################################################################################################################################
#
##########################################################################################################################################################
class ReolinkSourceVODView(HomeAssistantView):
    """ VOD security handler """

    url             = VOD_URL
    name            = "api:" + DOMAIN + ":video"
    cors_allowed    = True
    requires_auth   = False

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str, camera_id: str, event_id: str) -> web.Response:
        """ Start a GET request. """

        authenticated = request.get(KEY_AUTHENTICATED, False)
        if not authenticated:
            token: str = request.query.get("token")
            if not token:
                raise web.HTTPUnauthorized()

            data: dict          = self.hass.data.get(DOMAIN_DATA)
            data                = data.get(MEDIA_SOURCE) if data else None
            tokens: list[str]   = data.get(LONG_TOKENS) if data else None
            if not tokens or not token in tokens:
                raise web.HTTPUnauthorized()

        if not entry_id or not camera_id or not event_id:
            raise web.HTTPNotFound()

        data: dict[str, dict]   = self.hass.data[DOMAIN]
        host: ReolinkHost       = (data[entry_id].get(HOST, None) if entry_id in data else None)
        if not host:
            _LOGGER.debug("Source VoD view: camera %s:%s not found.", entry_id, camera_id)
            raise web.HTTPNotFound()

        file = unquote_plus(event_id)
        _, url = await host.api.get_vod_source(int(camera_id), file)
        return web.HTTPTemporaryRedirect(url)
#endof class ReolinkSourceVODView


##########################################################################################################################################################
#
##########################################################################################################################################################
class ReolinkSourceThumbnailView(HomeAssistantView):
    """ Thumbnial view handler """

    url             = THUMBNAIL_URL
    name            = "api:" + DOMAIN + ":image"
    cors_allowed    = True
    requires_auth   = False

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str, camera_id: str, event_id: str) -> web.Response:
        """ Start a GET request. """

        authenticated = request.get(KEY_AUTHENTICATED, False)
        if not authenticated:
            token: str = request.query.get("token")
            if not token:
                raise web.HTTPUnauthorized()

            data: dict          = self.hass.data.get(DOMAIN_DATA)
            data                = data.get(MEDIA_SOURCE) if data else None
            tokens: list[str]   = data.get(SHORT_TOKENS) if data else None
            if not tokens or not token in tokens:
                raise web.HTTPUnauthorized()

        if not entry_id or not camera_id or not event_id:
            raise web.HTTPNotFound()

        data: dict[str, dict]   = self.hass.data[DOMAIN]
        host: ReolinkHost       = (data[entry_id].get(HOST, None) if entry_id in data else None)
        if not host:
            _LOGGER.debug("Thumbnail view: camera %s:%s not found.", entry_id, camera_id)
            raise web.HTTPNotFound()

        thumbnail = f"{host.thumbnail_path}/{camera_id}/{event_id}.{THUMBNAIL_EXTENSION}"
        return web.FileResponse(thumbnail)
#endof class ReolinkSourceThumbnailView


##########################################################################################################################################################
# Globals
##########################################################################################################################################################
@callback
def async_parse_identifier(item: MediaSourceItem) -> tuple[str, str, str, Optional[str]]:
    if not item.identifier:
        return "events", "", "", None

    source, path = item.identifier.lstrip("/").split("/", 1)

    if source != "events":
        raise Unresolvable("Unknown source directory.")

    if "/" in path:
        camera_id = None
        event_id  = None

        entry_id, path = path.split("/", 1)
        if "/" in path:
            camera_id, event_id = path.split("/", 1)
        else:
            camera_id = path

        return source, entry_id, camera_id, event_id

    return source, path, "", None
#endof async_parse_identifier()


class IncompatibleMediaSource(MediaSourceError):
    """Incompatible media source attributes."""
