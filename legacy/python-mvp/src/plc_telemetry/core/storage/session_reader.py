"""Session reading primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Union

import polars as pl

from plc_telemetry.core.models.session_manifest import SessionManifest
from plc_telemetry.core.models.signal_definition import SignalDefinition


class SessionReader:
    """Loads a recorded session."""

    def __init__(self, session_path: Union[str, Path]) -> None:
        self.session_path = Path(session_path)

    def read_manifest(self) -> SessionManifest:
        payload = json.loads((self.session_path / "session.json").read_text(encoding="utf-8"))
        manifest = SessionManifest.from_dict(payload)
        manifest.storage_path = str(self.session_path)
        return manifest

    def read_channels(self) -> List[SignalDefinition]:
        payload = json.loads((self.session_path / "channels.json").read_text(encoding="utf-8"))
        return [SignalDefinition.from_dict(item) for item in payload]

    def read_samples(self) -> pl.DataFrame:
        return pl.read_parquet(self.session_path / "samples.parquet")
