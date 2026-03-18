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
    assert window._session_title_label.text() == sample_session.name
    assert window._status_badge.text() == "COMPLETED"
    assert "relative seconds" in window._plot_panel_subtitle.text().lower()
    assert window._grid_button.isChecked()
    assert window._legend_button.isChecked()
    assert window._channel_list.item(0).sizeHint().height() >= 20
    window.close()
