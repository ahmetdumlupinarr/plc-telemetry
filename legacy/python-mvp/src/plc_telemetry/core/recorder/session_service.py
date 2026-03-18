"""Session creation and discovery services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Union

from plc_telemetry.core.config.loader import AppConfig
from plc_telemetry.core.models.enums import SessionStatus
from plc_telemetry.core.models.session_manifest import SessionManifest
from plc_telemetry.core.models.signal_definition import SignalDefinition
from plc_telemetry.core.storage.session_reader import SessionReader
from plc_telemetry.core.storage.session_writer import SessionWriter
from plc_telemetry.utils.session_paths import build_session_id, ensure_directory, utc_now
from plc_telemetry.version import __version__


@dataclass(frozen=True)
class PreparedSession:
    manifest: SessionManifest
    writer: SessionWriter
    session_path: Path


class SessionService:
    """Creates and loads session artifacts."""

    def __init__(self, config: AppConfig, schema_version: int = 1) -> None:
        self._config = config
        self._schema_version = schema_version

    @property
    def storage_root(self) -> Path:
        return ensure_directory(self._config.project.storage_root)

    def create_session(self, channels: Iterable[SignalDefinition]) -> PreparedSession:
        channel_list = [channel for channel in channels if channel.enabled]
        session_id = build_session_id(self._config.session.name_prefix)
        session_path = ensure_directory(self.storage_root / session_id)
        manifest = SessionManifest(
            session_id=session_id,
            project_name=self._config.project.name,
            transport=self._config.transport.type,
            schema_version=self._schema_version,
            app_version=__version__,
            start_time=utc_now(),
            end_time=None,
            channel_count=len(channel_list),
            logged_channels=[channel.channel_id for channel in channel_list],
            notes=self._config.session.manifest_notes,
            status=SessionStatus.RUNNING,
            storage_path=str(session_path),
            description=self._config.project.description,
        )
        writer = SessionWriter(session_path)
        writer.write_metadata(manifest, channel_list)
        return PreparedSession(manifest=manifest, writer=writer, session_path=session_path)

    def list_sessions(self) -> List[Path]:
        if not self.storage_root.exists():
            return []
        return sorted(
            [path for path in self.storage_root.iterdir() if path.is_dir()],
            reverse=True,
        )

    def load_session(self, session_path: Union[str, Path]) -> SessionReader:
        return SessionReader(session_path)
