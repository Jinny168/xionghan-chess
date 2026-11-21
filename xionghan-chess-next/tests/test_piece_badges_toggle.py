"""特色子形状徽记开关（VA-14，I 批）门禁。

## 口径

徽记偏好 `pieceBadges`（web 旧树 / webapp）/ `piece_badges`（桌面）**默认 false**：
棋子本身有文字称呼，不再用图形重复标识。开启能力保留，用户可自行打开。

本文件盯四件事：
1. **默认关**：三端默认值均为 false；桌面棋盘初始 `show_badges=False`。
2. **关闭零残留**：关闭态三条绘制路径早退，不留环/星描边、空占位或半透明残影。
3. **不覆盖主题与风格**：开关只控制徽记叠加，不改已选主题 / 棋子风格；纯本地偏好，
   不进桌面云同步映射。
4. **链路接通**：偏好 → 视图 → 绘制三端各自闭环，开启后徽记仍达既有几何口径
   （几何间隙由 `test_badge_clearance.py` 复算）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="桌面断言依赖 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop import config as settings  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import BoardWidget  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _board() -> BoardWidget:
    board = BoardWidget()
    board.set_game(Game("desktop_complete"), Color.RED, True)
    board.set_appearance("classic", "none", "traditional", "glyph")
    return board


# ---------------------------------------------------------------------------
# 1. 默认关
# ---------------------------------------------------------------------------
def test_desktop_default_off() -> None:
    """桌面配置默认 `piece_badges=False`，棋盘初始不画徽记。"""
    assert settings.DEFAULTS["piece_badges"] is False


def test_desktop_board_default_off(qt_app: QApplication) -> None:
    board = _board()
    assert board.show_badges is False


def test_webapp_default_off() -> None:
    app_js = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
    assert "pieceBadges: false" in app_js, "webapp DEFAULT_PREFS 徽记必须默认 false"


def test_web_default_off() -> None:
    app_js = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    assert "pieceBadges:false" in app_js, "web 旧树 preferences 徽记必须默认 false"


# ---------------------------------------------------------------------------
# 2. 关闭零残留：早退分支包裹徽记绘制，且早退发生在描边 / 保存画布状态之前
# ---------------------------------------------------------------------------
def test_desktop_early_return_in_badge_helper() -> None:
    widget = (ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "board_widget.py").read_text(
        encoding="utf-8"
    )
    # helper 入口早退：enabled=False 时直接 return，不进入 save / stroke / draw 分支。
    assert "if not enabled:\n        return" in widget
    # 类内三条路径（字形 / 位图 / 缺图回退）都把开关透传成 self.show_badges。
    assert widget.count("self.show_badges") >= 3


def test_web_early_return_before_save() -> None:
    app_js = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    badge = app_js[app_js.index("function specialBadge("):]
    body = badge[: badge.index("ctx.save()")]
    assert "app.preferences.pieceBadges!==true)return" in body, (
        "web 旧树徽记必须在 ctx.save() 之前早退，关闭态不留描边 / 残影"
    )


def test_webapp_badge_call_wrapped_in_gate() -> None:
    board_js = (ROOT / "webapp" / "js" / "ui" / "board.js").read_text(encoding="utf-8")
    assert "if (view.pieceBadges === true)" in board_js
    # 徽记调用必须落在该 gate 块内（闸门行先于 drawSpecialBadge 调用）。
    gate = board_js.index("if (view.pieceBadges === true)")
    call = board_js.index("this.drawSpecialBadge(")
    assert gate < call


# ---------------------------------------------------------------------------
# 3. 开关不覆盖主题 / 风格；纯本地，不进云同步映射
# ---------------------------------------------------------------------------
def test_desktop_switch_keeps_theme_and_style(qt_app: QApplication) -> None:
    board = _board()
    before_theme, before_style = board.theme_name, board.piece_style
    board.set_assists(
        selection=True,
        legal_targets=True,
        capture_hints=True,
        animations=True,
        piece_badges=True,
    )
    assert board.show_badges is True
    assert board.theme_name == before_theme == "classic"
    assert board.piece_style == before_style == "traditional"


def test_desktop_pref_not_cloud_synced() -> None:
    """`piece_badges` 是纯本地偏好，不进桌面云同步偏好映射（同 high_contrast 体例）。"""
    app_py = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")
    # 两次 captureHints 映射区段之间不含本地徽记键（纯本地，不进云同步）。
    first = app_py.index('"captureHints"')
    second = app_py.index('"captureHints"', first + 1)
    mapping_region = app_py[first:second]
    assert "piece_badges" not in mapping_region


# ---------------------------------------------------------------------------
# 4. 链路接通：偏好 → 控件 / 回填 / 视图 → 绘制
# ---------------------------------------------------------------------------
def test_webapp_chain_wired() -> None:
    app_js = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
    board_js = (ROOT / "webapp" / "js" / "ui" / "board.js").read_text(encoding="utf-8")
    assert 'id="optPieceBadges"' in html
    assert "optPieceBadges" in app_js  # onchange 写 prefs
    # 三处视图组装都要带 pieceBadges 字段。
    assert app_js.count("pieceBadges: app.prefs.pieceBadges === true") == 3
    # 偏好回填勾选态。
    assert "$('#optPieceBadges').checked = app.prefs.pieceBadges === true" in app_js
    assert "view.pieceBadges" in board_js


def test_web_chain_wired() -> None:
    app_js = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="pieceBadgesEnabled"' in html
    assert "['pieceBadgesEnabled','pieceBadges']" in app_js  # 勾选 → 偏好映射
    assert "$('#pieceBadgesEnabled').checked=p.pieceBadges===true" in app_js  # 回填
    assert "app.preferences.pieceBadges" in app_js


def test_desktop_chain_wired() -> None:
    dialogs = (ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "dialogs.py").read_text(
        encoding="utf-8"
    )
    app_py = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")
    assert "self.piece_badges" in dialogs  # 控件 + 回填 + 落盘映射
    assert '"piece_badges": self.piece_badges.isChecked()' in dialogs
    assert "piece_badges=self.config.get(\"piece_badges\", False)" in app_py
