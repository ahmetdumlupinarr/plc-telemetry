from __future__ import annotations

import json
from pathlib import Path

from plc_telemetry.cli import main


def test_cli_sessions_show(sample_session: Path, capsys) -> None:
    exit_code = main(["sessions", "show", str(sample_session)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["session_id"] == sample_session.name
    assert payload["channel_summaries"][0]["name"] == "ActPos"
