from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


def config_root(platform: str | None = None,
                environ: Mapping[str, str] | None = None) -> Path:
    """各平台的用户配置目录（P1-F）。

    此前只有 Windows 的 `%APPDATA%` 约定，macOS/Linux 会退化成
    `~/XionghanChess` —— 既不符合平台规范，也和系统备份/清理工具对不上。

    三个平台各自的惯例：
      Windows  `%APPDATA%\\XionghanChess`
      macOS    `~/Library/Application Support/XionghanChess`
      Linux    `$XDG_CONFIG_HOME/xionghan-chess`（缺省 `~/.config/...`）

    参数可注入是有意的：这样路径规则能用普通单测覆盖，不必真的切换到某个系统。
    Windows 分支保持**逐字节不变** —— 已有用户的配置/棋谱目录不能因为这次改动搬家。
    """
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = environ.get("HOME") or str(Path.home())
    if platform.startswith("win"):
        return Path(environ.get("APPDATA") or home) / "XionghanChess"
    if platform == "darwin":
        return Path(home) / "Library" / "Application Support" / "XionghanChess"
    base = environ.get("XDG_CONFIG_HOME") or str(Path(home) / ".config")
    return Path(base) / "xionghan-chess"


def config_path() -> Path:
    root = config_root()
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


def puzzles_file() -> Path:
    """用户导入的题库（P1-K）。随包题库是只读的，导入的题目落在这里。

    不自动创建文件：没有导入过就该「没有这个文件」，而不是留一个空 JSON
    让加载逻辑去处理空列表。
    """
    return data_dir() / "puzzles.json"


DEFAULT_SERVER_URL = "http://127.0.0.1:8000"

# P1-R：配置文件的 schema 版本。加这个字段不是因为现在需要迁移，而是因为
# **没有它就无法安全地迁移**：`{**DEFAULTS, **data}` 是浅合并，删键或改类型
# 之后旧文件里的值会原样留在内存里，只能靠每个调用点自己兜底。
# 有了版本号，迁移就集中在一处、只跑一次，并且可以被单测覆盖。
CONFIG_VERSION = 1

DEFAULTS: dict[str, Any] = {
    "schema_version": CONFIG_VERSION,
    "profile": "desktop_complete",
    "language": "zh-CN",
    "game_mode": "ai",
    "difficulty": "medium",
    "human_color": "red",
    "sound": True,
    "music": False,
    "music_style": "fc",
    "sound_volume": 70,
    "sound_pack": "classic",
    "music_volume": 40,
    "theme": "classic",
    "font": "system",
    "background": "1",
    "piece_style": "glyph",
    # 棋子画法：`glyph` = 1.7.0 的字形棋子（默认，界面逐像素不变）；`image` = 三风格美术图。
    # 新增键不 bump CONFIG_VERSION：`{**DEFAULTS, **data}` 会自动给旧配置补上默认值。
    "piece_render": "glyph",
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


def _as_int(value: Any, default: int, low: int, high: int) -> int:
    """转成整数并夹到范围内；转不了就用默认值。

    旧版配置或手改文件里 `"sound_volume": "70"`、`"initial_minutes": 0` 这类值
    都会在播放/开局时变成难查的异常，收敛一次比在每个调用点判断便宜。
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _migrate_v0(data: dict[str, Any]) -> dict[str, Any]:
    """0 -> 1：把「没版本号时代」的配置收敛到合法类型与范围。

    刻意**不删除未知键**：它们可能是更新版本写入的字段，也可能是用户自己加的
    备注，静默丢弃数据比留着更糟。
    """
    result = dict(data)
    result["initial_minutes"] = _as_int(result.get("initial_minutes"), 20, 1, 180)
    result["sound_volume"] = _as_int(result.get("sound_volume"), 70, 0, 100)
    result["music_volume"] = _as_int(result.get("music_volume"), 40, 0, 100)
    result["countdown_seconds"] = _as_int(result.get("countdown_seconds"), 30, 0, 600)
    for key in ("rule_options", "setup_slots"):
        if not isinstance(result.get(key), dict):
            result[key] = {}
    if result.get("language") not in ("zh-CN", "en"):
        result["language"] = DEFAULTS["language"]
    return result


# 键是「来源版本号」。每加一版就在这里登记一步，`migrate()` 会顺序执行。
_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {0: _migrate_v0}


def migrate(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """按 `schema_version` 顺序迁移，返回 (结果, 是否改动过)。

    比当前版本**更新**的配置按原样返回：说明用户用新版本写过文件，
    旧版本不该自作主张改它（读到的未知键会在合并时保留）。
    """
    raw_version = data.get("schema_version", 0)
    try:
        version = int(raw_version)
    except (TypeError, ValueError):
        version = 0
    if version > CONFIG_VERSION:
        return dict(data), False

    result = dict(data)
    while version < CONFIG_VERSION:
        step = _MIGRATIONS.get(version)
        if step is not None:
            result = step(result)
        version += 1
    result["schema_version"] = CONFIG_VERSION
    return result, raw_version != CONFIG_VERSION


# 棋子画法的**唯一**枚举：字形 + 三套美术。`piece_render` 只是它的派生字段
# （`glyph` → "glyph"，其余 → "image"），老配置由 `_normalize_piece_style` 迁移。
PIECE_STYLES: tuple[str, ...] = ("glyph", "traditional", "modern", "cartoon")


def _normalize_piece_style(style: object, render: object) -> tuple[str, str]:
    """把 `(piece_style, piece_render)` 收敛成 4 个 style 值 + 派生 render。

    - 新配置：`piece_style` 已是四值之一，render 由它决定；
    - 老配置：`piece_render == "glyph"` 一律视为 `style == "glyph"`（1.7.0 观感）；
    - 其它未知值：回落 traditional（与 `piece_assets.normalize_style` 同口径）。
    """
    # **老配置优先**：`piece_render == "glyph"` 时必须回到字形（哪怕当时还存着
    # `piece_style="cartoon"` 的美术偏好 —— 那只是"下次再选图片风格时"的记忆位）。
    if render == "glyph":
        return "glyph", "glyph"
    if isinstance(style, str) and style in PIECE_STYLES and style != "glyph":
        return style, "image"
    return "traditional", "image"


def _normalize_background(value: object) -> str:
    """背景图只有 1–5 五张；老配置里的 `"none"`（已下线的「原色」项）一律落到 `"1"`。"""
    if value in ("1", "2", "3", "4", "5"):
        return str(value)
    return "1"


def load_config() -> dict[str, Any]:
    try:
        raw = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)
    if not isinstance(raw, dict):
        return dict(DEFAULTS)
    migrated, changed = migrate(raw)
    merged = {**DEFAULTS, **migrated}
    style, render = _normalize_piece_style(merged.get("piece_style"), merged.get("piece_render"))
    if (merged.get("piece_style"), merged.get("piece_render")) != (style, render):
        merged["piece_style"], merged["piece_render"] = style, render
        changed = True
    background = _normalize_background(merged.get("background"))
    if merged.get("background") != background:
        merged["background"] = background
        changed = True
    if changed:
        # 迁移结果回写一次，之后每次启动都是「已是最新版本」，不再重复跑。
        try:
            save_config(merged)
        except OSError:
            # 只读目录/磁盘满：迁移已在内存里生效，没必要让启动失败。
            pass
    return merged


def save_config(data: dict[str, Any]) -> None:
    config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
