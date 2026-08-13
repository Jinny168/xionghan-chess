from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def config_path() -> Path:
    root = Path(os.getenv("APPDATA", Path.home())) / "XionghanChess"
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


DEFAULTS: dict[str, Any] = {
    "profile": "desktop_complete",
    "language": "zh-CN",
    "game_mode": "ai",
    "difficulty": "medium",
    "human_color": "red",
    "sound": True,
    "music": False,
    "music_style": "fc",
    "sound_volume": 70,
    "music_volume": 40,
    "theme": "classic",
    "font": "system",
    "background": "none",
    "piece_style": "traditional",
    "flipped": False,
    "first_move": "red",
    "setup_slots": {},
    "account_token": "",
    "account_display_name": "",
    "account_avatar_url": "",
    "animations": True,
    "selection_highlight": True,
    "legal_targets": True,
    "capture_hints": True,
    "taunts": True,
    "countdown_seconds": 30,
    "autosave": True,
    "initial_minutes": 20,
    "rule_options": {},
}


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def save_config(data: dict[str, Any]) -> None:
    config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
