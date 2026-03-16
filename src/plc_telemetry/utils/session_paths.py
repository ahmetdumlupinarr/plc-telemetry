"""Session path helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "session"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_session_id(prefix: str, timestamp: Optional[datetime] = None) -> str:
    stamp = (timestamp or utc_now()).astimezone(timezone.utc)
    return "{date}_{name}".format(
        date=stamp.strftime("%Y-%m-%d_%H-%M-%S"),
        name=slugify(prefix),
    )


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
