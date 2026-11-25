"""P1-11 侧栏折叠分组的行为契约。

## 挡的是什么

折叠框本身很好写，问题都出在**边界**上：

1. 收起时用 `setFixedHeight(0)` / 改 minimumHeight 之类"顺手"的写法，会把侧栏整体
   重算一遍 —— 棋盘被挤小一个格子。这条最难在肉眼上发现（只是"看起来小了点"），
   所以用**折叠前后棋盘与侧栏像素宽度逐字节相等**来钉。
2. 折叠状态写进配置文件 —— 新增一条存储通道、换机器不同步、还要处理旧配置迁移。
   P1-11 明确不持久化。
3. 标题重复出现两次（原来那行 QLabel 没删干净）。

## 口径

宽度断言在两个尺寸下各跑一次（默认 1260×850 与最小 900×680）：只在默认尺寸成立
的"不变"没有意义，布局挤压恰恰发生在最小尺寸。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="折叠框是 Qt 控件")

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.collapsible import CollapsibleBox  # noqa: E402

DEFAULT_SIZE = (1260, 850)
MIN_SIZE = (900, 680)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    """真实 MainWindow + 干净用户目录（配置写到 tmp，不污染本机）。"""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.show()
    qt_app.processEvents()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_default_state_is_collapsed(window) -> None:
    """阵亡子力默认收起：首屏把高度让给棋谱。"""
    assert not window.captured_box.is_expanded
    assert not window.captured_box.content.isVisible()


def test_clicking_the_header_expands_and_collapses(window) -> None:
    """点标题展开、再点收起（走的是真实 clicked 信号，不是直接改属性）。"""
    box = window.captured_box
    box.header.click()
    assert box.is_expanded
    assert box.content.isVisible(), "展开后内容仍不可见 —— setVisible 没接上"

    box.header.click()
    assert not box.is_expanded
    assert not box.content.isVisible()


def test_header_title_is_the_old_small_heading(window) -> None:
    """标题就地复用原来的「阵亡子力」，不重复出现两次。"""
    assert window.captured_box.title == "阵亡子力"
    labels = [w.text() for w in window.side.widget().findChildren(QLabel) if w.text() == "阵亡子力"]
    assert labels == [], "旧的小标题 QLabel 还在，标题会重复显示两次"


@pytest.mark.parametrize("size", (DEFAULT_SIZE, MIN_SIZE))
def test_toggling_never_shrinks_the_board(window, qt_app: QApplication, size: tuple[int, int]) -> None:
    """折叠前后棋盘宽度与侧栏宽度**像素级不变**。

    这是 P1-11 的硬契约「不缩棋盘」：折叠只改可见性，不许改任何尺寸。
    """
    window.resize(*size)
    qt_app.processEvents()
    before_board, before_side = window.board.width(), window.side.width()

    window.captured_box.header.click()
    qt_app.processEvents()
    assert window.board.width() == before_board, f"{size} 展开后棋盘宽度变了：{before_board} → {window.board.width()}"
    assert window.side.width() == before_side, f"{size} 展开后侧栏宽度变了：{before_side} → {window.side.width()}"

    window.captured_box.header.click()
    qt_app.processEvents()
    assert window.board.width() == before_board, f"{size} 收起后棋盘宽度变了：{before_board} → {window.board.width()}"
    assert window.side.width() == before_side, f"{size} 收起后侧栏宽度变了：{before_side} → {window.side.width()}"


def test_side_stays_pinned_to_330(window) -> None:
    """侧栏那对写死的 330 没被动过（折叠框挂在它里面的布局上，不该反向影响它）。"""
    assert window.side.minimumWidth() == 330
    assert window.side.maximumWidth() == 330


def test_collapsible_box_standalone(qt_app: QApplication) -> None:
    """离屏单测：构造参数与 `set_content_layout` 的替换语义。

    注意别断言 `label.parent() is box.content`：Qt 的父子关系在**布局激活**时才
    落到子控件上（未显示的窗口里 parent 仍是 None）。断言"容器换了、布局挂对了、
    旧容器被丢弃"，这些不依赖激活时机。
    """
    box = CollapsibleBox("测试分组", expanded=True)
    first = QLabel("一")
    box.add_widget(first)
    assert box.is_expanded
    assert box.content.isVisibleTo(box)

    from PySide6.QtWidgets import QVBoxLayout

    old_content = box.content
    replacement = QVBoxLayout()
    replacement.addWidget(QLabel("二"))
    box.set_content_layout(replacement)
    assert box.content is not old_content, "set_content_layout 没有换容器"
    assert box.content.layout() is replacement
    assert replacement.parent() is box.content

    box.set_expanded(False)
    assert not box.content.isVisibleTo(box)
    box.deleteLater()
