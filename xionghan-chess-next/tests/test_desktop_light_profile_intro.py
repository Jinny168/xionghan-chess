"""2.2.0「轻量模式」预设：老用户**只提示一次**，档位与规则一律不动。

方案 A（已裁定）：不迁移 `desktop_complete` → `desktop_light`。

- 项目原则「用户的选择不再被静默替换」；
- 设置窗口保存的是 `rule_options` **全量键**，只改 profile 会被那批存量键压掉，
  产出一个「看起来换了档、规则却没变」的静默无效结果。

本文件钉住四条行为：老用户提示一次并落盘、二次启动不再提示、新装不提示、
题目态 / 观战态分别不提示。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="MainWindow 依赖 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop import config as desktop_config  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402

OLD_CONFIG = {
    "schema_version": desktop_config.CONFIG_VERSION,
    "profile": "desktop_complete",
    "language": "zh-CN",
    # 带一个非空规则键：断言提示逻辑**不碰** rule_options
    "rule_options": {"pawn_charge": False},
}


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def user_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path


@pytest.fixture()
def made(qt_app: QApplication):
    """按需造多个 MainWindow（模拟多次启动），结束时统一收尾。"""
    created: list[appmod.MainWindow] = []

    def _make() -> appmod.MainWindow:
        theme.load_bundled_fonts()
        win = appmod.MainWindow()
        win.config["language"] = "zh-CN"
        created.append(win)
        return win

    yield _make
    for win in created:
        win.timer.stop()
        win.close()
        win.deleteLater()


def _write_config(payload: dict) -> Path:
    path = desktop_config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _record_notifications(win, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(win, "notify", lambda text, level="info", timeout_ms=0: notes.append((text, level)))
    return notes


def test_complete_profile_is_told_once_and_flag_is_persisted(user_dir, made, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write_config(OLD_CONFIG)
    win = made()
    notes = _record_notifications(win, monkeypatch)

    win.maybe_introduce_light_profile()

    assert len(notes) == 1, f"应当只提示一次：{notes}"
    text, level = notes[0]
    assert level == "info"
    assert "轻量模式" in text

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["light_profile_intro_shown"] is True, "标记必须落盘，否则每次启动都弹"
    assert on_disk["profile"] == "desktop_complete", "绝不改用户档位"
    assert on_disk["rule_options"] == {"pawn_charge": False}, "不碰 rule_options"


def test_second_launch_does_not_prompt_again(user_dir, made, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_config(OLD_CONFIG)
    first = made()
    first_notes = _record_notifications(first, monkeypatch)
    first.maybe_introduce_light_profile()
    assert len(first_notes) == 1

    second = made()  # 重新从磁盘读配置，模拟再次启动
    assert second.config["light_profile_intro_shown"] is True
    second_notes = _record_notifications(second, monkeypatch)
    second.maybe_introduce_light_profile()
    assert second_notes == [], "第二次启动不该再提示"


def test_new_install_does_not_prompt(user_dir, made, monkeypatch: pytest.MonkeyPatch) -> None:
    win = made()  # 没有配置文件 → 默认 desktop_light
    assert win.config["profile"] == "desktop_light"
    notes = _record_notifications(win, monkeypatch)

    win.maybe_introduce_light_profile()

    assert notes == []
    assert win.config["light_profile_intro_shown"] is False


def test_puzzle_mode_does_not_prompt(user_dir, made, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_config(OLD_CONFIG)
    win = made()
    notes = _record_notifications(win, monkeypatch)
    win.puzzle_session = object()  # type: ignore[assignment]

    win.maybe_introduce_light_profile()

    assert notes == []
    assert win.config["light_profile_intro_shown"] is False


def test_spectating_does_not_prompt(user_dir, made, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_config(OLD_CONFIG)
    win = made()
    notes = _record_notifications(win, monkeypatch)
    win.spectating = True

    win.maybe_introduce_light_profile()

    assert notes == []
    assert win.config["light_profile_intro_shown"] is False
