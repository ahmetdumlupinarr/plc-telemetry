"""Session writing primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

import pyarrow as pa
import pyarrow.parquet as pq

from plc_telemetry.core.models.sample import Sample
from plc_telemetry.core.models.session_manifest import SessionManifest
from plc_telemetry.core.models.signal_definition import SignalDefinition
from plc_telemetry.utils.session_paths import ensure_directory


SAMPLE_SCHEMA = pa.schema(
    [
        ("session_id", pa.string()),
        ("channel_id", pa.int64()),
        ("pc_timestamp_ns", pa.int64()),
        ("plc_timestamp_ns", pa.int64()),
        ("value_numeric", pa.float64()),
        ("value_bool", pa.bool_()),
        ("value_text", pa.string()),
        ("quality", pa.string()),
        ("sequence_no", pa.int64()),
    ]
)


class SessionWriter:
    """Writes metadata and sample batches into a session folder."""

    def __init__(self, session_path: Path) -> None:
        self.session_path = ensure_directory(session_path)
        self._parquet_writer = pq.ParquetWriter(
            where=str(self.session_path / "samples.parquet"),
            schema=SAMPLE_SCHEMA,
            compression="zstd",
        )
        (self.session_path / "events.jsonl").touch(exist_ok=True)

    def write_metadata(
        self,
        manifest: SessionManifest,
        channels: Iterable[SignalDefinition],
    ) -> None:
        (self.session_path / "session.json").write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        channel_payload = [channel.to_dict() for channel in channels]
        (self.session_path / "channels.json").write_text(
            json.dumps(channel_payload, indent=2),
            encoding="utf-8",
        )

    def write_samples(self, samples: List[Sample]) -> None:
        if not samples:
            return
        table = pa.Table.from_pylist([sample.to_record() for sample in samples], schema=SAMPLE_SCHEMA)
        self._parquet_writer.write_table(table)

    def write_manifest(self, manifest: SessionManifest) -> None:
        (self.session_path / "session.json").write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )

    def close(self) -> None:
        self._parquet_writer.close()
