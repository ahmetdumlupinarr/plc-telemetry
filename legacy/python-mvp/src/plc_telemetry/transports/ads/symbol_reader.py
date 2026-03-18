"""Thin abstraction around ADS symbol reads."""

from __future__ import annotations

from typing import Any


class AdsSymbolReader:
    """Wraps pyads access behind a testable interface."""

    def __init__(self, ams_net_id: str, port: int, timeout_ms: int = 500) -> None:
        self._ams_net_id = ams_net_id
        self._port = port
        self._timeout_ms = timeout_ms
        self._connection = None

    def connect(self) -> None:
        try:
            import pyads
        except ImportError as exc:
            raise RuntimeError(
                "pyads is required for ADS transport. Install project dependencies first."
            ) from exc

        self._connection = pyads.Connection(self._ams_net_id, self._port)
        self._connection.open()
        self._connection.set_timeout(self._timeout_ms)

    def disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def read(self, symbol_path: str) -> Any:
        if self._connection is None:
            raise RuntimeError("ADS connection is not open")
        return self._connection.read_by_name(symbol_path)
