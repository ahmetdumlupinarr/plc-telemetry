"""Offline viewer application."""

from __future__ import annotations

from bisect import bisect_left
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import polars as pl

from plc_telemetry.core.storage.exporters import ExportService
from plc_telemetry.core.storage.session_reader import SessionReader

try:  # pragma: no cover - import depends on GUI availability
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
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
    import pyqtgraph as pg
except ImportError:  # pragma: no cover - exercised manually
    QAbstractItemView = None
    QApplication = None
    QFileDialog = None
    QFrame = None
    QGridLayout = None
    QHBoxLayout = None
    QHeaderView = None
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
    QSize = None
    pg = None


class OfflineViewerWindow(QMainWindow):
    """Offline viewer over recorded session data."""

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
        self._grid_enabled = True
        self._legend_enabled = True
        self._box_zoom_enabled = True
        self._x_locked = False
        self._y_locked = False
        self._measure_mode_enabled = False
        self._measurement_points: List[Tuple[float, float]] = []
        self._plotted_series: List[Tuple[str, List[float], List[float]]] = []

        self.setWindowTitle("PLC Telemetry Viewer - {session}".format(session=self._manifest.session_id))
        self.resize(1400, 900)
        self._apply_theme()
        self._build_ui()
        self._populate_channels()
        self._populate_bool_table()
        self._refresh_plot()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        layout.addWidget(self._build_top_bar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_plot_panel())
        splitter.setSizes([360, 1240])
        layout.addWidget(splitter, 1)

        self.setCentralWidget(central_widget)

    def _build_top_bar(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("topBar")

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        self._session_title_label = QLabel(self._manifest.session_id)
        self._session_title_label.setObjectName("sessionTitle")
        title_block.addWidget(self._session_title_label)

        self._session_subtitle_label = QLabel(
            "{project} / {transport} / {duration}".format(
                project=self._manifest.project_name,
                transport=self._manifest.transport.value.upper(),
                duration=self._format_duration(self._manifest.start_time, self._manifest.end_time),
            )
        )
        self._session_subtitle_label.setObjectName("sessionSubtitle")
        title_block.addWidget(self._session_subtitle_label)

        layout.addLayout(title_block, 1)

        self._status_badge = QLabel(self._manifest.status.value.upper())
        self._status_badge.setObjectName("statusBadge")
        self._status_badge.setProperty("status", self._manifest.status.value.lower())
        layout.addWidget(self._status_badge, 0, Qt.AlignVCenter | Qt.AlignRight)
        return panel

    def _build_sidebar(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sidePanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        channel_header = QHBoxLayout()
        channel_header.setSpacing(8)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self._channel_panel_title = QLabel("Channels")
        self._channel_panel_title.setObjectName("panelTitle")
        self._channel_panel_subtitle = QLabel("Ready")
        self._channel_panel_subtitle.setObjectName("panelSubtitle")
        title_block.addWidget(self._channel_panel_title)
        title_block.addWidget(self._channel_panel_subtitle)
        channel_header.addLayout(title_block, 1)

        all_button = QPushButton("All")
        all_button.setObjectName("tinyButton")
        all_button.clicked.connect(self._select_all_channels)
        numeric_button = QPushButton("Numeric")
        numeric_button.setObjectName("tinyButton")
        numeric_button.clicked.connect(self._select_numeric_channels)
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("tinyButton")
        clear_button.clicked.connect(self._clear_channel_selection)
        channel_header.addWidget(all_button)
        channel_header.addWidget(numeric_button)
        channel_header.addWidget(clear_button)
        layout.addLayout(channel_header)

        self._channel_list = QListWidget()
        self._channel_list.setSelectionMode(QListWidget.ExtendedSelection)
        self._channel_list.setUniformItemSizes(True)
        self._channel_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._channel_list.itemSelectionChanged.connect(self._refresh_plot)
        layout.addWidget(self._channel_list, 1)

        export_row = QHBoxLayout()
        export_row.setSpacing(8)
        csv_button = QPushButton("Export CSV")
        csv_button.setObjectName("secondaryButton")
        csv_button.clicked.connect(self._export_csv)
        png_button = QPushButton("Export PNG")
        png_button.setObjectName("secondaryButton")
        png_button.clicked.connect(self._export_png)
        export_row.addWidget(csv_button)
        export_row.addWidget(png_button)
        layout.addLayout(export_row)

        bool_title = QLabel("Discrete States")
        bool_title.setObjectName("panelTitle")
        layout.addWidget(bool_title)

        self._bool_table = QTableWidget(0, 3)
        self._bool_table.setHorizontalHeaderLabels(["Channel", "State", "Read Quality"])
        self._bool_table.verticalHeader().setVisible(False)
        self._bool_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._bool_table.horizontalHeader().setFixedHeight(32)
        self._bool_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bool_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._bool_table.setFocusPolicy(Qt.NoFocus)
        self._bool_table.setShowGrid(False)
        layout.addWidget(self._bool_table, 0)

        layout.addWidget(self._build_info_panel(), 0)
        return panel

    def _build_info_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("infoPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Session Info")
        title.setObjectName("infoPanelTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        for index, (label, value) in enumerate(self._info_metrics()):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)

            key_label = QLabel(label)
            key_label.setObjectName("infoKey")
            cell_layout.addWidget(key_label)

            value_label = QLabel(value)
            value_label.setObjectName("infoValue")
            value_label.setWordWrap(True)
            cell_layout.addWidget(value_label)

            grid.addWidget(cell, index // 2, index % 2)

        layout.addLayout(grid)
        return panel

    def _build_plot_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("plotPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self._plot_panel_title = QLabel("Numeric Plot")
        self._plot_panel_title.setObjectName("panelTitle")
        self._plot_panel_subtitle = QLabel("Relative timeline view for selected numeric channels.")
        self._plot_panel_subtitle.setObjectName("panelSubtitle")
        title_block.addWidget(self._plot_panel_title)
        title_block.addWidget(self._plot_panel_subtitle)
        header_row.addLayout(title_block, 1)

        reset_button = QPushButton("Reset")
        reset_button.setObjectName("tinyButton")
        reset_button.clicked.connect(self._reset_plot_view)
        self._zoom_mode_button = QPushButton("Box Zoom")
        self._zoom_mode_button.setObjectName("tinyButton")
        self._zoom_mode_button.setCheckable(True)
        self._zoom_mode_button.setChecked(True)
        self._zoom_mode_button.toggled.connect(self._toggle_box_zoom)
        self._lock_x_button = QPushButton("Lock X")
        self._lock_x_button.setObjectName("tinyButton")
        self._lock_x_button.setCheckable(True)
        self._lock_x_button.toggled.connect(self._toggle_x_lock)
        self._lock_y_button = QPushButton("Lock Y")
        self._lock_y_button.setObjectName("tinyButton")
        self._lock_y_button.setCheckable(True)
        self._lock_y_button.toggled.connect(self._toggle_y_lock)
        self._grid_button = QPushButton("Grid")
        self._grid_button.setObjectName("tinyButton")
        self._grid_button.setCheckable(True)
        self._grid_button.setChecked(True)
        self._grid_button.toggled.connect(self._toggle_grid)
        self._legend_button = QPushButton("Legend")
        self._legend_button.setObjectName("tinyButton")
        self._legend_button.setCheckable(True)
        self._legend_button.setChecked(True)
        self._legend_button.toggled.connect(self._toggle_legend)
        self._measure_button = QPushButton("Measure")
        self._measure_button.setObjectName("tinyButton")
        self._measure_button.setCheckable(True)
        self._measure_button.toggled.connect(self._toggle_measure_mode)
        header_row.addWidget(reset_button)
        header_row.addWidget(self._zoom_mode_button)
        header_row.addWidget(self._lock_x_button)
        header_row.addWidget(self._lock_y_button)
        header_row.addWidget(self._grid_button)
        header_row.addWidget(self._legend_button)
        header_row.addWidget(self._measure_button)
        layout.addLayout(header_row)

        readout_row = QHBoxLayout()
        readout_row.setSpacing(12)
        self._cursor_label = QLabel("Cursor: -")
        self._cursor_label.setObjectName("plotReadout")
        self._delta_label = QLabel("Delta: off")
        self._delta_label.setObjectName("plotReadout")
        readout_row.addWidget(self._cursor_label)
        readout_row.addWidget(self._delta_label)
        readout_row.addStretch(1)
        layout.addLayout(readout_row)

        self._plot = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot, 1)
        return panel

    def _info_metrics(self) -> List[Tuple[str, str]]:
        sample_count = int(self._manifest.stats.get("sample_count", self._frame.height))
        return [
            ("Project", self._manifest.project_name),
            ("Transport", self._manifest.transport.value.upper()),
            ("Started", self._format_timestamp(self._manifest.start_time)),
            ("Duration", self._format_duration(self._manifest.start_time, self._manifest.end_time)),
            ("Samples", "{count:,}".format(count=sample_count)),
            ("Storage", self._session_path.name),
        ]

    def _configure_plot(self) -> None:
        self._plot.setBackground("#0c1218")
        plot_item = self._plot.getPlotItem()
        plot_item.showGrid(x=self._grid_enabled, y=self._grid_enabled, alpha=0.18 if self._grid_enabled else 0.0)
        plot_item.setLabel("bottom", "Time", units="s")
        plot_item.setLabel("left", "Value")
        plot_item.getAxis("bottom").setTextPen(pg.mkColor("#9db0c4"))
        plot_item.getAxis("bottom").setPen(pg.mkPen("#2d3d4d"))
        plot_item.getAxis("left").setTextPen(pg.mkColor("#9db0c4"))
        plot_item.getAxis("left").setPen(pg.mkPen("#2d3d4d"))
        plot_item.hideButtons()
        plot_item.setMenuEnabled(True)
        if self._legend_enabled and plot_item.legend is None:
            plot_item.addLegend(offset=(12, 10))
        plot_item.vb.setMouseMode(pg.ViewBox.RectMode if self._box_zoom_enabled else pg.ViewBox.PanMode)
        plot_item.vb.setMouseEnabled(x=not self._x_locked, y=not self._y_locked)

        self._crosshair_vertical = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#456173", width=1))
        self._crosshair_horizontal = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#456173", width=1))
        self._measure_scatter = pg.ScatterPlotItem(size=9, brush=pg.mkBrush("#ffd166"), pen=pg.mkPen("#ffe29a", width=1.2))
        self._ensure_plot_overlays()
        self._mouse_move_proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_plot_mouse_moved,
        )
        self._plot.scene().sigMouseClicked.connect(self._on_plot_mouse_clicked)

    def _populate_channels(self) -> None:
        default_numeric_names = [
            channel.name for channel in self._channels if channel.value_type.is_numeric
        ][:3]
        selected_names = set(default_numeric_names)
        row_height = self._channel_row_height()

        self._channel_list.blockSignals(True)
        for channel in self._channels:
            item = QListWidgetItem(channel.name)
            item.setToolTip(channel.path)
            item.setSizeHint(QSize(0, row_height))
            self._channel_list.addItem(item)
            item.setSelected(channel.name in selected_names)
        self._channel_list.blockSignals(False)

    def _populate_bool_table(self) -> None:
        bool_channels = [channel for channel in self._channels if channel.value_type.is_boolean]
        self._bool_table.setRowCount(len(bool_channels))

        for index, channel in enumerate(bool_channels):
            channel_frame = self._frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
            last_value = "N/A"
            last_quality = "N/A"
            if channel_frame.height:
                last_value = "ON" if bool(channel_frame["value_bool"][-1]) else "OFF"
                last_quality = str(channel_frame["quality"][-1]).upper()

            name_item = QTableWidgetItem(channel.name)
            value_item = QTableWidgetItem(last_value)
            quality_item = QTableWidgetItem(last_quality)
            value_item.setTextAlignment(Qt.AlignCenter)
            quality_item.setTextAlignment(Qt.AlignCenter)

            self._bool_table.setItem(index, 0, name_item)
            self._bool_table.setItem(index, 1, value_item)
            self._bool_table.setItem(index, 2, quality_item)

        self._bool_table.resizeRowsToContents()
        self._update_bool_table_height()

    def _update_bool_table_height(self) -> None:
        row_count = self._bool_table.rowCount()
        header_height = self._bool_table.horizontalHeader().height()
        rows_height = sum(self._bool_table.rowHeight(index) for index in range(row_count))
        target_height = min(max(header_height + rows_height + 18, 78), 180)
        self._bool_table.setMinimumHeight(target_height)
        self._bool_table.setMaximumHeight(target_height)

    def _selected_channels(self) -> List[str]:
        return [item.text() for item in self._channel_list.selectedItems()]

    def _channel_row_height(self) -> int:
        channel_count = len(self._channels)
        if channel_count > 40:
            return 20
        if channel_count > 20:
            return 22
        return 26

    def _set_selected_channel_names(self, channel_names: List[str]) -> None:
        selected_names = set(channel_names)
        self._channel_list.blockSignals(True)
        for index in range(self._channel_list.count()):
            item = self._channel_list.item(index)
            item.setSelected(item.text() in selected_names)
        self._channel_list.blockSignals(False)
        self._refresh_plot()

    def _select_all_channels(self) -> None:
        self._set_selected_channel_names(
            [self._channel_list.item(index).text() for index in range(self._channel_list.count())]
        )

    def _select_numeric_channels(self) -> None:
        self._set_selected_channel_names([channel.name for channel in self._channels if channel.value_type.is_numeric])

    def _clear_channel_selection(self) -> None:
        self._set_selected_channel_names([])

    def _reset_plot_view(self) -> None:
        self._plot.getPlotItem().autoRange()

    def _toggle_box_zoom(self, enabled: bool) -> None:
        self._box_zoom_enabled = enabled
        self._plot.getPlotItem().vb.setMouseMode(pg.ViewBox.RectMode if enabled else pg.ViewBox.PanMode)

    def _toggle_x_lock(self, enabled: bool) -> None:
        self._x_locked = enabled
        self._plot.getPlotItem().vb.setMouseEnabled(x=not self._x_locked, y=not self._y_locked)

    def _toggle_y_lock(self, enabled: bool) -> None:
        self._y_locked = enabled
        self._plot.getPlotItem().vb.setMouseEnabled(x=not self._x_locked, y=not self._y_locked)

    def _toggle_grid(self, enabled: bool) -> None:
        self._grid_enabled = enabled
        self._plot.getPlotItem().showGrid(
            x=enabled,
            y=enabled,
            alpha=0.18 if enabled else 0.0,
        )

    def _toggle_legend(self, enabled: bool) -> None:
        self._legend_enabled = enabled
        self._refresh_plot()

    def _toggle_measure_mode(self, enabled: bool) -> None:
        self._measure_mode_enabled = enabled
        self._measurement_points = []
        self._update_measure_overlay()
        self._delta_label.setText("Delta: armed" if enabled else "Delta: off")

    def _refresh_plot(self) -> None:
        plot_item = self._plot.getPlotItem()
        plot_item.clear()
        if self._legend_enabled and plot_item.legend is None:
            plot_item.addLegend(offset=(12, 10))
        elif not self._legend_enabled and plot_item.legend is not None:
            plot_item.legend.scene().removeItem(plot_item.legend)
            plot_item.legend = None
        elif plot_item.legend is not None:
            plot_item.legend.clear()
        self._ensure_plot_overlays()

        selected_names = self._selected_channels()
        self._channel_panel_subtitle.setText(
            "{selected} selected / {total} total".format(
                selected=len(selected_names),
                total=self._channel_list.count(),
            )
        )
        self._plotted_series = []

        channel_frames = {
            channel.name: self._frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
            for channel in self._channels
            if channel.name in selected_names and channel.value_type.is_numeric
        }
        plotted_frames = [(name, frame) for name, frame in channel_frames.items() if frame.height]

        if not plotted_frames:
            self._plot_panel_subtitle.setText("No numeric channels selected.")
            return

        first_timestamp = min(int(frame["pc_timestamp_ns"][0]) for _, frame in plotted_frames)
        colors = ["#16c6d8", "#ff6b6b", "#8ce99a", "#ffd166", "#74c0fc"]

        for index, (channel_name, channel_frame) in enumerate(plotted_frames):
            relative_seconds = [
                (int(timestamp) - first_timestamp) / 1_000_000_000
                for timestamp in channel_frame["pc_timestamp_ns"].to_list()
            ]
            values = channel_frame["value_numeric"].to_list()
            plot_item.plot(
                relative_seconds,
                values,
                pen=pg.mkPen(colors[index % len(colors)], width=2),
                name=channel_name,
            )
            self._plotted_series.append((channel_name, relative_seconds, values))

        self._plot_panel_subtitle.setText(
            "{count} numeric channels selected / relative seconds".format(
                count=len(plotted_frames)
            )
        )
        self._update_measure_overlay()

    def _ensure_plot_overlays(self) -> None:
        plot_item = self._plot.getPlotItem()
        if self._crosshair_vertical.scene() is None:
            plot_item.addItem(self._crosshair_vertical, ignoreBounds=True)
        if self._crosshair_horizontal.scene() is None:
            plot_item.addItem(self._crosshair_horizontal, ignoreBounds=True)
        if self._measure_scatter.scene() is None:
            plot_item.addItem(self._measure_scatter)

    def _on_plot_mouse_moved(self, event: object) -> None:
        if not self._plotted_series:
            self._cursor_label.setText("Cursor: -")
            return

        scene_position = event[0]
        if not self._plot.sceneBoundingRect().contains(scene_position):
            self._cursor_label.setText("Cursor: -")
            return

        mouse_point = self._plot.getPlotItem().vb.mapSceneToView(scene_position)
        self._crosshair_vertical.setPos(mouse_point.x())
        self._crosshair_horizontal.setPos(mouse_point.y())

        nearest = self._nearest_plotted_point(mouse_point.x())
        if nearest is None:
            self._cursor_label.setText("Cursor: -")
            return

        channel_name, time_value, sample_value = nearest
        self._cursor_label.setText(
            "Cursor: {channel} / t={time_value:.3f}s / y={sample_value:.3f}".format(
                channel=channel_name,
                time_value=time_value,
                sample_value=sample_value,
            )
        )

    def _on_plot_mouse_clicked(self, event: object) -> None:
        if not self._measure_mode_enabled or event.button() != Qt.LeftButton:
            return
        if not self._plot.sceneBoundingRect().contains(event.scenePos()):
            return

        mouse_point = self._plot.getPlotItem().vb.mapSceneToView(event.scenePos())
        nearest = self._nearest_plotted_point(mouse_point.x())
        if nearest is None:
            return

        _, time_value, sample_value = nearest
        if len(self._measurement_points) == 2:
            self._measurement_points.pop(0)
        self._measurement_points.append((time_value, sample_value))
        self._update_measure_overlay()

        if len(self._measurement_points) == 1:
            self._delta_label.setText(
                "Delta: start t={time_value:.3f}s / y={sample_value:.3f}".format(
                    time_value=time_value,
                    sample_value=sample_value,
                )
            )
            return

        start_time, start_value = self._measurement_points[0]
        end_time, end_value = self._measurement_points[1]
        self._delta_label.setText(
            "Delta: dt={delta_time:.3f}s / dy={delta_value:.3f}".format(
                delta_time=end_time - start_time,
                delta_value=end_value - start_value,
            )
        )

    def _update_measure_overlay(self) -> None:
        if not self._measurement_points:
            self._measure_scatter.setData([], [])
            return

        self._measure_scatter.setData(
            [point[0] for point in self._measurement_points],
            [point[1] for point in self._measurement_points],
        )

    def _nearest_plotted_point(self, target_x: float) -> Optional[Tuple[str, float, float]]:
        best_match: Optional[Tuple[str, float, float]] = None
        best_distance: Optional[float] = None

        for channel_name, x_values, y_values in self._plotted_series:
            if not x_values:
                continue
            candidate_index = bisect_left(x_values, target_x)
            candidate_indexes = {max(candidate_index - 1, 0), min(candidate_index, len(x_values) - 1)}
            for index in candidate_indexes:
                candidate_distance = abs(x_values[index] - target_x)
                if best_distance is None or candidate_distance < best_distance:
                    best_distance = candidate_distance
                    best_match = (channel_name, x_values[index], y_values[index])

        return best_match

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

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0b1117;
            }
            QWidget {
                color: #e6edf5;
                font-size: 12px;
            }
            QFrame#topBar,
            QFrame#sidePanel,
            QFrame#plotPanel,
            QFrame#infoPanel {
                background-color: #111821;
                border: 1px solid #1f2c38;
                border-radius: 16px;
            }
            QLabel#sessionTitle {
                color: #f7fbff;
                font-size: 19px;
                font-weight: 700;
            }
            QLabel#sessionSubtitle,
            QLabel#panelSubtitle,
            QLabel#plotReadout {
                color: #8c9dad;
                font-size: 11px;
            }
            QLabel#statusBadge {
                padding: 6px 12px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#statusBadge[status="completed"] {
                background-color: rgba(68, 190, 162, 0.18);
                color: #8ff3d2;
                border: 1px solid rgba(68, 190, 162, 0.45);
            }
            QLabel#statusBadge[status="running"] {
                background-color: rgba(255, 209, 102, 0.16);
                color: #ffe08a;
                border: 1px solid rgba(255, 209, 102, 0.42);
            }
            QLabel#statusBadge[status="failed"],
            QLabel#statusBadge[status="aborted"] {
                background-color: rgba(255, 107, 107, 0.16);
                color: #ff9a9a;
                border: 1px solid rgba(255, 107, 107, 0.42);
            }
            QLabel#panelTitle,
            QLabel#infoPanelTitle {
                color: #f2f6fa;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#infoKey {
                color: #7f93a7;
                font-size: 10px;
                font-weight: 700;
            }
            QLabel#infoValue {
                color: #f2f6fa;
                font-size: 12px;
                font-weight: 600;
            }
            QListWidget {
                background-color: #0c131a;
                border: 1px solid #233241;
                border-radius: 14px;
                outline: none;
                padding: 6px;
            }
            QListWidget::item {
                border-radius: 8px;
                padding: 4px 8px;
                margin: 1px 0;
            }
            QListWidget::item:selected {
                background-color: #163342;
                border-left: 2px solid #16c6d8;
                color: #f7fbff;
            }
            QPushButton {
                background-color: #14202a;
                border: 1px solid #2a3948;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1a2732;
            }
            QPushButton#tinyButton {
                min-width: 56px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton#tinyButton:checked {
                background-color: #163342;
                border-color: #16c6d8;
                color: #f7fbff;
            }
            QPushButton#secondaryButton {
                color: #dbe6ef;
            }
            QTableWidget {
                background-color: #0c131a;
                border: 1px solid #233241;
                border-radius: 12px;
                padding: 4px;
                gridline-color: #233241;
            }
            QHeaderView::section {
                background-color: #111c25;
                color: #97aabc;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #233241;
                font-size: 11px;
                font-weight: 700;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #18232e;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #2b3c4d;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }
            QSplitter::handle {
                background-color: #0b1117;
            }
            """
        )

    @staticmethod
    def _format_timestamp(value: Optional[object]) -> str:
        if value is None:
            return "N/A"
        return value.strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def _format_duration(start_time: object, end_time: Optional[object]) -> str:
        if end_time is None:
            return "In progress"

        duration = end_time - start_time
        if isinstance(duration, timedelta):
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return "{hours}h {minutes}m {seconds}s".format(hours=hours, minutes=minutes, seconds=seconds)
            if minutes:
                return "{minutes}m {seconds}s".format(minutes=minutes, seconds=seconds)
            return "{seconds}s".format(seconds=seconds)
        return str(duration)


def launch_viewer(session_path: Union[str, Path]) -> None:
    """Launch the offline viewer."""

    if QApplication is None:  # pragma: no cover - depends on GUI installation
        raise RuntimeError("PySide6 is required for the offline viewer")

    app = QApplication.instance() or QApplication([])
    window = OfflineViewerWindow(session_path)
    window.show()
    app.exec()
