"""Telemetry sample model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .enums import Quality


@dataclass(frozen=True)
class Sample:
    """Normalized telemetry sample."""

    session_id: str
    channel_id: int
    pc_timestamp_ns: int
    quality: Quality
    plc_timestamp_ns: Optional[int] = None
    value_numeric: Optional[float] = None
    value_bool: Optional[bool] = None
    value_text: Optional[str] = None
    sequence_no: Optional[int] = None

    def __post_init__(self) -> None:
        if self.channel_id < 0:
            raise ValueError("channel_id must be >= 0")
        if self.pc_timestamp_ns <= 0:
            raise ValueError("pc_timestamp_ns must be > 0")
        populated = sum(
            value is not None
            for value in (self.value_numeric, self.value_bool, self.value_text)
        )
        if populated > 1:
            raise ValueError("sample can only carry one typed value field")

    def to_record(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "channel_id": self.channel_id,
            "pc_timestamp_ns": self.pc_timestamp_ns,
            "plc_timestamp_ns": self.plc_timestamp_ns,
            "value_numeric": self.value_numeric,
            "value_bool": self.value_bool,
            "value_text": self.value_text,
            "quality": self.quality.value,
            "sequence_no": self.sequence_no,
        }
