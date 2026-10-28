"""棋子图谱窗口的行为契约（offscreen）。

## 断言的是「用户能看到的东西」

- 14 子清单齐全，且本档案不启用的子灰显并注明（`rules.enabled_piece_types`）；
- 缺图格不留白：同风格底盘 + 字形 + 「字」小标；
- 「使用此风格」**不重开对局**：走子数、时钟、悔棋可用性都不变（只改画法）；
- 两个入口（菜单 / 设置页按钮）打开的是同一个窗口；
- 图谱本身的缩略图始终走图片路径，与棋盘的 `piece_render` 无关。
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="图谱依赖 PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.model import Color, PieceType  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.config import load_config  # noqa: E402
from xionghan_chess.desktop.ui import piece_assets, theme  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import GLYPH_STYLE_DATA, SettingsDialog  # noqa: E402
from xionghan_chess.desktop.ui.piece_atlas import (  # noqa: E402
    GLYPH_CHOICE, PIECE_OPTION_KEYS, REGULAR_KINDS, SPECIAL_KINDS, PieceAtlasDialog,
)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


@pytest.fixture()
def config() -> dict:
    return {
        "profile": "desktop_complete",
        "language": "zh-CN",
        "piece_style": "traditional",
        "piece_render": "glyph",
        "rule_options": {},
    }


@pytest.fixture()
def atlas(qt_app: QApplication, config: dict):
    dialog = PieceAtlasDialog(dict(config))
    yield dialog
    dialog.close()
    dialog.deleteLater()


def kind_items(dialog: PieceAtlasDialog) -> list[str]:
    """清单里真正的棋子项（跳过两个不可选的分组标题）。"""
    out = []
    for row in range(dialog._list.count()):
        item = dialog._list.item(row)
        value = item.data(0x0100)  # Qt.ItemDataRole.UserRole
        if value:
            out.append(value)
    return out


def test_constructs_without_a_game(qt_app: QApplication, config: dict) -> None:
    """图谱不依赖 `game`：没有对局也能开（构造时不碰 MainWindow）。"""
    dialog = PieceAtlasDialog(dict(config))
    assert dialog.size().width() == 900 and dialog.size().height() == 640
    assert dialog.minimumWidth() == 760 and dialog.minimumHeight() == 560
    dialog.deleteLater()


def test_lists_all_fourteen_piece_types(atlas: PieceAtlasDialog) -> None:
    listed = kind_items(atlas)
    assert listed == [kind.value for kind in (*REGULAR_KINDS, *SPECIAL_KINDS)]
    assert len(listed) == 14


def test_unavailable_pieces_are_marked_and_greyed(qt_app: QApplication) -> None:
    """`traditional` 档案没有甲/刺/楯/巡等特色子 —— 必须灰显并注明「本档案不使用」。"""
    config = {"profile": "traditional", "language": "zh-CN",
              "piece_style": "traditional", "piece_render": "glyph", "rule_options": {}}
    dialog = PieceAtlasDialog(config)
    rows = {}
    for row in range(dialog._list.count()):
        item = dialog._list.item(row)
        value = item.data(0x0100)
        if value:
            rows[value] = item
    assert "本档案不使用" in rows["armor"].text()
    assert "本档案不使用" in rows["patrol"].text()
    assert rows["armor"].foreground().color().lightness() < 200, "未启用项没有灰显"
    assert "本档案不使用" not in rows["rook"].text()
    dialog.deleteLater()


def test_missing_art_cell_draws_glyph_not_blank(atlas: PieceAtlasDialog) -> None:
    """甲/刺/楯：三风格都没有美术，缩略图必须是「同风格底盘 + 字形」，不是空白。"""
    atlas.kind = PieceType.ARMOR
    for style in piece_assets.STYLES:
        artwork = atlas._cell_pixmap(style, Color.RED, 72)
        assert not artwork.isNull()
        image = artwork.toImage()
        opaque = sum(1 for y in range(image.height()) for x in range(image.width())
                     if image.pixelColor(x, y).alpha() > 128)
        assert opaque > 72 * 72 * 0.25, f"{style} 缺图格几乎空白（不透明像素 {opaque}）"
        assert piece_assets.is_missing(style, Color.RED, PieceType.ARMOR)


def test_thumbnail_sizes_are_capped(atlas: PieceAtlasDialog) -> None:
    """缩略图逻辑边长 72（窄窗）/ 80（≥900），上限 80 —— 再大就超过源盘径。"""
    atlas.resize(760, 560)
    assert atlas._thumb_edge() == 72
    atlas.resize(1000, 700)
    assert atlas._thumb_edge() == 80
    atlas.resize(2560, 1400)
    assert atlas._thumb_edge() == 80


def test_glyph_choice_restores_glyph_render_without_losing_style(atlas: PieceAtlasDialog) -> None:
    """「书法字形」是回退项：切回 glyph，但 `piece_style` 保留原值（不是单向门）。"""
    atlas.config["piece_style"] = "cartoon"
    atlas.apply_style(GLYPH_CHOICE)
    assert atlas.config["piece_render"] == "glyph"
    assert atlas.config["piece_style"] == "cartoon"


def test_style_choice_enables_image_render(atlas: PieceAtlasDialog) -> None:
    """点「使用此风格」= 写风格 + 启用图片渲染（否则「选了风格棋盘却没变」是假预览）。"""
    atlas.apply_style("modern")
    assert atlas.config["piece_style"] == "modern"
    assert atlas.config["piece_render"] == "image"
    assert atlas._is_active("modern")
    assert not atlas._is_active(GLYPH_CHOICE)


def test_rule_keys_belong_to_the_rule_options() -> None:
    """「本局规则现状」引用的开关必须真的存在于 `RuleOptions`（避免抄错键名）。"""
    from dataclasses import fields

    from xionghan_chess.core.profiles import RuleOptions

    known = {field.name for field in fields(RuleOptions)}
    for kind, keys in PIECE_OPTION_KEYS.items():
        for key in keys:
            assert key in known, f"{kind.value} 引用了不存在的规则开关 {key}"


def test_moves_section_reads_chinese_doc_and_english_locale(atlas: PieceAtlasDialog) -> None:
    """中文取 `PIECE_RULES.md` 的 H2 小节；英文用 locale（不读中文文档）。"""
    atlas.kind = PieceType.ROOK
    section = atlas._rules_section()
    assert section and "横线" in section
    atlas.language = "en"
    assert atlas._rules_section() is not None  # 解析逻辑与语言无关，取用由界面决定


# ---------------------------------------------------------------------------
# 入口与「即时生效」
# ---------------------------------------------------------------------------
@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    win = appmod.MainWindow()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_help_menu_lists_atlas_above_piece_rules(window) -> None:
    """菜单「帮助 → 棋子图谱」必须排在「棋子规则」之上。"""
    titles: list[str] = []
    for top in window.menuBar().actions():
        submenu = top.menu()
        if submenu is not None and any(action.text() == "棋子规则" for action in submenu.actions()):
            titles = [action.text() for action in submenu.actions()]
    assert titles, "找不到含「棋子规则」的菜单"
    assert "棋子图谱" in titles
    assert titles.index("棋子图谱") < titles.index("棋子规则")


def test_switching_style_keeps_the_game(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """即时切换：走子数 / 时钟 / 悔棋可用性都与切前一致，且不重建界面。"""
    moves = window.game.rules.legal_moves(window.game.state, window.game.state.turn)
    window.game.move(moves[0])
    history = len(window.game.state.history)
    clocks = dict(window.game.state.clocks_ms)
    assert history > 0

    central = window.centralWidget()
    window.apply_piece_style("cartoon")

    assert len(window.game.state.history) == history, "切换风格把对局弄丢了"
    assert window.game.state.clocks_ms == clocks
    assert window.centralWidget() is central, "切换风格重建了中央控件"
    assert window.board.piece_style == "cartoon"
    assert window.board.piece_render == "image"
    assert load_config()["piece_style"] == "cartoon"
    assert load_config()["piece_render"] == "image"


def test_switching_back_to_glyph_keeps_the_game(window) -> None:
    moves = window.game.rules.legal_moves(window.game.state, window.game.state.turn)
    window.game.move(moves[0])
    history = len(window.game.state.history)
    window.apply_piece_style("cartoon")
    window.apply_piece_style(GLYPH_CHOICE)
    assert len(window.game.state.history) == history
    assert window.board.piece_render == "glyph"
    assert window.board.piece_style == "cartoon", "回退字形不该抹掉风格偏好"


def test_settings_dialog_exposes_the_same_atlas(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """设置页「棋子美术风格」：第一项是「书法字形（默认）」，右侧有「预览三风格」。"""
    dialog = SettingsDialog(window.config, window)
    assert dialog.piece_style.currentData() == GLYPH_STYLE_DATA
    assert "书法字形" in dialog.piece_style.currentText()
    assert [dialog.piece_style.itemData(index) for index in range(1, 4)] == [
        "traditional", "modern", "cartoon"]
    opened: list[dict] = []

    class _FakeAtlas:
        def __init__(self, config, parent=None, apply_style=None) -> None:
            opened.append({"config": config, "apply_style": apply_style})

        def exec(self) -> int:
            return 0

    monkeypatch.setattr("xionghan_chess.desktop.ui.piece_atlas.PieceAtlasDialog", _FakeAtlas)
    dialog.open_piece_atlas()
    assert opened and opened[0]["config"] is window.config, "预览按钮没有打开同一个窗口"
    assert callable(opened[0]["apply_style"]), "图谱没有拿到主窗口的即时生效回调"
    dialog.deleteLater()


def test_settings_choice_maps_to_piece_render(window) -> None:
    """下拉选「书法字形」→ 回写 `piece_render="glyph"` 且不动 `piece_style`。"""
    window.config["piece_style"] = "modern"
    window.config["piece_render"] = "image"
    dialog = SettingsDialog(window.config, window)
    dialog.piece_style.setCurrentIndex(dialog.piece_style.findData(GLYPH_STYLE_DATA))
    values = dialog.value()
    assert values["piece_render"] == "glyph"
    assert values["piece_style"] == "modern"
    dialog.piece_style.setCurrentIndex(dialog.piece_style.findData("cartoon"))
    values = dialog.value()
    assert values["piece_render"] == "image"
    assert values["piece_style"] == "cartoon"
    dialog.deleteLater()
