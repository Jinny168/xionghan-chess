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

from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

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
    Color.RED: {PieceType.KING:"漢",PieceType.ROOK:"俥",PieceType.HORSE:"傌",PieceType.ELEPHANT:"相",PieceType.ADVISOR:"仕",PieceType.CANNON:"炮",PieceType.PAWN:"兵",PieceType.GUARD:"尉",PieceType.ARCHER:"射",PieceType.THUNDER:"檑",PieceType.PATROL:"巡"},
    Color.BLACK: {PieceType.KING:"汗",PieceType.ROOK:"車",PieceType.HORSE:"馬",PieceType.ELEPHANT:"象",PieceType.ADVISOR:"士",PieceType.CANNON:"砲",PieceType.PAWN:"卒",PieceType.GUARD:"衛",PieceType.ARCHER:"䠶",PieceType.THUNDER:"礌",PieceType.PATROL:"廵"},
}

# 默认字体名（`load_bundled_fonts()` 会用随包字体覆盖成真实 family 名）。
#
# 阶段2 S2-4：随包字体从**微软授权的 msyh.ttc / simkai.ttf（31.5 MB）**
# 换成 Noto Sans SC / Noto Serif SC 的 GB2312 子集（9.8 MB，省 21.7 MB）。
# 换的理由不只是体积：微软雅黑/楷体随安装包分发需要单独授权，此前是直接把系统字体
# 拷进仓库，授权状态未查证。Noto 系列是 SIL OFL 1.1，明确允许嵌入与再分发
# （OFL.txt 与字体同目录，子集已按条件 3 改名，见 scripts/build_fonts.py）。
UI_FONT = "Noto Sans SC Subset"
PIECE_FONT = "Noto Serif SC Subset"

THEMES = {
    "classic": {"board": "#e7c88d", "line": "#684726", "frame": "#5a3b20", "panel": "#fff9ed", "window": "#d9c8a6", "accent": "#315c48"},
    "green": {"board": "#dfeeda", "line": "#315c36", "frame": "#365a3e", "panel": "#f6fbf2", "window": "#c8d8c1", "accent": "#315c48"},
    "blue": {"board": "#dcebf1", "line": "#285c73", "frame": "#31586a", "panel": "#f3f8fa", "window": "#c4d4da", "accent": "#315f76"},
    "purple": {"board": "#eee1f2", "line": "#724585", "frame": "#5c386d", "panel": "#fbf6fc", "window": "#d8c7dc", "accent": "#6d3e79"},
    "dark": {"board": "#34302b", "line": "#c9b58e", "frame": "#171513", "panel": "#29241f", "window": "#1d1a17", "accent": "#8e3b32"},
}

FONT_CHOICES = {"system": UI_FONT, "kaiti": PIECE_FONT, "songti": "SimSun", "fangsong": "FangSong"}


def _gui_application() -> QGuiApplication | None:
    """当前 GUI 应用实例；没有就返回 None。

    单独抽出来是为了**可测**：`QFontDatabase.addApplicationFont()` 在没有
    QGuiApplication 时不是抛异常，而是**直接段错误**（本机实测 exit 139）。
    段错误没法用 try/except 兜，只能在调用前先判。
    """
    return QGuiApplication.instance()


def load_bundled_fonts() -> None:
    """注册随包字体（Noto Sans SC Subset 界面 / Noto Serif SC Subset 棋子）。

    注意会**重新绑定**模块全局 UI_FONT / PIECE_FONT —— 调用方须用 `theme.UI_FONT` 读取。

    S2-4：字体文件与 family 名一起换掉。若随包字体加载失败（文件缺失/损坏），
    保持模块里的默认 family 名不变，Qt 会回退到系统字体 —— 不崩，只是样式降级。

    P1-Q：**没有 QGuiApplication 时整体跳过**。字体注册只是「让 Qt 认识这两个
    family」，没有 GUI 应用时既无意义也不安全（见 `_gui_application` 的说明）。
    此前这里直接 `QApplication.instance().setFont(...)`，无应用时抛 AttributeError；
    但真正致命的是它前面的 `addApplicationFont` —— 那一步会先把进程打死。
    """
    app = _gui_application()
    if app is None:
        return
    global UI_FONT, PIECE_FONT
    font_dir = RESOURCES / "fonts"
    loaded: dict[str, str] = {}
    for filename, key in (("NotoSansSC-subset.ttf", "ui"), ("NotoSerifSC-subset.ttf", "piece")):
        font_id = QFontDatabase.addApplicationFont(str(font_dir / filename))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if families:
            loaded[key] = families[0]
    UI_FONT = loaded.get("ui", UI_FONT)
    PIECE_FONT = loaded.get("piece", PIECE_FONT)
    FONT_CHOICES["system"] = UI_FONT
    FONT_CHOICES["kaiti"] = PIECE_FONT
    # S2-4：原来 "songti"/"fangsong" 硬指向系统 SimSun / FangSong —— 机器上没装就静默回退。
    # 现改用已注册的随包字体：宋体选项恰好就是随包的 Noto Serif SC，仿宋回退到界面字体。
    FONT_CHOICES["songti"] = PIECE_FONT
    FONT_CHOICES["fangsong"] = UI_FONT
    app.setFont(QFont(UI_FONT, 10))
