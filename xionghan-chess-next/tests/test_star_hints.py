"""P1-7 射·星轨提示层：默认关闭、场景/档位守卫、零干扰、零采集。

对拍（两端锚点逐点相等）在 `test_star_lattice_parity.py`；这里守的是
「不该出现的地方一律不出现」：
  · 三端默认关（含桌面 set_assists 的 demo 兼容调用）；
  · 桌面 off 态 / 未选中射 / 增强档逐像素零差异；
  · 桌面锚点放射线有界（≤4）且确实复用 core 的最近星位距离；
  · webapp / web 的开关、守卫、文案、零采集载荷静态断言；
  · 新增模块不引入任何网络调用。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEBAPP_APP = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
WEBAPP_BOARD = (ROOT / "webapp" / "js" / "ui" / "board.js").read_text(encoding="utf-8")
WEBAPP_HTML = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
WEBAPP_STAR = (ROOT / "webapp" / "js" / "ui" / "star_hints.js").read_text(encoding="utf-8")
WEB_APP = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
WEB_HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
WEB_STAR = (ROOT / "web" / "js" / "star-hints.js").read_text(encoding="utf-8")

NETWORK = re.compile(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon")


# ---------------------------------------------------------------- 三端默认关闭
def test_defaults_are_off_on_all_three_ends() -> None:
    from xionghan_chess.desktop.config import DEFAULTS

    assert DEFAULTS["archer_star_hints"] is False
    assert "starHints: false," in WEBAPP_APP
    assert "starHints:false," in WEB_APP
    # 两个开关在 HTML 里都不能带 checked（老配置由 JS 的 ?? / === true 兜底）
    assert re.search(r'<input type="checkbox" id="optStarHints">', WEBAPP_HTML)
    assert re.search(r'<input type="checkbox" id="starHintsEnabled">', WEB_HTML)


def test_new_modules_have_no_network_calls() -> None:
    for name, source in (
        ("webapp star_hints.js", WEBAPP_STAR),
        ("web star-hints.js", WEB_STAR),
        ("webapp board.js", WEBAPP_BOARD),
    ):
        assert not NETWORK.search(source), f"{name} 引入了网络调用（零采集红线）"


# ---------------------------------------------------------------- web 零采集
def test_web_preferences_post_excludes_star_hints() -> None:
    """本地 xh-preferences 照存，但 /api/me/preferences 的 body 不得含新键。"""
    match = re.search(r"function persistPreferences\(\)\{[^\n]*\}", WEB_APP)
    assert match, "找不到 persistPreferences"
    body = match.group(0)
    assert "safeStorageSet('xh-preferences',JSON.stringify(app.preferences))" in body
    assert "const {starHints:_omitStarHints,...syncable}=app.preferences" in body
    assert "body:JSON.stringify({preferences:syncable})" in body
    assert "preferences:app.preferences" not in body


def test_no_desktop_cloud_mapping_for_star_hints() -> None:
    app_source = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")
    assert "archer_star_hints" not in app_source[app_source.index("cloud_to_desktop") :]


# ---------------------------------------------------------------- web/webapp 守卫与文案
def test_webapp_guards_and_wiring() -> None:
    for snippet in (
        "app.prefs.starHints",
        "profile.rows === 13",
        "app.game.rules.options.archer_enhanced_mode === false",
        "selectedPiece.type === 'archer'",
        "!app.puzzle",
        "archerAnchorRays(app.game.rules, app.selected)",
        "showStarHints,",
    ):
        assert snippet in WEBAPP_APP, f"webapp render() 缺少守卫/接线：{snippet}"
    assert "if (view.showStarHints) this.drawStarHints(view, theme, geom);" in WEBAPP_BOARD
    assert "ctx.globalAlpha = 0.24" in WEBAPP_BOARD
    assert "theme.line" in WEBAPP_BOARD
    assert 'data-i18n-title="settings.starHintsHint"' in WEBAPP_HTML


def test_web_guards_and_wiring() -> None:
    for snippet in (
        "app.replayIndex!==null",
        "app.puzzleSession",
        "app.spectator",
        "app.options.archer_enhanced_mode!==false",
        "app.selected.type!=='archer'",
        "globalThis.XHStarHints?.archerAnchorRays",
        "lastMoveInk(.20)",
    ):
        assert snippet in WEB_APP, f"web 旧树缺少守卫/接线：{snippet}"
    assert "drawStarPoints(g)}drawStarHints(g);drawHighlights(g)" in WEB_APP
    assert 'src="/js/star-hints.js?v=2.0.3"' in WEB_HTML


def test_legend_wording_is_exact_on_all_ends() -> None:
    legend = "空心环＝星位（射程锚点），实心圆点＝可落子"
    zh = (ROOT / "locales" / "zh-CN.json").read_text(encoding="utf-8")
    i18n = (ROOT / "webapp" / "js" / "i18n.js").read_text(encoding="utf-8")
    assert legend in zh
    assert legend in i18n


# ---------------------------------------------------------------- 桌面渲染
pytest.importorskip("PySide6", reason="桌面渲染守卫依赖 PySide6")

from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType, Position  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import (  # noqa: E402
    STAR_HINT_ALPHA,
    BoardWidget,
)

SIZE = 900
ARCHER = Position(12, 0)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def _game(pieces: list[Piece] | None = None, profile: str = "desktop_classic") -> Game:
    game = Game(profile)
    if pieces is not None:
        game.state.pieces = list(pieces)
    return game


def _render(game: Game, *, hints: bool, selected: Position | None, legal: list | None = None) -> QImage:
    board = BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", "glyph")
    board.set_assists(
        selection=True,
        legal_targets=True,
        capture_hints=True,
        animations=True,
        archer_star_hints=hints,
    )
    board.legal = list(legal or [])
    board.selected = selected
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage()


def _diff(a: QImage, b: QImage) -> int:
    return sum(
        1
        for row in range(a.height())
        for col in range(a.width())
        if a.pixelColor(col, row) != b.pixelColor(col, row)
    )


def test_board_default_is_off_and_demo_call_stays_valid(qt_app: QApplication) -> None:
    board = BoardWidget()
    assert board.show_archer_star_hints is False
    # piece_atlas.py demo 的四参数调用必须继续可用
    board.set_assists(selection=True, legal_targets=True, capture_hints=True, animations=True)
    assert board.show_archer_star_hints is False


def test_alpha_is_strictly_below_last_move(qt_app: QApplication) -> None:
    assert STAR_HINT_ALPHA == int(64 * 0.8) == 51
    assert STAR_HINT_ALPHA < 64 < 90 < 145


def test_anchor_rays_match_core_and_are_bounded(qt_app: QApplication) -> None:
    game = _game()
    board = BoardWidget()
    board.set_game(game, Color.RED, True)
    board.selected = ARCHER
    rays = board.archer_star_anchor_rays()
    assert [(anchor.row, anchor.col) for anchor, _sr, _sc in rays] == [(9, 3)]
    for source in (Position(row, col) for row in range(13) for col in range(13)):
        board.selected = source
        assert len(board.archer_star_anchor_rays()) <= 4


def test_off_state_never_enters_the_drawing_path(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """开关关时直接 early-return：连锚点换算都不做，逐像素零干扰。"""

    def _forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("关闭开关仍进入了星轨绘制路径")

    monkeypatch.setattr(BoardWidget, "archer_star_anchor_rays", _forbidden)
    game = _game()
    _render(game, hints=False, selected=ARCHER)


def test_flag_is_inert_without_a_player_selection(qt_app: QApplication) -> None:
    game = _game()
    legal = [move for move in game.rules.legal_moves(game.state) if move.source == ARCHER]
    for selected in (None, next(p.position for p in game.state.pieces if p.type is PieceType.ROOK and p.color is Color.RED)):
        off = _render(game, hints=False, selected=selected, legal=legal)
        on = _render(game, hints=True, selected=selected, legal=legal)
        assert _diff(off, on) == 0
    # 增强档（完整/轻量/精简）整层 early-return：同一选中状态，开关无效
    complete = _game(profile="desktop_complete")
    off = _render(complete, hints=False, selected=ARCHER)
    on = _render(complete, hints=True, selected=ARCHER)
    assert _diff(off, on) == 0


def test_blocked_direction_draws_solid_ray(qt_app: QApplication) -> None:
    """虚线端点≠锚点（第一步就被挡）→ 必须补画实线，不能整层吞掉。"""
    pieces = [
        Piece.create(PieceType.KING, Color.RED, 12, 6),
        Piece.create(PieceType.KING, Color.BLACK, 1, 1),
        Piece.create(PieceType.ARCHER, Color.RED, ARCHER.row, ARCHER.col),
        Piece.create(PieceType.PAWN, Color.RED, 11, 1),
    ]
    game = _game(pieces)
    off = _render(game, hints=False, selected=ARCHER)
    on = _render(game, hints=True, selected=ARCHER)
    assert _diff(off, on) > 0, "被挡方向应有 P→锚点实线 + 端点环"
