"""开关极性：界面一律「勾选 = 这枚子更强」，负向存储键在显示/写回时取反。

三条负向键的历史来源：它们的 `True` 描述的是"少了一种能力"——
出宫后**失去**斜走 / 马**受**别腿限制 / 直走三格**不可**吃子。
只改呈现不改存储，老配置与存档照旧可用。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.core.profiles import (
    NEGATED_OPTIONS,
    RuleOptions,
    display_value,
    stored_value,
)

ROOT = Path(__file__).resolve().parents[1]
ABOUT = ROOT / "src" / "xionghan_chess" / "desktop" / "resources" / "docs" / "ABOUT.md"


def test_negated_set_is_exactly_the_three_nerf_keys() -> None:
    assert NEGATED_OPTIONS == {
        "king_lose_diagonal_outside_palace",
        "horse_blocked_by_leg",
        "horse_straight_three_move_only",
    }
    # 每个键都必须是真实规则项，防止拼错后静默失效
    for key in NEGATED_OPTIONS:
        assert key in RuleOptions.__dataclass_fields__


@pytest.mark.parametrize("key", sorted(NEGATED_OPTIONS | {"pawn_charge", "horse_straight_three"}))
def test_display_and_stored_are_inverses(key: str) -> None:
    for stored in (True, False):
        assert stored_value(key, display_value(key, stored)) is stored


def test_only_the_three_nerf_keys_are_inverted() -> None:
    assert display_value("horse_blocked_by_leg", True) is False
    assert display_value("horse_blocked_by_leg", False) is True
    # 正向键原样透传
    assert display_value("pawn_charge", True) is True
    assert display_value("pawn_charge", False) is False


# --- 桌面设置对话框 -------------------------------------------------------

@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PySide6", reason="桌面端依赖 PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _dialog(profile: str):
    from xionghan_chess.desktop.config import load_config
    from xionghan_chess.desktop.ui.dialogs import SettingsDialog
    config = load_config()
    config["profile"] = profile
    return SettingsDialog(config)


def test_classic_profile_shows_leg_blocking_as_unchecked(qt_app) -> None:
    """经典模式存储 `horse_blocked_by_leg=True`（受限制）→ 勾选应显示为**未勾**。"""
    dialog = _dialog("desktop_classic")
    assert dialog.checks["horse_blocked_by_leg"].isChecked() is False
    # 取消限制 = 勾上，写回后存储值应为 False
    dialog.checks["horse_blocked_by_leg"].setChecked(True)
    assert dialog.value()["rule_options"]["horse_blocked_by_leg"] is False
    dialog.deleteLater()


def test_complete_profile_shows_no_leg_blocking_as_checked(qt_app) -> None:
    dialog = _dialog("desktop_complete")
    assert dialog.checks["horse_blocked_by_leg"].isChecked() is True
    dialog.checks["horse_blocked_by_leg"].setChecked(False)
    assert dialog.value()["rule_options"]["horse_blocked_by_leg"] is True
    dialog.deleteLater()


def test_positive_options_keep_their_direction(qt_app) -> None:
    """正向键不受影响：完整模式三连吃子开着 → 勾选；关掉后存储为 False。"""
    dialog = _dialog("desktop_complete")
    assert dialog.checks["pawn_three_line_capture"].isChecked() is True
    dialog.checks["pawn_three_line_capture"].setChecked(False)
    assert dialog.value()["rule_options"]["pawn_three_line_capture"] is False
    dialog.deleteLater()


# --- 关于文档与 API 版本 --------------------------------------------------

def test_about_doc_has_no_hardcoded_version() -> None:
    text = ABOUT.read_text(encoding="utf-8")
    assert "{{VERSION}}" in text, "关于文档应使用占位符，由运行时注入当前版本"
    assert not re.search(r"版本：\d+\.\d+\.\d+", text), "关于文档里又写死了版本号"


def test_api_version_tracks_package_version() -> None:
    import xionghan_chess
    from xionghan_chess.service.app import app

    assert app.version == xionghan_chess.__version__


def test_profiles_endpoint_reports_negated_options() -> None:
    from fastapi.testclient import TestClient
    from xionghan_chess.service.app import app

    with TestClient(app) as client:
        profiles = client.get("/api/profiles").json()
    for profile in profiles:
        assert set(profile["negatedOptions"]) == set(NEGATED_OPTIONS)
