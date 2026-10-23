"""桌面端主题与资源（阶段1 S1-1 第二切片）。

从 `app.py` 抽出：棋子字形表、配色主题、字体选择、随包字体注册。
抽出的动机：`BoardWidget` 与各 QDialog 都要用 `NAMES`/`THEMES`/`FONT_CHOICES`，
若它们留在 `app.py`，这些类搬到 `ui/` 后会与 `app.py` 形成**循环导入**。

⚠️ **两个字体全局是被 `load_bundled_fonts()` 重新绑定的**：
    UI_FONT / PIECE_FONT
调用方必须用 `theme.UI_FONT`（模块属性访问）读取，**不要** `from .ui.theme import UI_FONT`
—— 那会在 import 时就绑死旧值，`load_bundled_fonts()` 之后读到的仍是默认字体。
（`NAMES` / `THEMES` / `FONT_CHOICES` 是字典，原地修改，直接 import 是安全的。）
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from xionghan_chess.core.model import Color, PieceType

# 资源根目录：本模块在 desktop/ui/ 下，resources 在 desktop/ 下 —— 回退两级。
RESOURCES = Path(__file__).resolve().parent.parent / "resources"


def resources_dir() -> Path:
    """随包资源根目录（icon / fonts / sounds / backgrounds / avatars / docs）。"""
    return RESOURCES


def resource(*parts: str) -> Path:
    """拼一个资源路径，例如 `resource("sounds", "drop.wav")`。"""
    return RESOURCES.joinpath(*parts)


def read_docs(name: str, fallback_label: str = "文档") -> str:
    """读取随包文档（`docs/` 下的 md），失败时返回可展示的中文提示而非抛异常。

    S1-1：`show_rules`/`show_help`/`show_about` 原先各自内联「拼路径 + try/except
    OSError + 拼错误串」，三份重复且都用 `Path(__file__).parent / "resources"` ——
    这类写法在文件搬家后就会静默指错（BoardWidget 搬 `ui/` 时就踩过）。统一走
    `resource()`，搬文件不再影响这里。
    """
    path = resource("docs", name)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"{fallback_label}读取失败：{exc}"


# 棋盘上的棋子字形。**必须保持中文**（切英文界面也不翻译）：这是象棋子的视觉本体。
NAMES = {
    Color.RED: {PieceType.KING:"漢",PieceType.ROOK:"俥",PieceType.HORSE:"傌",PieceType.ELEPHANT:"相",PieceType.ADVISOR:"仕",PieceType.CANNON:"炮",PieceType.PAWN:"兵",PieceType.GUARD:"尉",PieceType.ARCHER:"射",PieceType.THUNDER:"檑",PieceType.ARMOR:"甲",PieceType.ASSASSIN:"刺",PieceType.SHIELD:"楯",PieceType.PATROL:"巡"},
    Color.BLACK: {PieceType.KING:"汗",PieceType.ROOK:"車",PieceType.HORSE:"馬",PieceType.ELEPHANT:"象",PieceType.ADVISOR:"士",PieceType.CANNON:"砲",PieceType.PAWN:"卒",PieceType.GUARD:"衛",PieceType.ARCHER:"䠶",PieceType.THUNDER:"礌",PieceType.ARMOR:"胄",PieceType.ASSASSIN:"伺",PieceType.SHIELD:"碷",PieceType.PATROL:"廵"},
}

# 默认字体名（`load_bundled_fonts()` 会用随包字体覆盖成真实 family 名）
UI_FONT = "Microsoft YaHei"
PIECE_FONT = "KaiTi"

THEMES = {
    "classic": {"board": "#e7c88d", "line": "#684726", "frame": "#5a3b20", "panel": "#fff9ed", "window": "#d9c8a6", "accent": "#315c48"},
    "green": {"board": "#dfeeda", "line": "#315c36", "frame": "#365a3e", "panel": "#f6fbf2", "window": "#c8d8c1", "accent": "#315c48"},
    "blue": {"board": "#dcebf1", "line": "#285c73", "frame": "#31586a", "panel": "#f3f8fa", "window": "#c4d4da", "accent": "#315f76"},
    "purple": {"board": "#eee1f2", "line": "#724585", "frame": "#5c386d", "panel": "#fbf6fc", "window": "#d8c7dc", "accent": "#6d3e79"},
    "dark": {"board": "#34302b", "line": "#c9b58e", "frame": "#171513", "panel": "#29241f", "window": "#1d1a17", "accent": "#8e3b32"},
}

FONT_CHOICES = {"system": UI_FONT, "kaiti": PIECE_FONT, "songti": "SimSun", "fangsong": "FangSong"}


def load_bundled_fonts() -> None:
    """注册随包字体（msyh.ttc 界面 / simkai.ttf 棋子），并把默认字体名换成真实 family。

    注意会**重新绑定**模块全局 UI_FONT / PIECE_FONT —— 调用方须用 `theme.UI_FONT` 读取。
    """
    global UI_FONT, PIECE_FONT
    font_dir = RESOURCES / "fonts"
    loaded: dict[str, str] = {}
    for filename, key in (("msyh.ttc", "ui"), ("simkai.ttf", "piece")):
        font_id = QFontDatabase.addApplicationFont(str(font_dir / filename))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if families:
            loaded[key] = families[0]
    UI_FONT = loaded.get("ui", UI_FONT)
    PIECE_FONT = loaded.get("piece", PIECE_FONT)
    FONT_CHOICES["system"] = UI_FONT
    FONT_CHOICES["kaiti"] = PIECE_FONT
    QApplication.instance().setFont(QFont(UI_FONT, 10))
