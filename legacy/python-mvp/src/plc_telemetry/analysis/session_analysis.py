"""Analysis helpers for recorded sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import polars as pl

from plc_telemetry.core.models.signal_definition import SignalDefinition


@dataclass(frozen=True)
class ChannelSummary:
    name: str
    row_count: int
    min_numeric: Optional[float]
    max_numeric: Optional[float]
    last_quality: str


def summarize_channels(frame: pl.DataFrame, channels: List[SignalDefinition]) -> List[ChannelSummary]:
    summaries: List[ChannelSummary] = []
    for channel in channels:
        channel_frame = frame.filter(pl.col("channel_id") == channel.channel_id).sort("pc_timestamp_ns")
        if channel_frame.height == 0:
            summaries.append(
                ChannelSummary(
                    name=channel.name,
                    row_count=0,
                    min_numeric=None,
                    max_numeric=None,
                    last_quality="n/a",
                )
            )
            continue
        numeric = channel_frame["value_numeric"].drop_nulls()
        summaries.append(
            ChannelSummary(
                name=channel.name,
                row_count=channel_frame.height,
                min_numeric=float(numeric.min()) if len(numeric) else None,
                max_numeric=float(numeric.max()) if len(numeric) else None,
                last_quality=str(channel_frame["quality"][-1]),
            )
        )
    return summaries
