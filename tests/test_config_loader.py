from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from plc_telemetry.core.config.loader import load_config


def test_load_config_resolves_storage_root(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    payload = {
        "project": {
            "name": "demo",
            "description": "demo",
            "storage_root": "./sessions",
        },
        "transport": {
            "type": "ads",
            "ads": {
                "ams_net_id": "127.0.0.1.1.1",
                "port": 851,
                "poll_interval_ms": 10,
            },
        },
        "session": {
            "name_prefix": "demo",
            "auto_start": False,
            "manifest_notes": "note",
        },
        "channels": [
            {
                "channel_id": 1,
                "name": "ActPos",
                "path": "GVL.ActPos",
                "value_type": "lreal",
                "unit": "deg",
                "group": "motion",
                "description": "Actual position",
                "display_hint": "plot",
                "sample_mode": "cyclic",
                "sample_interval_ms": 10,
                "enabled": True,
            }
        ],
    }
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    config = load_config(config_path)

    assert config.project.storage_root == (tmp_path / "sessions").resolve()
    assert config.channels[0].name == "ActPos"


def test_load_config_rejects_non_cyclic_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    payload = {
        "project": {"name": "demo", "storage_root": "./sessions"},
        "transport": {
            "type": "ads",
            "ads": {"ams_net_id": "127.0.0.1.1.1", "port": 851, "poll_interval_ms": 10},
        },
        "session": {"name_prefix": "demo", "auto_start": False},
        "channels": [
            {
                "channel_id": 1,
                "name": "ActPos",
                "path": "GVL.ActPos",
                "value_type": "lreal",
                "display_hint": "plot",
                "sample_mode": "on_change",
                "enabled": True,
            }
        ],
    }
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="only cyclic"):
        load_config(config_path)
