"""几何守卫：侧栏不横溢、棋盘是正方形、对话框最小尺寸不倒退。

为什么要有这一组：这几处都是"看起来有尺寸"的坑 ——
· `setFixedWidth(188)` 把清单钉死，比"没设下限"更难查；
· `BoardWidget.sizeHint()` 返回 -1×-1（无法测量），所以**棋盘只比 w==h 与空带，不用 sizeHint**；
· 对话框改了最小尺寸却不解决可视高度，用户仍然看不全。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="几何守卫需要 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

SIZES = [(1260, 850), (1000, 700), (900, 680)]
ROOT = Path(__file__).resolve().parents[1]
DIALOGS_PY = (ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "dialogs.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    from xionghan_chess.desktop.ui import theme
    theme.load_bundled_fonts()
    return app


@pytest.fixture()
def window(qt_app: QApplication):
    from xionghan_chess.desktop.app import MainWindow
    w = MainWindow()
    w.show()
    qt_app.processEvents()
    yield w
    w.close()


def test_sidebar_never_scrolls_horizontally(window, qt_app) -> None:
    """侧栏内容宽必须 ≤ 视口宽，且横向滚动条不可见。

    这条是 `setMinimumWidth(330)` 的守卫：将来往侧栏里加更宽的控件，这里先红。
    """
    inner = window.side.widget()
    for size in SIZES:
        window.resize(*size)
        qt_app.processEvents()
        viewport = window.side.viewport().width()
        content = inner.sizeHint().width()
        assert content <= viewport, f"{size}: 内容 {content} > 视口 {viewport}（会出横向滚动条）"
        assert not window.side.horizontalScrollBar().isVisible(), f"{size}: 横向滚动条可见"


def test_board_is_square(window, qt_app) -> None:
    """棋盘控件始终是正方形（±1px）。

    注意：`BoardWidget.sizeHint()` 是 -1×-1，**不能用它做断言** —— 只比实际几何。
    """
    for size in SIZES:
        window.resize(*size)
        qt_app.processEvents()
        board = window.board
        assert abs(board.width() - board.height()) <= 1, (
            f"{size}: 棋盘 {board.width()}×{board.height()} 不是正方形")


def test_dialogs_declare_audit_minimum_sizes() -> None:
    """五个对话框的最小尺寸必须与几何审计表一致（静态断言，防止被改回去）。

    用源码断言而不是全部实例化：`HandicapDialog`/`TrainingDialog` 需要 parent 提供
    `config`，`ReplayDialog` 需要房间对象，为一个数值断言去构造整套依赖不值得。
    """
    # 权威来源：`docs/UI_GEOMETRY_AUDIT_2026-10-31.md` §3「对话框最小尺寸」表。
    # 表变了就改这里；这里变了说明实现偏离审计 —— 两边必须同步，别只改一边。
    expected = {
        "HandicapDialog": "setMinimumSize(520,480)",
        "ReplayDialog": "setMinimumSize(820,560)",
        "TrainingDialog": "setMinimumSize(560,420)",
        "GameLibraryDialog": "setMinimumSize(560,380)",
        "DocumentDialog": "setMinimumSize(420,360)",
    }
    for name, snippet in expected.items():
        block = re.search(rf"class {name}\b[\s\S]*?(?=\nclass |\Z)", DIALOGS_PY)
        assert block, f"找不到类 {name}"
        assert snippet in block.group(0), f"{name} 缺少 {snippet}"


def test_board_fills_the_limiting_dimension(window, qt_app) -> None:
    """空带只允许出现在**非限制维度**：边长 == min(容器宽, 容器高)，±1px。

    这是不变量，比任何像素阈值稳。曾写过"空带 <= 72px"，那是拍出来的数：
    1260x850 档棋盘列 890 宽、737 高，正方形顶满高度后水平空带必然是 (890-737)/2 = 76.5，
    要压到 72 只能让棋盘小于可用高度 —— 拿真实尺寸换阈值，不划算。旧阈值作废。
    """
    for size in SIZES:
        window.resize(*size)
        qt_app.processEvents()
        board, host = window.board, window._board_host
        expected = min(host.width(), host.height())
        assert abs(board.width() - expected) <= 1, (
            f"{size}: 棋盘边长 {board.width()} != 容器短边 {expected}（限制维度没顶满）")


def test_document_dialog_body_is_usable(qt_app) -> None:
    """`DocumentDialog` 能**无依赖构造**（只吃 title/content），所以在这里做真实测量。

    判据用**绝对像素 120**，不用 sizeHint 百分比：`QTextBrowser` 的 sizeHint 依赖内容，
    拿它算比例会把"内容短"误判成"布局差"。
    """
    from xionghan_chess.desktop.ui.dialogs import DocumentDialog

    dialog = DocumentDialog("t", "正文" * 200)
    dialog.resize(dialog.minimumSize())
    dialog.show()
    qt_app.processEvents()
    body = dialog.findChild(type(dialog.findChildren(type(dialog))[0])) if False else None
    from PySide6.QtWidgets import QTextBrowser
    browser = dialog.findChild(QTextBrowser)
    assert browser is not None, "DocumentDialog 里没有正文控件"
    assert browser.height() >= 120, f"最小尺寸下正文只有 {browser.height()}px"
    dialog.close()


def test_library_dialog_list_is_usable(qt_app, tmp_path) -> None:
    """`GameLibraryDialog` 只吃 (folder, config)，可无依赖构造 → 真实测量列表高度。"""
    from xionghan_chess.desktop.ui.dialogs import GameLibraryDialog

    dialog = GameLibraryDialog(tmp_path, {})
    dialog.resize(dialog.minimumSize())
    dialog.show()
    qt_app.processEvents()
    from PySide6.QtWidgets import QListWidget
    lists = dialog.findChildren(QListWidget)
    assert lists, "GameLibraryDialog 里没有列表控件"
    assert max(x.height() for x in lists) >= 120, (
        f"最小尺寸下列表最高只有 {max(x.height() for x in lists)}px")
    dialog.close()
