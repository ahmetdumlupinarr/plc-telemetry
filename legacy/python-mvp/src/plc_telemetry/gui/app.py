"""Offline viewer application."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union

import polars as pl

from plc_telemetry.core.storage.exporters import ExportService
from plc_telemetry.core.storage.session_reader import SessionReader

try:  # pragma: no cover - import depends on GUI availability
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    from PySide6.QtCore import Qt
    import pyqtgraph as pg
except ImportError:  # pragma: no cover - exercised manually
    QApplication = None
    QFileDialog = None
    QHBoxLayout = None
    QLabel = None
    QListWidget = None
    QListWidgetItem = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QSplitter = None
    QTableWidget = None
    QTableWidgetItem = None
    QVBoxLayout = None
    QWidget = None
    Qt = None
    pg = None


class OfflineViewerWindow(QMainWindow):
    """Simple offline viewer over recorded session data."""

    def __init__(self, session_path: Union[str, Path]) -> None:
        if QApplication is None or pg is None:
            raise RuntimeError("PySide6 and pyqtgraph are required for the offline viewer")
        super().__init__()
        self._session_path = Path(session_path)
        self._reader = SessionReader(self._session_path)
        self._export_service = ExportService(self._reader)
        self._manifest = self._reader.read_manifest()
        self._channels = self._reader.read_channels()
        self._frame = self._reader.read_samples()
        self._channel_lookup: Dict[str, int] = {channel.name: channel.channel_id for channel in self._channels}

        self.setWindowTitle("PLC Telemetry Viewer - {session}".format(session=self._manifest.session_id))
        self.resize(1400, 900)
        self._build_ui()
        self._populate_channels()
        self._populate_bool_table()
        self._refresh_plot()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        header = QLabel(
            "Session: {session}\nProject: {project}\nStatus: {status}".format(
                session=self._manifest.session_id,
                project=self._manifest.project_name,
                status=self._manifest.status.value,
            )
        )
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Channels"))
        self._channel_list = QListWidget()
        self._channel_list.setSelectionMode(QListWidget.ExtendedSelection)
        self._channel_list.itemSelectionChanged.connect(self._refresh_plot)
        left_layout.addWidget(self._channel_list)

        button_row = QHBoxLayout()
        csv_button = QPushButton("Export CSV")
        csv_button.clicked.connect(self._export_csv)
        png_button = QPushButton("Export PNG")
        png_button.clicked.connect(self._export_png)
        button_row.addWidget(csv_button)
        button_row.addWidget(png_button)
        left_layout.addLayout(button_row)

        left_layout.addWidget(QLabel("Boolean Channels"))
        self._bool_table = QTableWidget(0, 3)
        self._bool_table.setHorizontalHeaderLabels(["Channel", "Last Value", "Quality"])
        left_layout.addWidget(self._bool_table)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=True, y=True)
        self._plot.addLegend()
        right_layout.addWidget(self._plot)
        splitter.addWidget(right_panel)

        splitter.setSizes([320, 980])
        layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    def _populate_channels(self) -> None:
        for channel in self._channels:
            item = QListWidgetItem(channel.name)
            item.setToolTip(channel.path)
            self._channel_list.addItem(item)

    def _populate_bool_table(self) -> None:
        bool_channels = [channel for channel in self._channels if channel.value_type.is_boolean]
        self._bool_table.setRowCount(len(bool_channels))
        for index, channel in enumerate(bool_channels):
            channel_frame = self._frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
            last_value = ""
            last_quality = ""
            if channel_frame.height:
                last_value = str(channel_frame["value_bool"][-1])
                last_quality = str(channel_frame["quality"][-1])
            self._bool_table.setItem(index, 0, QTableWidgetItem(channel.name))
            self._bool_table.setItem(index, 1, QTableWidgetItem(last_value))
            self._bool_table.setItem(index, 2, QTableWidgetItem(last_quality))

    def _selected_channels(self) -> List[str]:
        selected_items = self._channel_list.selectedItems()
        if not selected_items:
            return [self._channel_list.item(index).text() for index in range(min(3, self._channel_list.count()))]
        return [item.text() for item in selected_items]

    def _refresh_plot(self) -> None:
        self._plot.clear()
        selected_names = self._selected_channels()
        numeric_channels = [
            channel for channel in self._channels
            if channel.name in selected_names and channel.value_type.is_numeric
        ]

        if not numeric_channels:
            return

        colors = ["#0b7285", "#c92a2a", "#2b8a3e", "#5f3dc4", "#e67700"]
        for index, channel in enumerate(numeric_channels):
            channel_frame = self._frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
            if channel_frame.height == 0:
                continue
            self._plot.plot(
                channel_frame["pc_timestamp_ns"].to_list(),
                channel_frame["value_numeric"].to_list(),
                pen=pg.mkPen(colors[index % len(colors)], width=2),
                name=channel.name,
            )

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", str(self._session_path / "export.csv"), "CSV Files (*.csv)")
        if not path:
            return
        self._export_service.export_csv(path, channels=self._selected_channels())
        QMessageBox.information(self, "Export complete", "CSV exported to {path}".format(path=path))

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", str(self._session_path / "export.png"), "PNG Files (*.png)")
        if not path:
            return
        self._export_service.export_png(path, channels=self._selected_channels())
        QMessageBox.information(self, "Export complete", "PNG exported to {path}".format(path=path))


def launch_viewer(session_path: Union[str, Path]) -> None:
    """Launch the offline viewer."""

    if QApplication is None:  # pragma: no cover - depends on GUI installation
        raise RuntimeError("PySide6 is required for the offline viewer")

    app = QApplication.instance() or QApplication([])
    window = OfflineViewerWindow(session_path)
    window.show()
    app.exec()
