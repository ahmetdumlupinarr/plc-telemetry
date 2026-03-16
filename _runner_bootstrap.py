"""Helpers for repository-root runner scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

_SKIP_REEXEC_ENV = "PLC_TELEMETRY_SKIP_VENV_REEXEC"


def project_root() -> Path:
    return Path(__file__).resolve().parent


def find_venv_python(root: Optional[Path] = None) -> Optional[Path]:
    base = root or project_root()
    candidates = [
        base / ".venv" / "Scripts" / "python.exe",
        base / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def ensure_src_on_path(root: Optional[Path] = None) -> None:
    src_path = str((root or project_root()) / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def maybe_reexec_into_venv() -> Optional[int]:
    if os.environ.get(_SKIP_REEXEC_ENV) == "1":
        return None

    venv_python = find_venv_python()
    if venv_python is None:
        return None

    try:
        current_python = Path(sys.executable).resolve()
        if current_python == venv_python.resolve():
            return None
    except OSError:
        pass

    env = os.environ.copy()
    env[_SKIP_REEXEC_ENV] = "1"
    command = [str(venv_python), *sys.argv]
    return subprocess.run(command, env=env, check=False).returncode


def run_cli(default_args: Optional[Sequence[str]] = None) -> int:
    reexec_exit_code = maybe_reexec_into_venv()
    if reexec_exit_code is not None:
        return reexec_exit_code

    ensure_src_on_path()

    from plc_telemetry.cli import main

    argv = [*(default_args or ()), *sys.argv[1:]]
    return main(argv)
