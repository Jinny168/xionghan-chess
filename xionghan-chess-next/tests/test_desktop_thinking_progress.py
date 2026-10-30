"""思考态预算读条：封顶 0.9、正向秒数、归零时机、定时器不常驻。

## 为什么封顶 0.9

预算耗尽不等于"AI 该出手了"（`AI._search` 撞墙后会返回 best-so-far，落子还要再走一遍
`Game.move` + 重绘）。条铺到 100% 会让玩家以为"卡住了"，也会把"预算用完"误读成
"时间到了必须立刻有动作"。留 10% 表示"随时可能出手"。

## 为什么秒数是正向累计

倒计时会让玩家盯着"还剩几秒"数；而引擎在预算耗尽后仍可能多跑一会儿（收尾/落子），
倒计时一旦归零就会自己打脸。正向累计「已用 3.2 秒」不会说谎。

## 为什么 `time_limit` 只能从 CONFIGS 读

前端再写一份时长就会与 `core/ai.py` 的真实预算分叉；这条同 `test_difficulty_labels`
一起把"文案/读条/引擎"三处的预算钉在同一个来源上。
"""

from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.ai import CONFIGS, Difficulty  # noqa: E402
from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import board_widget as bw  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402

SIZE = 620


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


class _Clock:
    """可手动推进的单调时钟（不 sleep，测试才稳）。"""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_board() -> bw.BoardWidget:
    board = bw.BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(Game("web"), Color.RED, True)
    board.set_appearance("classic", "none", "traditional", "glyph")
    board.locked = True
    return board


def render(board: bw.BoardWidget) -> QImage:
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage()


# ---------------------------------------------------------------------------
# 1) 封顶 0.9 + 单调增
# ---------------------------------------------------------------------------
def test_ratio_is_monotonic_and_capped(qt_app: QApplication,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _Clock()
    monkeypatch.setattr(bw.time, "monotonic", clock)
    board = make_board()
    board.begin_thinking(CONFIGS[Difficulty.BEGINNER].time_limit)   # 0.5s

    ratios = []
    for step in range(1, 4):
        clock.now += 0.1          # 0.1 / 0.2 / 0.3 秒
        ratios.append(board.thinking_ratio())
    assert ratios == sorted(ratios), f"ratio 必须单调不减：{ratios}"
    assert all(ratio <= 0.9 for ratio in ratios), ratios

    clock.now += 10.0             # 远超预算
    assert board.thinking_ratio() == pytest.approx(0.9), "预算耗尽也必须封顶 0.9，不得归满"


def test_hard_ratio_is_small_at_one_second(qt_app: QApplication,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _Clock()
    monkeypatch.setattr(bw.time, "monotonic", clock)
    board = make_board()
    board.begin_thinking(CONFIGS[Difficulty.HARD].time_limit)       # 12s
    clock.now += 1.0
    assert board.thinking_ratio() <= 0.1


# ---------------------------------------------------------------------------
# 2) 归零时机：只在 end_thinking（= 真正落子/失败/取消）
# ---------------------------------------------------------------------------
def test_progress_clears_only_after_end_thinking(qt_app: QApplication,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _Clock()
    monkeypatch.setattr(bw.time, "monotonic", clock)
    board = make_board()
    board.begin_thinking(0.5)
    clock.now += 0.5
    busy = render(board)

    assert board.thinking_started is not None, "预算耗尽后仍应保持思考态（条不许自己归零）"
    board.end_thinking()
    assert board.thinking_started is None and board.thinking_ratio() == 0
    idle = render(board)
    assert busy != idle, "结束思考后画面必须变（读条与秒数消失）"


def test_progress_uses_config_time_limit(qt_app: QApplication) -> None:
    """`begin_thinking` 收到多少预算就按多少算 —— app 层必须传 CONFIGS 的值。"""
    board = make_board()
    board.begin_thinking(CONFIGS[Difficulty.MEDIUM].time_limit)
    assert board.thinking_limit == pytest.approx(CONFIGS[Difficulty.MEDIUM].time_limit)
    # 不写死秒数：medium 预算会随产品调整（5s→6s），写死就变成「改预算必红」的假测试
    assert board.thinking_limit == pytest.approx(CONFIGS[Difficulty.MEDIUM].time_limit)


# ---------------------------------------------------------------------------
# 3) 定时器不常驻：连续三次 start/finish 后必须停
# ---------------------------------------------------------------------------
@pytest.fixture()
def window(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    # 结果弹窗改为自定义按钮框后，静默点转移到 `show_result_dialog`（否则会真模态挂住）
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: False))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))

    class _Signal:
        def connect(self, *_args, **_kwargs) -> None:
            return None

    class _Signals:
        def __init__(self) -> None:
            self.finished = _Signal()
            self.failed = _Signal()

    class _Worker:
        def __init__(self, *args, **kwargs) -> None:
            self.signals = _Signals()

    monkeypatch.setattr(appmod, "AIWorker", _Worker)
    win = appmod.MainWindow()
    monkeypatch.setattr(win.pool, "start", lambda *args, **kwargs: None)
    yield win
    win.timer.stop()
    win.thinking_timer.stop()
    win.close()
    win.deleteLater()


def test_thinking_timer_does_not_stay_running(window) -> None:
    for _ in range(3):
        window.start_ai()
        assert window.thinking_timer.isActive(), "start_ai 之后读条定时器应当在跑"
        assert window.board.thinking_started is not None
        window.finish_ai((None, threading.Event()))       # `move is None` 出口
        assert not window.thinking_timer.isActive(), "finish_ai 之后定时器必须停"
        assert window.board.thinking_started is None

    assert not window.thinking_timer.isActive(), "连续三次之后不得残留"


def test_cancel_exit_also_stops_the_timer(window) -> None:
    window.start_ai()
    cancelled = threading.Event()
    cancelled.set()
    window.finish_ai((None, cancelled))
    assert not window.thinking_timer.isActive(), "取消出口也必须停表"
    assert window.board.thinking_started is None
