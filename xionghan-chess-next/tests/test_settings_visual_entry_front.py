"""C3 设置首屏与首跑第②步：真开窗口、真解析 DOM，不靠源码字符串。

默认值仍由 `test_piece_badges_toggle.py` / `test_high_contrast_pieces.py` 钉住；
这里只验证「找得到」：两个既有开关在首屏、引导第②步带静态徽记示意。
"""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QCheckBox  # noqa: E402

from xionghan_chess.desktop import app as app_module  # noqa: E402
from xionghan_chess.desktop.config import DEFAULTS  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import SettingsDialog  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _has_ancestor(widget: QCheckBox, ancestor: object) -> bool:
    parent = widget.parent()
    while parent is not None:
        if parent is ancestor:
            return True
        parent = parent.parent()
    return False


def test_settings_first_screen_has_both_visual_toggles(qt_app: QApplication) -> None:
    """默认设置窗口打开就在第 0 页，两个开关在这一页可见且读同一份配置。"""
    config = dict(DEFAULTS)
    config["high_contrast_pieces"] = True
    config["piece_badges"] = True
    dialog = SettingsDialog(config, None)
    dialog.show()
    qt_app.processEvents()
    try:
        first_tab = dialog.tabs.widget(0)
        assert dialog.tabs.currentIndex() == 0
        for widget in (dialog.high_contrast, dialog.piece_badges):
            assert _has_ancestor(widget, first_tab), f"{widget.objectName()} 不在首屏页面里"
            assert widget.isVisibleTo(dialog), f"{widget.objectName()} 被布局挡住了"
            assert widget.isChecked(), "开关没有读回配置"
            matches = [c for c in dialog.findChildren(QCheckBox) if c.objectName() == widget.objectName()]
            assert len(matches) == 1, "同一开关不能有两份，否则状态会分叉"
        assert not _has_ancestor(dialog.archer_star_hints, first_tab), "星轨提示不属于这次前置的入口"
    finally:
        dialog.close()


def test_desktop_onboarding_step_two_shows_badge_sample(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """三步横幅不增步数、不弹层；第②行挂一枚静态「射 ✦○」示意。"""
    monkeypatch.setattr(app_module, "save_config", lambda *_args, **_kwargs: None)
    window = app_module.MainWindow()
    try:
        window.config["onboarded"] = False
        window.maybe_show_onboarding()
        text = window.statusBar().currentMessage()
        assert all(mark in text for mark in ("①", "②", "③"))
        assert "④" not in text, "引导仍只能有三步"
        assert "✦" in text and "○" in text, text
        assert "徽记" in text or "Badge" in text, text
        assert window.config["onboarded"] is True
    finally:
        window.close()


class _DomProbe(HTMLParser):
    """只记录开始标签的顺序与祖先，不用子串猜 DOM 结构。"""

    VOID = {"input", "br", "hr", "meta", "link", "img", "source"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.events: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        info = {key: value or "" for key, value in attrs}
        self.events.append(
            {
                "tag": tag,
                "attrs": info,
                "ancestors": [(parent_tag, parent_attrs.get("id", "")) for parent_tag, parent_attrs in self.stack],
            }
        )
        if tag not in self.VOID:
            self.stack.append((tag, info))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def _events(path: Path) -> list[dict[str, object]]:
    probe = _DomProbe()
    probe.feed(path.read_text(encoding="utf-8"))
    return probe.events


def _index_by_id(events: list[dict[str, object]], element_id: str) -> int:
    found = [index for index, event in enumerate(events) if event["attrs"].get("id") == element_id]
    assert len(found) == 1, f"#{element_id} 出现 {len(found)} 次"
    return found[0]


def test_web_settings_first_fieldset_contains_both_visual_toggles() -> None:
    events = _events(ROOT / "web/index.html")
    dialog = _index_by_id(events, "settingsDialog")
    appearance = _index_by_id(events, "appearanceSettings")
    assist = _index_by_id(events, "assistSettings")
    assert dialog < appearance < assist

    for element_id in ("highContrastEnabled", "pieceBadgesEnabled"):
        index = _index_by_id(events, element_id)
        assert appearance < index < assist, f"#{element_id} 没在首屏 fieldset 里"
        ancestors = events[index]["ancestors"]
        assert ("fieldset", "appearanceSettings") in ancestors, ancestors


def test_webapp_settings_first_screen_contains_both_visual_toggles() -> None:
    events = _events(ROOT / "webapp/index.html")
    dialog = _index_by_id(events, "dlgSettings")
    headings = [
        index
        for index, event in enumerate(events)
        if event["tag"] == "h3" and event["attrs"].get("data-i18n") == "settings.appearance"
    ]
    assert headings, "找不到外观标题"
    for element_id in ("optHighContrast", "optPieceBadges"):
        index = _index_by_id(events, element_id)
        assert dialog < index < headings[0], f"#{element_id} 排在外观标题后面，不是首屏"


def test_web_onboarding_step_two_has_static_archer_badge_demo() -> None:
    events = _events(ROOT / "web/index.html")
    dialog = _index_by_id(events, "onboardDialog")
    line1 = _index_by_id(events, "onboardLine1")
    line2 = _index_by_id(events, "onboardLine2")
    demos = [
        index
        for index, event in enumerate(events)
        if "onboard-badge-demo" in str(event["attrs"].get("class", ""))
    ]
    assert len(demos) == 1, demos
    assert dialog < line1 < demos[0] < line2, "示例棋子没插在第②步前"


def test_webapp_onboarding_step_two_copy_carries_static_badge_sample() -> None:
    source = (ROOT / "webapp/js/i18n.js").read_text(encoding="utf-8")
    values = re.findall(r"'onboard\.step2':\s*'([^']*)'", source)
    assert len(values) == 2, "中英两份 step2 文案都要在"
    assert all("✦" in value and "○" in value for value in values), values
