from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_plc_telemetry_script_forwards_full_command(sample_session: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "run_plc_telemetry.py", "sessions", "show", str(sample_session)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["session_id"] == sample_session.name


def test_run_sessions_script_prepends_sessions_command(sample_session: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "run_sessions.py", "show", str(sample_session)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["session_id"] == sample_session.name
