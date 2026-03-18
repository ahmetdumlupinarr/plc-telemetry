"""ADS polling adapter."""

from __future__ import annotations

import logging
import time
from typing import Iterable, List, Optional

from plc_telemetry.core.config.loader import AdsConfig
from plc_telemetry.core.models.enums import Quality
from plc_telemetry.core.models.sample import Sample
from plc_telemetry.core.models.signal_definition import SignalDefinition
from plc_telemetry.transports.ads.symbol_reader import AdsSymbolReader
from plc_telemetry.transports.base.adapter import TransportAdapter, TransportHealth

LOGGER = logging.getLogger(__name__)


class AdsAdapter(TransportAdapter):
    """Polling transport for Beckhoff ADS symbols."""

    def __init__(self, config: AdsConfig, reader: Optional[AdsSymbolReader] = None) -> None:
        self._config = config
        self._reader = reader or AdsSymbolReader(
            ams_net_id=config.ams_net_id,
            port=config.port,
            timeout_ms=config.timeout_ms,
        )
        self._channels: List[SignalDefinition] = []
        self._connected = False
        self._running = False
        self._session_id = ""
        self._last_cycle_started = 0.0
        self._drops = 0
        self._last_error: Optional[str] = None

    def connect(self) -> None:
        self._reader.connect()
        self._connected = True

    def disconnect(self) -> None:
        self._reader.disconnect()
        self._connected = False

    def start(self, session_id: str, channels: Iterable[SignalDefinition]) -> None:
        self._session_id = session_id
        self._channels = [channel for channel in channels if channel.enabled]
        self._running = True

    def stop(self) -> None:
        self._running = False

    def read_batch(self) -> List[Sample]:
        if not self._running:
            return []

        batch: List[Sample] = []
        self._last_cycle_started = time.monotonic()
        for channel in self._channels:
            timestamp_ns = time.time_ns()
            try:
                raw_value = self._reader.read(channel.path)
                batch.append(
                    self._build_sample(
                        channel=channel,
                        raw_value=raw_value,
                        pc_timestamp_ns=timestamp_ns,
                        quality=Quality.GOOD,
                    )
                )
            except TimeoutError:
                LOGGER.warning("ADS timeout while reading %s", channel.path)
                batch.append(
                    Sample(
                        session_id=self._session_id,
                        channel_id=channel.channel_id,
                        pc_timestamp_ns=timestamp_ns,
                        quality=Quality.TIMEOUT,
                    )
                )
            except Exception as exc:  # pragma: no cover - depends on ADS runtime
                self._last_error = str(exc)
                LOGGER.exception("ADS read failed for %s", channel.path)
                batch.append(
                    Sample(
                        session_id=self._session_id,
                        channel_id=channel.channel_id,
                        pc_timestamp_ns=timestamp_ns,
                        quality=Quality.INVALID,
                    )
                )

        sleep_seconds = max(0.0, self._config.poll_interval_ms / 1000.0 - (time.monotonic() - self._last_cycle_started))
        if sleep_seconds:
            time.sleep(sleep_seconds)
        return batch

    def health(self) -> TransportHealth:
        return TransportHealth(
            connected=self._connected,
            drops=self._drops,
            details={
                "transport": "ads",
                "poll_interval_ms": self._config.poll_interval_ms,
                "last_error": self._last_error,
                "channels": len(self._channels),
            },
        )

    def _build_sample(
        self,
        channel: SignalDefinition,
        raw_value: object,
        pc_timestamp_ns: int,
        quality: Quality,
    ) -> Sample:
        numeric_value = None
        bool_value = None
        text_value = None

        if channel.value_type.is_boolean:
            bool_value = bool(raw_value)
        elif channel.value_type.is_text:
            text_value = str(raw_value)
        else:
            numeric_value = float(raw_value)

        return Sample(
            session_id=self._session_id,
            channel_id=channel.channel_id,
            pc_timestamp_ns=pc_timestamp_ns,
            quality=quality,
            value_numeric=numeric_value,
            value_bool=bool_value,
            value_text=text_value,
        )
