from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from plc_telemetry.core.config.loader import AdsConfig, AppConfig, ProjectConfig, SessionConfig, TransportConfig
from plc_telemetry.core.models.enums import (
    DisplayHint,
    Quality,
    SampleMode,
    SessionStatus,
    SignalType,
    TransportType,
)
from plc_telemetry.core.models.sample import Sample
from plc_telemetry.core.models.session_manifest import SessionManifest
from plc_telemetry.core.models.signal_definition import SignalDefinition
from plc_telemetry.core.storage.session_writer import SessionWriter
from plc_telemetry.utils.session_paths import utc_now


def build_channels() -> list[SignalDefinition]:
    return [
        SignalDefinition(
            channel_id=1,
            name="ActPos",
            path="GVL.ActPos",
            value_type=SignalType.LREAL,
            unit="deg",
            group="motion",
            description="Actual position",
            display_hint=DisplayHint.PLOT,
            sample_mode=SampleMode.CYCLIC,
            sample_interval_ms=100,
            enabled=True,
        ),
        SignalDefinition(
            channel_id=2,
            name="AxisReady",
            path="GVL.AxisReady",
            value_type=SignalType.BOOL,
            unit=None,
            group="status",
            description="Axis ready",
            display_hint=DisplayHint.BOOL,
            sample_mode=SampleMode.CYCLIC,
            sample_interval_ms=100,
            enabled=True,
        ),
    ]


@pytest.fixture()
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        project=ProjectConfig(
            name="test_project",
            description="test",
            storage_root=tmp_path / "sessions",
        ),
        transport=TransportConfig(
            type=TransportType.ADS,
            ads=AdsConfig(
                ams_net_id="127.0.0.1.1.1",
                port=851,
                poll_interval_ms=1,
                timeout_ms=100,
            ),
        ),
        session=SessionConfig(
            name_prefix="unit_test",
            auto_start=False,
            manifest_notes="notes",
        ),
        channels=build_channels(),
    )


@pytest.fixture()
def sample_session(tmp_path: Path) -> Path:
    session_root = tmp_path / "sessions" / "2026-03-16_10-00-00_test_session"
    channels = build_channels()
    start_time = utc_now()
    manifest = SessionManifest(
        session_id=session_root.name,
        project_name="test_project",
        transport=TransportType.ADS,
        schema_version=1,
        app_version="1.0.0",
        start_time=start_time,
        end_time=start_time + timedelta(seconds=1),
        channel_count=len(channels),
        logged_channels=[channel.channel_id for channel in channels],
        notes="fixture",
        status=SessionStatus.COMPLETED,
        storage_path=str(session_root),
        description="fixture session",
        stats={"sample_count": 4, "batch_count": 2, "drop_count": 0},
    )
    writer = SessionWriter(session_root)
    writer.write_metadata(manifest, channels)
    writer.write_samples(
        [
            Sample(
                session_id=manifest.session_id,
                channel_id=1,
                pc_timestamp_ns=1,
                quality=Quality.GOOD,
                value_numeric=1.0,
            ),
            Sample(
                session_id=manifest.session_id,
                channel_id=2,
                pc_timestamp_ns=1,
                quality=Quality.GOOD,
                value_bool=True,
            ),
            Sample(
                session_id=manifest.session_id,
                channel_id=1,
                pc_timestamp_ns=2,
                quality=Quality.GOOD,
                value_numeric=2.5,
            ),
            Sample(
                session_id=manifest.session_id,
                channel_id=2,
                pc_timestamp_ns=2,
                quality=Quality.GOOD,
                value_bool=False,
            ),
        ]
    )
    writer.write_manifest(manifest)
    writer.close()
    return session_root
