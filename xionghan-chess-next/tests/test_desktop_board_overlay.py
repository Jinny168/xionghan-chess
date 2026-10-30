"""棋盘遮罩与走子动画的**绘制顺序**（P1-2）。

## 修的是什么

`human_move` 落子后立刻 `start_ai()`，于是玩家自己那一手的 350 ms 动画**全程**处在
`locked=True`（「棋灵思考中」遮罩）之下。原来 `paintEvent` 把遮罩画在动画之后，
遮罩的 90-alpha 深色把动画压住 —— 玩家看到的是「我落子没反馈、AI 落子有反馈」。

修法只调顺序：遮罩提到**棋子之后、动画之前**。遮罩本身的颜色/文案/透明度一个字没改。

## 为什么用「动画环」取样

动画环（`_draw_animation` 的椭圆）在 `animation_frame=0` 时 `progress=0`，
画笔 alpha 是 `1 - progress = 1.0`、半径 `0.25 × cell`、笔宽 5 —— 环上任意一点都是
**纯色 `#315c48`**（非吃子）。于是判据可以写成「该像素 == 纯色」：
遮罩若压在动画上面，这个像素必然被深色混过、不等于纯色。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType, Position  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import BoardWidget  # noqa: E402

SIZE = 620
RING_COLOR = QColor("#315c48").getRgb()


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render(*, locked: bool, paused: bool = False) -> tuple[QImage, BoardWidget]:
    game = Game("web")
    game.state.pieces = [Piece.create(PieceType.ROOK, Color.RED, 6, 6)]
    board = BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", "glyph")
    board.interactive = False
    board.animation_source = Position(6, 6)
    board.animation_target = Position(7, 7)
    board.animation_frame = 0      # progress=0 → 环是纯色，便于取样
    board.animation_capture = False
    board.game.state.paused = paused
    board.locked = locked
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage(), board


def ring_pixel(image: QImage, board: BoardWidget) -> tuple[int, int, int, int]:
    """动画环上的一点（目标格中心向右 0.25 cell）。"""
    _rect, left, top, cw, _ch = board._geometry()
    center_x = left + 7 * cw
    center_y = top + 7 * cw
    return image.pixelColor(int(center_x) + round(0.25 * cw), int(center_y)).getRgb()


def board_pixel(image: QImage, board: BoardWidget) -> tuple[int, int, int, int]:
    """盘面上一块没有棋子/动画的区域（棋盘内缩 20px 处）。"""
    _rect, left, top, _cw, _ch = board._geometry()
    return image.pixelColor(int(left) + 20, int(top) + 20).getRgb()


def test_animation_is_drawn_above_the_thinking_mask(qt_app: QApplication) -> None:
    """锁盘（思考中）时，动画环仍是**纯色**，没有被遮罩混过。"""
    locked_image, board = render(locked=True)
    unlocked_image, _ = render(locked=False)
    assert ring_pixel(locked_image, board) == RING_COLOR, "动画被「思考中」遮罩压住了"
    assert ring_pixel(locked_image, board) == ring_pixel(unlocked_image, board), \
        "锁盘与不锁盘的动画像素应当一致"


def test_thinking_mask_still_dims_the_board(qt_app: QApplication) -> None:
    """只调顺序，不许把遮罩调没了：盘面像素必须仍被压暗。"""
    locked_image, board = render(locked=True)
    unlocked_image, _ = render(locked=False)
    locked_board = board_pixel(locked_image, board)
    unlocked_board = board_pixel(unlocked_image, board)
    assert locked_board != unlocked_board, "遮罩没有生效"
    assert sum(locked_board[:3]) < sum(unlocked_board[:3]), "遮罩应变暗而不是变亮"


def test_pause_overlay_stays_on_top(qt_app: QApplication) -> None:
    """暂停遮罩仍然盖住一切（含动画）—— 暂停是「停下」，不该露出动画。"""
    paused_image, board = render(locked=False, paused=True)
    assert ring_pixel(paused_image, board) != RING_COLOR, "暂停遮罩应当压在动画之上"


# ---------------------------------------------------------------------------
# 落子指示的时长：550ms / 16ms（原来 350ms / 25ms，肉眼只有 ~9 帧）
# ---------------------------------------------------------------------------
def test_animation_duration_is_about_450ms(qt_app: QApplication) -> None:
    """23 帧 × 20ms = 460ms：够看清落子方向，又落在单帧 20ms 预算内。

    取这一档而不是 550ms/16ms，是因为实测 900×900 单帧 max 14.3ms（超 12ms 掉帧线）、
    1470px p95 已 16.2ms —— 20ms 定时器下两个尺寸都在预算内。
    """
    from xionghan_chess.desktop.ui.board_widget import ANIMATION_FRAMES, ANIMATION_TIMER_MS

    assert ANIMATION_TIMER_MS == 20
    duration = ANIMATION_FRAMES * ANIMATION_TIMER_MS
    assert 420 <= duration <= 500, f"落子指示时长 {duration}ms 不在 460±40 内"
    assert duration > 350, "时长必须比改前的 350ms 更久（原来只有 ~9 个可见帧）"


def test_animation_stops_after_the_last_frame(qt_app: QApplication) -> None:
    """跑满帧数后必须清掉动画状态；脉冲走完后定时器必须停（不得常驻）。"""
    from xionghan_chess.desktop.ui.board_widget import (
        ANIMATION_FRAMES, CHECK_PULSE_FRAMES, BoardWidget as Widget,
    )

    game = Game("web")
    board = Widget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.animations_enabled = True
    board.animation_source = Position(6, 6)
    board.animation_target = Position(5, 6)
    board.animation_frame = 0
    board.animation_timer.start()
    for _ in range(max(ANIMATION_FRAMES, CHECK_PULSE_FRAMES) + 2):
        board._advance_animation()
    assert board.animation_target is None and board.animation_source is None
    assert not board.animation_timer.isActive(), "动画结束后定时器必须停"
