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

        figure, axes = plt.subplots(2 if bool_channels else 1, 1, figsize=(12, 8), squeeze=False)
        plot_axis = axes[0][0]
        for channel in numeric_channels:
            channel_frame = frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
            if channel_frame.height == 0:
                continue
            plot_axis.plot(
                channel_frame["pc_timestamp_ns"].to_list(),
                channel_frame["value_numeric"].to_list(),
                label=channel.name,
            )
        plot_axis.set_title("{name} numeric channels".format(name=manifest.session_id))
        plot_axis.set_xlabel("pc_timestamp_ns")
        plot_axis.set_ylabel("value_numeric")
        if numeric_channels:
            plot_axis.legend()

        if bool_channels:
            bool_axis = axes[1][0]
            for index, channel in enumerate(bool_channels):
                channel_frame = frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
                if channel_frame.height == 0:
                    continue
                values = [1 if item else 0 for item in channel_frame["value_bool"].to_list()]
                bool_axis.step(
                    channel_frame["pc_timestamp_ns"].to_list(),
                    [value + index * 1.2 for value in values],
                    where="post",
                    label=channel.name,
                )
            bool_axis.set_title("Boolean channels")
            bool_axis.set_xlabel("pc_timestamp_ns")
            bool_axis.set_yticks([])
            bool_axis.legend()

        figure.tight_layout()
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination)
        plt.close(figure)
        return destination

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
