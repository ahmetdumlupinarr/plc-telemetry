"""YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import yaml

from plc_telemetry.core.models.enums import SampleMode, TransportType
from plc_telemetry.core.models.signal_definition import SignalDefinition


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    description: Optional[str]
    storage_root: Path


@dataclass(frozen=True)
class AdsConfig:
    ams_net_id: str
    port: int
    poll_interval_ms: int
    timeout_ms: int = 500


@dataclass(frozen=True)
class TransportConfig:
    type: TransportType
    ads: AdsConfig


@dataclass(frozen=True)
class SessionConfig:
    name_prefix: str
    auto_start: bool
    manifest_notes: Optional[str]


@dataclass(frozen=True)
class AppConfig:
    project: ProjectConfig
    transport: TransportConfig
    session: SessionConfig
    channels: List[SignalDefinition]


def load_config(config_path: Union[str, Path]) -> AppConfig:
    path = Path(config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    try:
        project_payload = payload["project"]
        transport_payload = payload["transport"]
        session_payload = payload["session"]
        channel_payloads = payload["channels"]
    except KeyError as exc:
        raise ValueError("config is missing required top-level sections") from exc

    transport_type = TransportType(str(transport_payload["type"]).lower())
    if transport_type is not TransportType.ADS:
        raise ValueError("v1.0 supports only ads transport")

    ads_payload = transport_payload.get("ads") or {}
    ads = AdsConfig(
        ams_net_id=str(ads_payload["ams_net_id"]),
        port=int(ads_payload["port"]),
        poll_interval_ms=int(ads_payload["poll_interval_ms"]),
        timeout_ms=int(ads_payload.get("timeout_ms", 500)),
    )
    if ads.poll_interval_ms <= 0:
        raise ValueError("poll_interval_ms must be > 0")
    if ads.timeout_ms <= 0:
        raise ValueError("timeout_ms must be > 0")

    channels = [SignalDefinition.from_dict(item) for item in channel_payloads]
    if not channels:
        raise ValueError("config must define at least one channel")

    duplicate_ids = {channel.channel_id for channel in channels if sum(item.channel_id == channel.channel_id for item in channels) > 1}
    if duplicate_ids:
        raise ValueError("channel_id values must be unique")

    for channel in channels:
        if channel.sample_mode is not SampleMode.CYCLIC:
            raise ValueError("v1.0 supports only cyclic sample_mode")

    project = ProjectConfig(
        name=str(project_payload["name"]),
        description=project_payload.get("description"),
        storage_root=(path.parent / str(project_payload.get("storage_root", "./sessions"))).resolve(),
    )
    session = SessionConfig(
        name_prefix=str(session_payload.get("name_prefix", "session")),
        auto_start=bool(session_payload.get("auto_start", False)),
        manifest_notes=session_payload.get("manifest_notes"),
    )

    return AppConfig(
        project=project,
        transport=TransportConfig(type=transport_type, ads=ads),
        session=session,
        channels=channels,
    )
