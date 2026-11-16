"""复盘"分析"按钮的容器 API 回归守卫。

`ReplayDialog` 继承的是 `QDialog`，不是 `QMainWindow`。`statusBar()` /
`menuBar()` / `centralWidget()` 都是 QMainWindow-only；`self.pool` 则是主窗口
在 `__init__` 里自建的属性。对话框里误用任何一个，都是"点一下就 AttributeError"
的生产崩溃，且静态类型检查不会报（PySide6 的动态包装）。

这里守两件事：① 无 parent 注入时点分析按钮能真正跑通；② 同类误用不再出现。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

pytest.importorskip("PySide6", reason="桌面端用例依赖 PySide6")

from PySide6.QtCore import QThreadPool  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import ReplayDialog  # noqa: E402
from xionghan_chess.desktop.ui.workers import AnalysisWorker  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIALOGS = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "dialogs.py"


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _RecordingPool:
    """代替全局线程池：只记录 start，不让 40-ply 分析真跑起来。"""

    def __init__(self) -> None:
        self.started: list[object] = []

    def start(self, worker: object) -> None:
        self.started.append(worker)


def test_show_analysis_starts_worker_without_parent_injection(qt_app: QApplication, monkeypatch) -> None:
    """无 parent、无外部 shim：点分析按钮不抛，worker 入池，提示走对话框内控件。"""
    game = Game()
    for _ in range(3):
        game.move(next(iter(game.rules.legal_moves(game.state))))

    dialog = ReplayDialog(game, {"language": "zh-CN"})  # 故意不传 parent
    pool = _RecordingPool()
    monkeypatch.setattr(QThreadPool, "globalInstance", lambda: pool)

    dialog.show_analysis()  # 修复前在这里 AttributeError: 'ReplayDialog' has no attribute 'statusBar'

    assert len(pool.started) == 1
    assert isinstance(pool.started[0], AnalysisWorker)
    assert "正在分析" in dialog.info.text(), "状态提示必须落在对话框自己的 QLabel 上"
    dialog.close()


def test_no_qmainwindow_only_api_in_qdialog_classes() -> None:
    """所有 QDialog 子类里不得再出现 QMainWindow-only API 或自建 pool 引用。"""
    source = DIALOGS.read_text(encoding="utf-8")
    classes = re.findall(r"^class (\w+)\(QDialog\):([\s\S]*?)(?=^class |\Z)", source, re.M)
    assert len(classes) >= 6, "类扫描失效（QDialog 子类数量不对）"

    banned = (
        "self.statusBar(",
        "self.menuBar(",
        "self.centralWidget(",
        "self.setCentralWidget(",
        "self.addDockWidget(",
        "self.toolBar(",
        "self.pool",
    )
    offenders = [f"{name}:{token}" for name, body in classes for token in banned if token in body]
    assert not offenders, "QDialog 里误用了 QMainWindow-only API：" + "；".join(offenders)
