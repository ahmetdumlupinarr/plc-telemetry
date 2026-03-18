from __future__ import annotations

from typing import Iterable, List

from plc_telemetry.core.models.enums import Quality
from plc_telemetry.core.models.sample import Sample
from plc_telemetry.core.recorder.recorder_service import RecorderService
from plc_telemetry.core.recorder.session_service import SessionService
from plc_telemetry.core.storage.session_reader import SessionReader
from plc_telemetry.transports.base.adapter import TransportAdapter, TransportHealth


class FakeTransport(TransportAdapter):
    def __init__(self, batches: List[List[Sample]]) -> None:
        self._batches = list(batches)
        self.connected = False
        self.started = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def start(self, session_id: str, channels: Iterable[object]) -> None:
        self.started = True
        self.session_id = session_id
        self.channels = list(channels)

    def stop(self) -> None:
        self.started = False

    def read_batch(self) -> List[Sample]:
        if not self._batches:
            return []
        return self._batches.pop(0)

    def health(self) -> TransportHealth:
        return TransportHealth(connected=self.connected)


def test_recording_pipeline_writes_session(app_config) -> None:
    session_service = SessionService(app_config)
    prepared = session_service.create_session(app_config.channels)
    batches = [
        [
            Sample(
                session_id=prepared.manifest.session_id,
                channel_id=1,
                pc_timestamp_ns=1,
                quality=Quality.GOOD,
                value_numeric=10.0,
            ),
            Sample(
                session_id=prepared.manifest.session_id,
                channel_id=2,
                pc_timestamp_ns=1,
                quality=Quality.GOOD,
                value_bool=True,
            ),
        ],
        [
            Sample(
                session_id=prepared.manifest.session_id,
                channel_id=1,
                pc_timestamp_ns=2,
                quality=Quality.GOOD,
                value_numeric=12.0,
            )
        ],
    ]
    transport = FakeTransport(batches=batches)
    recorder = RecorderService(max_queue_size=4, flush_batch_size=2)

    result = recorder.record(
        transport=transport,
        channels=app_config.channels,
        manifest=prepared.manifest,
        writer=prepared.writer,
        max_batches=2,
    )

    reader = SessionReader(result.session_path)
    manifest = reader.read_manifest()
    frame = reader.read_samples()

    assert manifest.status.value == "completed"
    assert manifest.stats["sample_count"] == 3
    assert frame.height == 3
