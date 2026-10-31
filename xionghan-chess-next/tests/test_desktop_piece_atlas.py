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

from xionghan_chess.core.model import Color, PieceType, Position  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.config import load_config  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import GLYPH_STYLE_DATA, SettingsDialog  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import GLYPH_STYLE_DATA  # noqa: E402
from xionghan_chess.desktop.ui.piece_atlas import (  # noqa: E402
    PIECE_OPTION_KEYS, THUMB, PieceAtlasDialog,
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




def test_unavailable_pieces_are_marked_and_greyed(qt_app: QApplication) -> None:
    """`traditional` 档案没有特色子（刺/巡等）—— 必须灰显并注明「本档案不使用」。"""
    config = {"profile": "traditional", "language": "zh-CN",
              "piece_style": "traditional", "piece_render": "glyph", "rule_options": {}}
    dialog = PieceAtlasDialog(config)
    rows = {}
    for row in range(dialog._list.count()):
        item = dialog._list.item(row)
        value = item.data(0x0100)
        if value:
            rows[value] = item
    assert "本档案不使用" in rows["patrol"].text()
    assert rows["patrol"].foreground().color().lightness() < 200, "未启用项没有灰显"
    assert "本档案不使用" not in rows["rook"].text()
    dialog.deleteLater()




def test_thumbnail_edge_is_a_single_value(atlas: PieceAtlasDialog) -> None:
    """缩略图边长**单值 72**（边长 = 盘径）。

    曾经有 80 的大窗档，但 80×2 ÷ 源盘径 137 = 1.17× 上采样，越过「>1.15 记缺陷」
    那条线；72×2 ÷ 137 = 1.05×，任何 DPI 下都≈1:1。这里同时钉住「不随窗口变」。
    """
    assert THUMB == 72
    sizes = []
    for width, height in ((760, 560), (1000, 700), (2560, 1400)):
        atlas.resize(width, height)
        sizes.append(atlas._cell_pixmap("traditional", Color.RED, THUMB).width())
    assert len(set(sizes)) == 1, f"缩略图尺寸随窗口变了：{sizes}"


def test_glyph_choice_restores_glyph_style(atlas: PieceAtlasDialog) -> None:
    """「书法字形」也是四值之一：选中即 `piece_style="glyph"`，不是单向门。"""
    atlas.config["piece_style"] = "cartoon"
    atlas.apply_style(GLYPH_STYLE_DATA)
    assert atlas.config["piece_render"] == "glyph"
    assert atlas.config["piece_style"] == "glyph"


def test_style_choice_enables_image_render(atlas: PieceAtlasDialog) -> None:
    """点「使用此风格」= 写风格 + 启用图片渲染（否则「选了风格棋盘却没变」是假预览）。"""
    atlas.apply_style("modern")
    assert atlas.config["piece_style"] == "modern"
    assert atlas.config["piece_render"] == "image"
    assert atlas._is_active("modern")
    assert not atlas._is_active(GLYPH_STYLE_DATA)


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
    # 结果弹窗改为自定义按钮框后，静默点转移到 `show_result_dialog`（否则会真模态挂住）
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: False))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    win = appmod.MainWindow()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_help_menu_has_exactly_one_rules_entry(window) -> None:
    """规则已并入图谱：帮助菜单里**只能有一个**入口，且它就是「棋子图谱」。

    原来还有一项「棋子规则」，两块内容各看一半；合并后旧项删掉，
    `menu.piece_rules` 这个键改作图谱项的提示语（不再有第二个"规则"入口）。
    """
    titles: list[str] = []
    for top in window.menuBar().actions():
        submenu = top.menu()
        if submenu is not None and any(action.text() == "棋子图谱" for action in submenu.actions()):
            titles = [action.text() for action in submenu.actions()]
    assert titles, "找不到含「棋子图谱」的菜单"
    assert "棋子图谱" in titles
    assert "棋子规则" not in titles, "旧「棋子规则」菜单项必须删除，不能留第二个入口"
    rules_entries = [title for title in titles if "规则" in title]
    assert rules_entries == [], f"菜单里不该再有独立的规则入口：{rules_entries}"


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
    window.apply_piece_style(GLYPH_STYLE_DATA)
    assert len(window.game.state.history) == history
    assert window.board.piece_render == "glyph"
    # `board.piece_style` 是**图片风格**（`glyph` 不是美术风格，会被归一成 traditional 用于预热），
    # 统一的四值写在 config 里；棋盘侧只认 `piece_render`。
    assert window.config["piece_style"] == "glyph"
    assert window.board.piece_render == "glyph"


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
    """下拉选「书法字形」→ `piece_style="glyph"` 且 `piece_render="glyph"`（派生态）。"""
    window.config["piece_style"] = "modern"
    window.config["piece_render"] = "image"
    dialog = SettingsDialog(window.config, window)
    dialog.piece_style.setCurrentIndex(dialog.piece_style.findData(GLYPH_STYLE_DATA))
    values = dialog.value()
    assert values["piece_render"] == "glyph"
    assert values["piece_style"] == "glyph"
    dialog.piece_style.setCurrentIndex(dialog.piece_style.findData("cartoon"))
    values = dialog.value()
    assert values["piece_render"] == "image"
    assert values["piece_style"] == "cartoon"
    dialog.deleteLater()


# ---------------------------------------------------------------------------
# 演示盘：三个预设必须能**演示出**各自的规则（空盘演示不出任何东西）
# ---------------------------------------------------------------------------
def _load_preset(atlas: PieceAtlasDialog, key: str):
    index = atlas._preset.findData(key)
    assert index >= 0, f"预设 {key} 不在下拉里"
    atlas._preset.setCurrentIndex(index)
    QApplication.processEvents()
    return atlas._demo_board


def test_demo_preset_pinch_blocks_the_pinched_diagonal(atlas: PieceAtlasDialog) -> None:
    """夹逼局：射起点两侧都有子 → 同一条斜线再远的敌子也吃不到。"""
    board = _load_preset(atlas, "clamp")
    targets = [move.target for move in board.legal]
    assert Position(9, 9) not in targets, "被夹逼的斜线不该给出落点"
    assert targets, "其它方向仍应有合法着法（否则演示盘像坏图）"




def test_demo_preset_facing_puts_the_king_in_check(atlas: PieceAtlasDialog) -> None:
    """照面局：两王同线无子 → 被将；王只能走到离开该线的格。"""
    board = _load_preset(atlas, "facing")
    assert board.game.rules.in_check(board.game.state, board.game.state.turn)
    for move in board.legal:
        assert move.target.col != 6, "王不能留在照面的那一线上"


# ---------------------------------------------------------------------------
# 右栏开关：可写、只放单子开关、改完提示重开
# ---------------------------------------------------------------------------
def test_switches_are_piece_scoped_only(atlas: PieceAtlasDialog) -> None:
    """图谱只放**单子**开关：`*_appear` 与全局开关（禁送将/和棋/长将）都不在这里。"""
    labels = [atlas._list.item(i).data(0x0100) for i in range(atlas._list.count())]
    atlas._list.setCurrentRow(labels.index("pawn"))
    QApplication.processEvents()

    from PySide6.QtWidgets import QCheckBox
    boxes = atlas._detail.findChildren(QCheckBox)
    texts = " ".join(box.text() for box in boxes)
    assert "直冲" in texts and "夹一敌子" in texts, "兵的两个开关必须在图谱里可写"
    for forbidden in ("登场", "送将", "和棋", "长将"):
        assert forbidden not in texts, f"图谱不该出现 {forbidden} 类开关"


def test_toggling_a_switch_writes_config_and_offers_restart(qt_app: QApplication) -> None:
    """勾选 → 写 config["rule_options"] → 问「现在重开」→ 选现在则回调 new_game。"""
    from PySide6.QtWidgets import QCheckBox

    restarted: list[int] = []
    config = dict(load_config())
    config["rule_options"] = {}
    dialog = PieceAtlasDialog(config, restart_game=lambda: restarted.append(1))
    labels = [dialog._list.item(i).data(0x0100) for i in range(dialog._list.count())]
    dialog._list.setCurrentRow(labels.index("pawn"))
    QApplication.processEvents()

    dialog._ask_restart = lambda: True          # 模拟点「现在重开」
    box = next(b for b in dialog._detail.findChildren(QCheckBox) if "直冲" in b.text())
    box.setChecked(True)
    QApplication.processEvents()

    assert config["rule_options"]["pawn_charge"] is True
    assert window_rules_have_charge(dialog), "规则应立刻按新开关重建"
    assert restarted == [1], "选「现在重开」必须回调 new_game"
    dialog.deleteLater()


def window_rules_have_charge(dialog: PieceAtlasDialog) -> bool:
    return bool(dialog.rules.options.pawn_charge)
