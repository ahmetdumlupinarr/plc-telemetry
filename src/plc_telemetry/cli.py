"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, Optional, Sequence

from plc_telemetry.analysis.session_analysis import summarize_channels
from plc_telemetry.core.config.loader import AppConfig, load_config
from plc_telemetry.core.recorder.recorder_service import RecorderService
from plc_telemetry.core.recorder.session_service import SessionService
from plc_telemetry.core.storage.exporters import ExportService
from plc_telemetry.core.storage.session_reader import SessionReader
from plc_telemetry.transports.ads.ads_adapter import AdsAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plc-telemetry")
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_parser = subparsers.add_parser("record", help="Record a telemetry session")
    record_parser.add_argument("--config", required=True)
    record_parser.add_argument("--max-batches", type=int, default=None)

    sessions_parser = subparsers.add_parser("sessions", help="Inspect stored sessions")
    sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_command", required=True)

    list_parser = sessions_subparsers.add_parser("list", help="List recorded sessions")
    list_parser.add_argument("--root", default="./sessions")

    show_parser = sessions_subparsers.add_parser("show", help="Show a recorded session")
    show_parser.add_argument("session_path")

    export_parser = subparsers.add_parser("export", help="Export recorded session artifacts")
    export_subparsers = export_parser.add_subparsers(dest="export_command", required=True)
    for name in ("csv", "png"):
        child = export_subparsers.add_parser(name, help="Export session as {name}".format(name=name.upper()))
        child.add_argument("session_path")
        child.add_argument("--output", default=None)
        child.add_argument("--channels", nargs="*", default=None)

    view_parser = subparsers.add_parser("view", help="Open the offline viewer")
    view_parser.add_argument("session_path")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.command == "record":
        return _record(args.config, max_batches=args.max_batches)
    if args.command == "sessions":
        if args.sessions_command == "list":
            return _list_sessions(args.root)
        return _show_session(args.session_path)
    if args.command == "export":
        return _export_session(
            export_type=args.export_command,
            session_path=args.session_path,
            output=args.output,
            channels=args.channels,
        )
    if args.command == "view":
        return _view_session(args.session_path)
    parser.error("unsupported command")
    return 2


def _record(config_path: str, max_batches: Optional[int]) -> int:
    config = load_config(config_path)
    session_service = SessionService(config)
    prepared = session_service.create_session(config.channels)
    recorder = RecorderService()
    transport = _build_transport(config)
    result = recorder.record(
        transport=transport,
        channels=config.channels,
        manifest=prepared.manifest,
        writer=prepared.writer,
        max_batches=max_batches,
    )
    print(json.dumps(result.manifest.to_dict(), indent=2))
    return 0


def _build_transport(config: AppConfig) -> AdsAdapter:
    return AdsAdapter(config.transport.ads)


def _list_sessions(root: str) -> int:
    root_path = Path(root)
    if not root_path.exists():
        print("No sessions directory found at {path}".format(path=root_path))
        return 0
    for path in sorted([item for item in root_path.iterdir() if item.is_dir()], reverse=True):
        print(path)
    return 0


def _show_session(session_path: str) -> int:
    reader = SessionReader(session_path)
    manifest = reader.read_manifest()
    channels = reader.read_channels()
    frame = reader.read_samples()
    summaries = summarize_channels(frame, channels)
    payload = manifest.to_dict()
    payload["channel_summaries"] = [summary.__dict__ for summary in summaries]
    print(json.dumps(payload, indent=2))
    return 0


def _export_session(
    export_type: str,
    session_path: str,
    output: Optional[str],
    channels: Optional[Iterable[str]],
) -> int:
    session_root = Path(session_path)
    destination = Path(output) if output else session_root / ("export.{ext}".format(ext=export_type))
    service = ExportService(SessionReader(session_root))
    if export_type == "csv":
        result = service.export_csv(destination, channels=channels)
    else:
        result = service.export_png(destination, channels=channels)
    print(result)
    return 0


def _view_session(session_path: str) -> int:
    from plc_telemetry.gui.app import launch_viewer

    launch_viewer(session_path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
