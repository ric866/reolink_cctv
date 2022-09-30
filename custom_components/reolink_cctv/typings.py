""" Typing Definitions """

from dataclasses    import dataclass
from datetime       import datetime, timedelta


@dataclass
class VoDRecordThumbnail:
    url: str        = None
    exists: bool    = None
    path: str       = None


@dataclass
class VoDRecord:
    event_id: str                   = None
    start: datetime                 = None
    duration: timedelta             = None
    file: str                       = None
    url: str                        = None
    cam_record_url: str             = None
    thumbnail: VoDRecordThumbnail   = None
