"""Headless recording service."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from plc_telemetry.core.models.enums import SessionStatus
from plc_telemetry.core.models.sample import Sample
from plc_telemetry.core.models.session_manifest import SessionManifest
from plc_telemetry.core.models.signal_definition import SignalDefinition
from plc_telemetry.core.storage.session_writer import SessionWriter
from plc_telemetry.transports.base.adapter import TransportAdapter
from plc_telemetry.utils.session_paths import utc_now

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecordResult:
    manifest: SessionManifest
    session_path: Path


class RecorderService:
    """Consumes transport data and writes it to storage."""

    def __init__(self, max_queue_size: int = 256, flush_batch_size: int = 128) -> None:
        self._max_queue_size = max_queue_size
        self._flush_batch_size = flush_batch_size

    def record(
        self,
        transport: TransportAdapter,
        channels: Iterable[SignalDefinition],
        manifest: SessionManifest,
        writer: SessionWriter,
        stop_event: Optional[threading.Event] = None,
        max_batches: Optional[int] = None,
    ) -> RecordResult:
        channel_list = [channel for channel in channels if channel.enabled]
        queue_: "queue.Queue[List[Sample]]" = queue.Queue(maxsize=self._max_queue_size)
        completion_event = stop_event or threading.Event()
        stats = {
            "sample_count": 0,
            "batch_count": 0,
            "drop_count": 0,
            "backlog_high_watermark": 0,
        }
        producer_error: List[BaseException] = []

        def producer() -> None:
            batches_seen = 0
            try:
                transport.connect()
                transport.start(manifest.session_id, channel_list)
                while not completion_event.is_set():
                    batch = transport.read_batch()
                    if batch:
                        try:
                            queue_.put(batch, timeout=0.2)
                            stats["backlog_high_watermark"] = max(
                                stats["backlog_high_watermark"],
                                queue_.qsize(),
                            )
                        except queue.Full:
                            stats["drop_count"] += len(batch)
                            LOGGER.warning(
                                "Dropping %s samples because recorder queue is full",
                                len(batch),
                            )
                    batches_seen += 1
                    if max_batches is not None and batches_seen >= max_batches:
                        completion_event.set()
                        break
            except BaseException as exc:  # pragma: no cover - exception path is environment-dependent
                producer_error.append(exc)
                completion_event.set()
            finally:
                try:
                    transport.stop()
                finally:
                    transport.disconnect()

        producer_thread = threading.Thread(target=producer, name="telemetry-producer", daemon=True)
        producer_thread.start()

        try:
            while producer_thread.is_alive() or not queue_.empty():
                try:
                    batch = queue_.get(timeout=0.2)
                except queue.Empty:
                    continue
                buffer = [batch]
                while len(buffer) < self._flush_batch_size:
                    try:
                        buffer.append(queue_.get_nowait())
                    except queue.Empty:
                        break
                flattened = [sample for item in buffer for sample in item]
                writer.write_samples(flattened)
                stats["sample_count"] += len(flattened)
                stats["batch_count"] += len(buffer)
        except KeyboardInterrupt:
            LOGGER.info("Stopping recording because of keyboard interrupt")
            completion_event.set()
        finally:
            completion_event.set()
            producer_thread.join(timeout=5.0)

        if producer_error:
            manifest.status = SessionStatus.FAILED
            manifest.end_time = utc_now()
            manifest.stats = stats
            writer.write_manifest(manifest)
            writer.close()
            raise RuntimeError("recording failed") from producer_error[0]

        manifest.status = SessionStatus.COMPLETED
        manifest.end_time = utc_now()
        manifest.stats = stats
        writer.write_manifest(manifest)
        writer.close()
        return RecordResult(manifest=manifest, session_path=Path(writer.session_path))
