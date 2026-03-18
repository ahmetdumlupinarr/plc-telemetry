from __future__ import annotations

from datetime import timedelta

from plc_telemetry.core.models.enums import SessionStatus, TransportType
from plc_telemetry.core.models.session_manifest import SessionManifest
from plc_telemetry.utils.session_paths import build_session_id, utc_now


def test_session_manifest_roundtrip() -> None:
    start = utc_now()
    manifest = SessionManifest(
        session_id="test_session",
        project_name="demo",
        transport=TransportType.ADS,
        schema_version=1,
        app_version="1.0.0",
        start_time=start,
        end_time=start + timedelta(seconds=5),
        channel_count=2,
        logged_channels=[1, 2],
        notes="demo",
        status=SessionStatus.COMPLETED,
        storage_path="sessions/test_session",
        stats={"sample_count": 10},
    )

    restored = SessionManifest.from_dict(manifest.to_dict())

    assert restored.session_id == manifest.session_id
    assert restored.status == SessionStatus.COMPLETED
    assert restored.stats["sample_count"] == 10


def test_build_session_id_sanitizes_prefix() -> None:
    session_id = build_session_id("Azimuth Test 001")

    assert session_id.endswith("Azimuth_Test_001")
