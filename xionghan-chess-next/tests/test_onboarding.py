"""D4 首跑引导：只出现一次，两端都要有可见出口。

桌面版**刻意不用弹窗**：任何模态/子窗口都会抢键盘焦点，把「按回车再来一局」这类
交互顶掉（实测过，会让 `test_desktop_play_again` 变红）。所以它是状态栏横幅，
这里也顺带守一条「别改回弹窗」。
"""

from __future__ import annotations

import json
from pathlib import Path

from xionghan_chess.desktop.config import DEFAULTS

ROOT = Path(__file__).resolve().parents[1]


def test_config_default_is_not_onboarded() -> None:
    assert DEFAULTS["onboarded"] is False, "新装用户应当还没看过引导"


def test_desktop_shows_a_banner_once_and_marks_itself() -> None:
    src = (ROOT / "src/xionghan_chess/desktop/app.py").read_text(encoding="utf-8")
    assert "def maybe_show_onboarding" in src
    assert "QTimer.singleShot(0, self.maybe_show_onboarding)" in src, "启动时没触发引导"

    body = src.split("def maybe_show_onboarding")[1].split("def ")[0]
    assert 'if self.config.get("onboarded")' in body, "缺少只显示一次的判断"
    assert "self.statusBar().showMessage(text,15000)" in body, "引导没有可见出口"
    assert 'self.config["onboarded"]=True' in body and "save_config(self.config)" in body, \
        "标记没落盘，重启会再显示"
    assert "QMessageBox" not in body, "别改回弹窗：子窗口会抢键盘，顶掉其它用例"


def test_web_has_the_dialog_and_the_flag() -> None:
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    for element in ('id="onboardDialog"', 'id="onboardLine1"', 'id="onboardLine2"',
                    'id="onboardLine3"', 'id="onboardStartButton"'):
        assert element in html, f"弹窗缺少 {element}"

    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    assert "function maybeShowOnboarding" in js
    assert "xh-onboarded" in js, "没有持久化键，会每次访问都弹"
    assert "maybeShowOnboarding();" in js, "初始化时没调用"
    assert "showModal()" in js


def test_web_copy_exists_in_both_languages() -> None:
    for name in ("zh-CN", "en"):
        data = json.loads((ROOT / f"locales/{name}.json").read_text(encoding="utf-8"))
        training = data.get("training", {})
        for key in ("onboard_title", "onboard_1", "onboard_2", "onboard_3", "onboard_cta"):
            assert training.get(key), f"{name} 缺少 training.{key}"
