"""E1 高对比棋子组（桌面 / Python 侧）门禁。

覆盖：
- 派生纯函数：达标令牌原样返回（mix=0）；不达标令牌按盘底方向派生且比值提升；
- 配置默认关闭；
- 棋盘开关只叠加对比增强，不改已选主题 / 棋子风格。

JS 两侧（`web/js`、`webapp/js`）的同公式断言在第二段补；本文件不做 canvas 像素基线。
"""

from __future__ import annotations

import pytest

from xionghan_chess.desktop import config
from xionghan_chess.desktop.ui import contrast

pytest.importorskip("PySide6", reason="棋盘控件依赖 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import BoardWidget  # noqa: E402


def test_default_switch_is_off() -> None:
    """开关默认关闭：老用户配置不被自动打开高对比。"""
    assert config.DEFAULTS["high_contrast_pieces"] is False


def test_derived_color_is_untouched_when_already_meeting_target() -> None:
    """既有令牌在目标比值内时原样返回，不做派生（mix=0）。"""
    derived = contrast.derive_for_background("#9a2424", "#e7c88d", contrast.TEXT_TARGET)
    assert derived.mix == 0.0
    assert derived.color == "#9a2424"
    assert derived.met is True


def test_derived_color_improves_ratio_when_below_target() -> None:
    """对比不足时沿盘底方向派生，实测比值必须不低于原比值。"""
    # 深底上的中灰令牌：与深底对比不足，派生向白提亮。
    derived = contrast.derive_for_background("#6b6b6b", "#34302b", contrast.TEXT_TARGET)
    original = contrast.contrast_ratio("#6b6b6b", "#34302b")
    assert derived.ratio >= original
    assert derived.mix > 0.0


def test_graphic_target_is_lower_than_text_target() -> None:
    """非文本图形（可走点 / 可吃点）按 3:1 判据，文本按 4.5:1。"""
    assert contrast.GRAPHIC_TARGET < contrast.TEXT_TARGET


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


def _board() -> BoardWidget:
    game = Game("desktop_complete")
    board = BoardWidget()
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", "glyph")
    return board


def test_board_switch_does_not_change_theme_or_style(qt_app: QApplication) -> None:
    """切换开关不覆盖已选主题与棋子风格，只叠加对比增强。"""
    board = _board()
    before_theme, before_style = board.theme_name, board.piece_style
    board.set_assists(
        selection=True,
        legal_targets=True,
        capture_hints=True,
        animations=True,
        high_contrast=True,
    )
    assert board.high_contrast is True
    assert board.theme_name == before_theme == "classic"
    assert board.piece_style == before_style == "traditional"


def test_board_switch_default_off(qt_app: QApplication) -> None:
    board = _board()
    assert board.high_contrast is False


# ---------------------------------------------------------------------------
# 第二段：三端公式一致、白名单棘轮、实测脚本与偏好隔离。
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_allowlist_entry_count_unchanged() -> None:
    """E1 零新增色值：白名单条目数与 D 终验基线一致（139 条）。"""
    lines = [
        line
        for line in (ROOT / "benchmarks" / "color_allowlist.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 139


def test_js_mirrors_share_formula_constants() -> None:
    """webapp / web 旧树与桌面共用同一套派生常量（目标比值、明暗阈值、步长）。"""
    board_js = (ROOT / "webapp" / "js" / "ui" / "board.js").read_text(encoding="utf-8")
    web_js = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    for token in (
        "CONTRAST_TEXT_TARGET = 4.5",
        "CONTRAST_GRAPHIC_TARGET = 3.0",
        "_CONTRAST_LIGHT_THRESHOLD = 0.179",
        "_MIX_STEP = 0.05",
    ):
        assert token in board_js, f"webapp 缺派生常量 {token}"
        assert token in web_js, f"web 旧树缺派生常量 {token}"
    assert contrast.TEXT_TARGET == 4.5
    assert contrast.GRAPHIC_TARGET == 3.0


def test_prefs_default_off_and_isolated_from_theme() -> None:
    """三端偏好默认关；高对比字段独立透传，不回写已选主题 / 棋子风格。"""
    webapp = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
    web = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    assert "highContrastPieces: false" in webapp
    assert "highContrastPieces:false" in web
    assert "highContrast: app.prefs.highContrastPieces === true" in webapp
    assert config.DEFAULTS["high_contrast_pieces"] is False


def _load_measure():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "measure_contrast", ROOT / "scripts" / "measure_contrast_high_contrast.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_measure_script_text_elements_meet_target() -> None:
    """实测脚本：棋子文本元素派生后必须达 4.5:1。"""
    report = _load_measure().measure()
    for endpoint, spec in report["endpoints"].items():
        for theme_name, theme in spec["themes"].items():
            for key, item in theme.items():
                if isinstance(item, dict) and item["criterion"] == "text":
                    assert item["met"], f"{endpoint}/{theme_name}/{key} 文本未达 {item['target']}:1"


def test_graphic_gaps_flagged_with_criterion() -> None:
    """图形元素按 3:1 判据；不达标的保留实测比值并标 met=false，不偷加色值。"""
    report = _load_measure().measure()
    for endpoint, spec in report["endpoints"].items():
        for theme_name, theme in spec["themes"].items():
            for key, item in theme.items():
                if isinstance(item, dict) and item["criterion"] == "graphic":
                    assert item["target"] == 3.0
                    assert "ratio" in item
                    assert isinstance(item["met"], bool)


def test_graphic_after_meets_graphic_target() -> None:
    """F1：高对比组内提示点派生 + 提不透明后，图形判据 3:1 全部达标。

    before（默认主题半透明合成）允许不达标准并保留差值；after（高对比派生后）
    必须 met=true 且比值 ≥ 3.0。
    """
    report = _load_measure().measure()
    gaps: list[str] = []
    for endpoint, spec in report["endpoints"].items():
        for theme_name, theme in spec["themes"].items():
            for key, item in theme.items():
                if isinstance(item, dict) and item["criterion"] == "graphic":
                    after = item["after"]
                    if not after["met"] or after["ratio"] < 3.0:
                        gaps.append(f"{endpoint}/{theme_name}/{key}={after['ratio']}")
                    # 派生后比值不得低于 before 现状。
                    assert after["ratio"] >= item["before"]["ratio"], (
                        f"{endpoint}/{theme_name}/{key} 派生后比值倒退："
                        f"before={item['before']['ratio']} after={after['ratio']}"
                    )
    assert not gaps, f"高对比组图形提示点未达 3:1: {', '.join(gaps)}"


def test_hc_dot_radius_constant_shared() -> None:
    """F1：高对比组可走点半径三端同为 0.16（授权上限 0.18 格）。"""
    board_js = (ROOT / "webapp" / "js" / "ui" / "board.js").read_text(encoding="utf-8")
    web_js = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    desktop_src = (
        ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "board_widget.py"
    ).read_text(encoding="utf-8")
    assert "LEGAL_DOT_RATIO_HC = 0.16" in desktop_src
    assert "const LEGAL_DOT_RATIO_HC = 0.16;" in board_js
    assert "const LEGAL_DOT_RATIO_HC = 0.16;" in web_js
