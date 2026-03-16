"""Transport abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from plc_telemetry.core.models.sample import Sample
from plc_telemetry.core.models.signal_definition import SignalDefinition


@dataclass
class TransportHealth:
    connected: bool
    backlog: int = 0
    drops: int = 0
    details: Dict[str, object] = field(default_factory=dict)


class TransportAdapter(ABC):
    """Base transport contract."""

    @abstractmethod
    def connect(self) -> None:
        """Establish transport connection."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down transport connection."""

    @abstractmethod
    def start(self, session_id: str, channels: Iterable[SignalDefinition]) -> None:
        """Prepare transport for sample collection."""

    @abstractmethod
    def stop(self) -> None:
        """Stop sample collection."""

    @abstractmethod
    def read_batch(self) -> List[Sample]:
        """Return the next sample batch."""

    @abstractmethod
    def health(self) -> TransportHealth:
        """Return current transport health information."""
