"""Domain enumerations."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Small backport-friendly string enum base."""

    def __str__(self) -> str:
        return self.value


class SignalType(StrEnum):
    BOOL = "bool"
    INT = "int"
    DINT = "dint"
    LINT = "lint"
    UINT = "uint"
    UDINT = "udint"
    ULINT = "ulint"
    REAL = "real"
    LREAL = "lreal"
    STRING = "string"

    @property
    def is_numeric(self) -> bool:
        return self not in {SignalType.BOOL, SignalType.STRING}

    @property
    def is_boolean(self) -> bool:
        return self is SignalType.BOOL

    @property
    def is_text(self) -> bool:
        return self is SignalType.STRING


class DisplayHint(StrEnum):
    PLOT = "plot"
    BOOL = "bool"
    TEXT = "text"


class SampleMode(StrEnum):
    CYCLIC = "cyclic"
    ON_CHANGE = "on_change"
    TRIGGERED_SNAPSHOT = "triggered_snapshot"


class Quality(StrEnum):
    GOOD = "good"
    STALE = "stale"
    TIMEOUT = "timeout"
    INVALID = "invalid"
    DROPPED = "dropped"
    EXTRAPOLATED = "extrapolated"


class TransportType(StrEnum):
    ADS = "ads"
    UDP = "udp"


class SessionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
