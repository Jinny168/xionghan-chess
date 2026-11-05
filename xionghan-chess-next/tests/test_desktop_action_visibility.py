"""侧栏操作按钮的**可见性**：由规则决定，不由对局状态决定。

## 为什么要单独守这条

「置灰」和「隐藏」是两件不同的事，而两者的差别**没有任何现有测试能看出来**：
- 置灰：按钮还在、还能被读屏念出来、还能点（点下去弹错）；
- 隐藏：按钮不在布局里，也不在无障碍树里。

2.0.0 的验收口径是：`pawn_resurrection` 关掉后，侧栏**只剩 6 个按钮**，
而且**无障碍树里也没有第七个** —— 只 `setEnabled(False)` 是不合格的。
这条测试就是那个口径，防止以后有人图省事把"隐藏"悄悄改回"置灰"。

顺带守一条反向自检：`UI_ACTION_REQUIRES` 里登记的每个动作，在对应开关关掉时
**core 入口必须真的拒绝**。否则哪天 core 放宽了（比如复活不再依赖开关），
表还在替它隐藏一个合法动作 —— 两边静默脱钩，谁也不知道。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game, GameError  # noqa: E402
from xionghan_chess.core.model import Color, Position  # noqa: E402
from xionghan_chess.core.profiles import (UI_ACTION_REQUIRES,  # noqa: E402
                                          RuleOptions)
from xionghan_chess.desktop import config as settings  # noqa: E402
from xionghan_chess.desktop.app import MainWindow  # noqa: E402

# 侧栏一共七个按钮（构造时按顺序注册，见 `MainWindow._build` 的 `specs`）
SIDEBAR_BUTTONS = ("undo", "pause", "resign", "draw", "resurrect", "flip", "again")


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(qt_app, monkeypatch, tmp_path):
    """**必须隔离 APPDATA**，否则这条测试会污染开发者的真实配置。

    `MainWindow.new_game()` 会调 `save_config`，而它是在 `app.py` 里 `from .config
    import save_config` 拿到的 —— 直接 patch `config.save_config` **拦不住**它。
    本文件第一版就踩了这个坑：跑完之后 `%APPDATA%/XionghanChess/settings.json` 里的
    `profile` 被写成 `desktop_classic`，紧接着 `test_desktop_layout_limits` 里
    新建的窗口就少了一个按钮、宽度断言直接红。
    """
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from xionghan_chess.desktop import app as app_module

    monkeypatch.setattr(app_module, "save_config", lambda *_a, **_k: None)
    monkeypatch.setattr(settings, "save_config", lambda *_a, **_k: None)
    win = MainWindow()
    win.show()
    qt_app.processEvents()
    yield win
    win.close()


def _visible_buttons(window) -> list[str]:
    """真正"看得见"的按钮名。`isVisibleTo(window)` 才是会被无障碍树暴露的那一批，
    `isVisible()` 在窗口未 show 时恒为 False，容易写出假绿。"""
    return [kind for button, kind in window._action_buttons if button.isVisibleTo(window)]


def test_resurrection_on_keeps_all_seven_buttons(window) -> None:
    window.config["profile"] = "desktop_complete"
    window.new_game()
    window.refresh()
    assert window.game.options.pawn_resurrection is True
    assert _visible_buttons(window) == list(SIDEBAR_BUTTONS)
    assert window.resurrect_action.isVisible(), "菜单项也该跟着规则走"


def test_resurrection_off_leaves_six_buttons_and_no_seventh_in_the_a11y_tree(window) -> None:
    window.config["profile"] = "desktop_classic"      # 经典模式：pawn_resurrection=False
    window.new_game()
    window.refresh()
    assert window.game.options.pawn_resurrection is False

    assert _visible_buttons(window) == [k for k in SIDEBAR_BUTTONS if k != "resurrect"], \
        "关掉复活后侧栏应只剩 6 个按钮"
    # 无障碍树：Qt 不会把 isVisibleTo() 为假的控件交给辅助技术。
    # 只 `setEnabled(False)` 的话这里会是 True —— 那正是本条要拦的写法。
    assert not window.resurrect.isVisibleTo(window), "复活按钮仍在无障碍树里（只是被置灰/藏起来？）"
    assert not window.resurrect_action.isVisible(), "菜单项「复活兵卒」也得消失"


def _probe_resurrect(options: RuleOptions) -> None:
    """`resurrect` 动作在 core 的入口：开关关掉时必须抛错。"""
    game = Game("desktop_complete",
                option_overrides={"pawn_resurrection": options.pawn_resurrection})
    game.resurrect_pawn(Color.RED, Position(8, 0))


# 动作 → 它的 core 入口探针。新增一条 `UI_ACTION_REQUIRES` 就必须在这里登记探针，
# 否则下面的测试会因为缺项而红（这是故意的：没有探针就无法反向自检）。
ACTION_PROBES = {"resurrect": _probe_resurrect}


def test_every_declared_action_is_really_blocked_by_core() -> None:
    assert set(UI_ACTION_REQUIRES) <= set(ACTION_PROBES), \
        f"这些动作没有登记 core 探针：{sorted(set(UI_ACTION_REQUIRES) - set(ACTION_PROBES))}"
    for action, parents in UI_ACTION_REQUIRES.items():
        off = RuleOptions(**{parent: False for parent in parents})
        with pytest.raises(GameError):
            ACTION_PROBES[action](off)
