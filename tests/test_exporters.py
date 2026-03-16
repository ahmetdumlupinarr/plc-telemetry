from __future__ import annotations

from pathlib import Path

from plc_telemetry.core.storage.exporters import ExportService
from plc_telemetry.core.storage.session_reader import SessionReader


def test_export_service_writes_csv_and_png(sample_session: Path, tmp_path: Path) -> None:
    service = ExportService(SessionReader(sample_session))

    csv_path = service.export_csv(tmp_path / "out" / "session.csv", channels=["ActPos"])
    png_path = service.export_png(tmp_path / "out" / "session.png", channels=["ActPos", "AxisReady"])

    assert csv_path.exists()
    assert png_path.exists()
    assert csv_path.read_text(encoding="utf-8").startswith("session_id")
