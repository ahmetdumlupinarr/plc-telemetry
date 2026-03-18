"""Session metadata model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .enums import SessionStatus, TransportType


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass
class SessionManifest:
    """Represents a recording session manifest."""

    session_id: str
    project_name: str
    transport: TransportType
    schema_version: int
    app_version: str
    start_time: datetime
    end_time: Optional[datetime]
    channel_count: int
    logged_channels: List[int]
    notes: Optional[str] = None
    status: SessionStatus = SessionStatus.RUNNING
    storage_path: Optional[str] = None
    description: Optional[str] = None
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "transport": self.transport.value,
            "schema_version": self.schema_version,
            "app_version": self.app_version,
            "start_time": _ensure_utc(self.start_time).isoformat(),
            "end_time": _ensure_utc(self.end_time).isoformat() if self.end_time else None,
            "channel_count": self.channel_count,
            "logged_channels": self.logged_channels,
            "notes": self.notes,
            "status": self.status.value,
            "storage_path": self.storage_path,
            "description": self.description,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SessionManifest":
        end_time = payload.get("end_time")
        return cls(
            session_id=str(payload["session_id"]),
            project_name=str(payload["project_name"]),
            transport=TransportType(str(payload["transport"]).lower()),
            schema_version=int(payload["schema_version"]),
            app_version=str(payload["app_version"]),
            start_time=datetime.fromisoformat(str(payload["start_time"])),
            end_time=datetime.fromisoformat(str(end_time)) if end_time else None,
            channel_count=int(payload["channel_count"]),
            logged_channels=[int(item) for item in payload.get("logged_channels", [])],
            notes=payload.get("notes"),
            status=SessionStatus(str(payload.get("status", SessionStatus.RUNNING.value)).lower()),
            storage_path=payload.get("storage_path"),
            description=payload.get("description"),
            stats=dict(payload.get("stats", {})),
        )
