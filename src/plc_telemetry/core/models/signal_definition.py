"""Signal metadata model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from .enums import DisplayHint, SampleMode, SignalType


@dataclass(frozen=True)
class SignalDefinition:
    """Defines a telemetry channel."""

    channel_id: int
    name: str
    path: str
    value_type: SignalType
    unit: Optional[str]
    group: Optional[str]
    description: Optional[str]
    display_hint: DisplayHint
    sample_mode: SampleMode
    sample_interval_ms: Optional[int]
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.channel_id < 0:
            raise ValueError("channel_id must be >= 0")
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.path:
            raise ValueError("path must not be empty")
        if self.sample_interval_ms is not None and self.sample_interval_ms <= 0:
            raise ValueError("sample_interval_ms must be > 0")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["value_type"] = self.value_type.value
        data["display_hint"] = self.display_hint.value
        data["sample_mode"] = self.sample_mode.value
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SignalDefinition":
        return cls(
            channel_id=int(payload["channel_id"]),
            name=str(payload["name"]),
            path=str(payload["path"]),
            value_type=SignalType(str(payload["value_type"]).lower()),
            unit=payload.get("unit"),
            group=payload.get("group"),
            description=payload.get("description"),
            display_hint=DisplayHint(str(payload.get("display_hint", DisplayHint.PLOT.value)).lower()),
            sample_mode=SampleMode(str(payload.get("sample_mode", SampleMode.CYCLIC.value)).lower()),
            sample_interval_ms=(
                int(payload["sample_interval_ms"])
                if payload.get("sample_interval_ms") is not None
                else None
            ),
            enabled=bool(payload.get("enabled", True)),
        )
