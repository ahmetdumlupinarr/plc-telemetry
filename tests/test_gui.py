from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_offline_viewer_loads_session(sample_session: Path) -> None:
    pytest.importorskip("PySide6")
    pytest.importorskip("pyqtgraph")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication
    from plc_telemetry.gui.app import OfflineViewerWindow

    app = QApplication.instance() or QApplication([])
    window = OfflineViewerWindow(sample_session)

    assert sample_session.name in window.windowTitle()
    window.close()
