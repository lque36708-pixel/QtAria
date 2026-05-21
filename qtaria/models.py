from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DownloadStatus(Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    PAUSED = "paused"
    COMPLETED = "complete"
    ERROR = "error"
    REMOVED = "removed"


@dataclass
class Download:
    gid: str
    url: str
    filename: str
    status: DownloadStatus = DownloadStatus.WAITING
    total_length: int = 0
    completed_length: int = 0
    download_speed: int = 0
    upload_speed: int = 0
    error_message: str = ""
