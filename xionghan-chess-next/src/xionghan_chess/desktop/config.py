from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def config_path() -> Path:
    root = Path(os.getenv("APPDATA", Path.home())) / "XionghanChess"
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


def data_dir() -> Path:
    """用户数据目录（settings.json / games / statistics.json 都在这里）。

    阶段1 S1-1：此前 app.py 里有 3 处写 `config_path().parent / "games"`，
    storage.py 里还有 3 处 —— 同一件事两种拼法。集中到此函数。
    """
    return config_path().parent


def games_dir() -> Path:
    """棋谱目录（导入/导出/自动保存的默认位置），保证存在。"""
    folder = data_dir() / "games"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


DEFAULT_SERVER_URL = "http://127.0.0.1:8000"

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
    # S1-1 修复：`server_url` 此前被 app.py 读 3 次、被 SettingsDialog.value()
    # 回填，却**不在 DEFAULTS 里** —— 首次运行完全依赖调用点的
    # `config.get("server_url", "http://127.0.0.1:8000")` 硬编码兜底。
    # 现声明为默认值，兜底字符串只在 DEFAULT_SERVER_URL 一处。
    "server_url": DEFAULT_SERVER_URL,
}

# S1-9：这些键改变「规则 / 对局结构」，改了就必然要重开一局。
# 其余键（主题 / 字体 / 语言 / 音量 / 翻转 / 辅助提示…）只是界面差异，应保留当前对局。
# 放在 config.py 而不是 MainWindow 里：它是**配置语义**，UI 与测试都应引用同一份。
GAME_BREAKING_KEYS: tuple[str, ...] = ("profile", "rule_options", "initial_minutes")


def settings_differ_in_game_breaking_keys(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """两次配置之间是否发生了「必须重开对局」的变更（S1-9 的判定，可单测）。"""
    return any(old.get(key) != new.get(key) for key in GAME_BREAKING_KEYS)


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def save_config(data: dict[str, Any]) -> None:
    config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
