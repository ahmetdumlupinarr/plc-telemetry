"""Export services for recorded sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl

from plc_telemetry.core.models.signal_definition import SignalDefinition
from plc_telemetry.core.storage.session_reader import SessionReader


class ExportService:
    """Exports recorded session data to CSV and PNG."""

    _PLOT_COLORS = ["#16c6d8", "#ff6b6b", "#8ce99a", "#ffd166", "#74c0fc"]

    def __init__(self, reader: SessionReader) -> None:
        self._reader = reader

    def export_csv(
        self,
        output_path: Union[str, Path],
        channels: Optional[Sequence[str]] = None,
    ) -> Path:
        frame = self._load_frame(channels)
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.write_csv(destination)
        return destination

    def export_png(
        self,
        output_path: Union[str, Path],
        channels: Optional[Sequence[str]] = None,
    ) -> Path:
        manifest = self._reader.read_manifest()
        channel_defs = self._reader.read_channels()
        frame = self._load_frame(channels)

        selected_channels = self._resolve_channels(channel_defs, channels)
        numeric_channels = [channel for channel in selected_channels if channel.value_type.is_numeric]
        bool_channels = [channel for channel in selected_channels if channel.value_type.is_boolean]

        figure, axes = plt.subplots(
            2 if bool_channels else 1,
            1,
            figsize=(12, 8),
            squeeze=False,
            facecolor="#0b1117",
        )
        plot_axis = axes[0][0]
        self._style_axis(plot_axis)
        numeric_frames = [
            (
                channel,
                frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns"),
            )
            for channel in numeric_channels
        ]
        plotted_numeric_frames = [(channel, channel_frame) for channel, channel_frame in numeric_frames if channel_frame.height]
        numeric_baseline = self._first_timestamp(plotted_numeric_frames)

        for index, (channel, channel_frame) in enumerate(plotted_numeric_frames):
            relative_seconds = self._relative_seconds(channel_frame, numeric_baseline)
            plot_axis.plot(
                relative_seconds,
                channel_frame["value_numeric"].to_list(),
                label=channel.name,
                linewidth=2,
                color=self._PLOT_COLORS[index % len(self._PLOT_COLORS)],
            )
        plot_axis.set_title("{name} numeric channels".format(name=manifest.session_id), color="#e6edf5")
        plot_axis.set_xlabel("Time (s)", color="#9db0c4")
        plot_axis.set_ylabel("Value", color="#9db0c4")
        if plotted_numeric_frames:
            plot_axis.legend(
                facecolor="#111821",
                edgecolor="#233241",
                labelcolor="#e6edf5",
                framealpha=0.95,
            )

        if bool_channels:
            bool_axis = axes[1][0]
            self._style_axis(bool_axis)
            bool_frames = [
                (
                    channel,
                    frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns"),
                )
                for channel in bool_channels
            ]
            plotted_bool_frames = [(channel, channel_frame) for channel, channel_frame in bool_frames if channel_frame.height]
            bool_baseline = self._first_timestamp(plotted_bool_frames)

            for index, (channel, channel_frame) in enumerate(plotted_bool_frames):
                values = [1 if item else 0 for item in channel_frame["value_bool"].to_list()]
                bool_axis.step(
                    self._relative_seconds(channel_frame, bool_baseline),
                    [value + index * 1.2 for value in values],
                    where="post",
                    label=channel.name,
                    linewidth=2,
                    color=self._PLOT_COLORS[index % len(self._PLOT_COLORS)],
                )
            bool_axis.set_title("Discrete channels", color="#e6edf5")
            bool_axis.set_xlabel("Time (s)", color="#9db0c4")
            bool_axis.set_ylabel("State", color="#9db0c4")
            bool_axis.set_yticks([])
            if plotted_bool_frames:
                bool_axis.legend(
                    facecolor="#111821",
                    edgecolor="#233241",
                    labelcolor="#e6edf5",
                    framealpha=0.95,
                )

        figure.tight_layout()
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            destination,
            facecolor=figure.get_facecolor(),
            edgecolor="none",
            dpi=160,
        )
        plt.close(figure)
        return destination

    def _style_axis(self, axis: object) -> None:
        axis.set_facecolor("#0c1218")
        axis.grid(True, color="#1d2a36", alpha=0.35, linewidth=0.6)
        axis.tick_params(colors="#9db0c4")
        for spine in axis.spines.values():
            spine.set_color("#2d3d4d")

    def _relative_seconds(self, channel_frame: pl.DataFrame, baseline: Optional[int]) -> List[float]:
        if baseline is None:
            return []
        return [
            (int(timestamp) - baseline) / 1_000_000_000
            for timestamp in channel_frame["pc_timestamp_ns"].to_list()
        ]

    def _first_timestamp(self, frames: Sequence[tuple[SignalDefinition, pl.DataFrame]]) -> Optional[int]:
        if not frames:
            return None
        return min(int(frame["pc_timestamp_ns"][0]) for _, frame in frames if frame.height)

    def _load_frame(self, channels: Optional[Sequence[str]]) -> pl.DataFrame:
        all_channels = self._reader.read_channels()
        selected = self._resolve_channels(all_channels, channels)
        frame = self._reader.read_samples()
        if channels is None:
            return frame
        if not selected:
            return frame.head(0)
        selected_ids = [channel.channel_id for channel in selected]
        return frame.filter(pl.col("channel_id").is_in(selected_ids))

    def _resolve_channels(
        self,
        channels: Iterable[SignalDefinition],
        requested: Optional[Sequence[str]],
    ) -> List[SignalDefinition]:
        channel_list = list(channels)
        if not requested:
            return channel_list
        requested_set = {item.strip() for item in requested if item.strip()}
        return [channel for channel in channel_list if channel.name in requested_set]
