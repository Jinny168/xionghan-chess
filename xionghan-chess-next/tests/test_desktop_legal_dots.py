"""可走点（空位落点）的可见性与边界。

## 两条判据

1. **可见性**：点色与棋盘底色的**绿通道差 ≥ 40**。低于 40 在 13×13 上基本看不见。
   这条判据是有来历的：深色主题旧做法（深绿 `#315c48` @.72 混在 `#34302b` 上）
   绿差只有 **+32**，一律不达标 —— 那不是新回归，是存量问题。
2. **不越界**：有子阻挡处不得出现可走点。点画多了等于骗玩家"这格能走"。

颜色按主题取（浅色四主题用该主题 accent、深色用浅灰绿 `#9fbfa8`），
`board.legal_dot_color()` 是唯一来源，这里直接读它做混合，避免"量渲染像素"时
被格线颜色干扰（点正好压在格线交点上）。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Move, Piece, PieceType, Position  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import BoardWidget  # noqa: E402

SIZE = 620
THEMES = ("classic", "green", "blue", "purple", "dark")


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def make_board(theme_name: str, pieces: list[Piece], legal: list[Move] | None = None) -> BoardWidget:
    game = Game("desktop_complete")
    game.state.pieces = list(pieces)
    board = BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance(theme_name, "none", "traditional", "glyph")
    board.legal = list(legal or [])
    board.show_legal_targets = True
    return board


def render(board: BoardWidget) -> QImage:
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage()


def centre(board: BoardWidget, position: Position) -> tuple[int, int]:
    _rect, left, top, cw, _ch = board._geometry()
    shown = board._view_position(position)
    return int(left + shown.col * cw), int(top + shown.row * cw)


# ---------------------------------------------------------------------------
# 1) 可见性：点色 vs 盘底色 的绿通道差
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("theme_name", THEMES)
def test_legal_dot_contrast_on_every_theme(qt_app: QApplication, theme_name: str) -> None:
    board = make_board(theme_name, [Piece.create(PieceType.KING, Color.RED, 11, 6)])
    dot = board.legal_dot_color()
    board_background = QColor(theme.THEMES[theme_name]["board"])

    alpha = dot.alphaF()
    blended_green = alpha * dot.green() + (1 - alpha) * board_background.green()
    delta = abs(blended_green - board_background.green())
    assert delta >= 40, (
        f"{theme_name}: 点色 {dot.getRgb()} 混到盘底 {board_background.name()} 上，"
        f"绿通道只差 {delta:.0f}（要求 ≥40）")


def test_dark_theme_dot_is_lighter_not_redder(qt_app: QApplication) -> None:
    """深色主题的点必须是**浅灰绿**：不能让 red 通道压过 green（否则像可吃红叉）。"""
    board = make_board("dark", [Piece.create(PieceType.KING, Color.RED, 11, 6)])
    dot = board.legal_dot_color()
    assert (dot.red(), dot.green(), dot.blue()) == (0x9F, 0xBF, 0xA8)
    assert dot.green() > dot.red(), "深色主题的点应是灰绿，不应偏红"


# ---------------------------------------------------------------------------
# 2) 不越界：有子阻挡处不得画点
# ---------------------------------------------------------------------------
def test_no_dot_beyond_a_blocker(qt_app: QApplication) -> None:
    """车在 (行6,列6)，同列 (行4,列6) 有己方兵挡路：

    可达 (行5,列6)；(行3,列6) 与 (行1,列6) 在阻挡之后，必须没有点。
    （注意坐标系是 `Position(row, col)`，车沿**列**移动。）
    """
    pieces = [
        Piece.create(PieceType.KING, Color.RED, 11, 6),
        Piece.create(PieceType.KING, Color.BLACK, 1, 1),
        Piece.create(PieceType.ROOK, Color.RED, 6, 6),
        Piece.create(PieceType.PAWN, Color.RED, 4, 6),   # 挡路的己方兵
    ]
    game = Game("desktop_complete")
    game.state.pieces = list(pieces)
    reachable = game.rules.legal_moves(game.state)
    legal = [move for move in reachable if move.source == Position(6, 6)]
    assert legal, "构造的局面里车应当有可走格"

    board = make_board("classic", pieces, legal)
    with_dots = render(board)
    board.legal = []
    without_dots = render(board)

    def has_dot(position: Position) -> bool:
        x, y = centre(board, position)
        return with_dots.pixelColor(x, y) != without_dots.pixelColor(x, y)

    assert has_dot(Position(5, 6)), "(行5,列6) 无人阻挡，应当有点"
    assert not has_dot(Position(3, 6)), "(行3,列6) 被己方兵挡住，不该有点"
    assert not has_dot(Position(1, 6)), "(行1,列6) 在阻挡之后，不该有点"
    assert all(move.target != Position(3, 6) for move in legal)


# ---------------------------------------------------------------------------
# 3) 选中时，可走点所在格的星位刻线必须藏起来
# ---------------------------------------------------------------------------
def _tick_pixel(image: QImage, board: BoardWidget, position: Position) -> tuple[int, int, int, int]:
    """星位刻线**外端**的取样点：距格心 0.17 cell 的对角方向。

    可走点半径是 0.13 cell，这个位置在圆外，所以像素只反映"有没有刻线"。
    """
    _rect, left, top, cw, ch = board._geometry()
    shown = board._view_position(position)
    offset = 0.17 * min(cw, ch)
    return image.pixelColor(int(left + shown.col * cw + offset),
                            int(top + shown.row * ch + offset)).getRgb()


def test_star_ticks_are_hidden_under_legal_targets(qt_app: QApplication) -> None:
    """射的最远落点恰好是星位：不藏刻线的话，那一格会变成"一个星号"。

    验收两条：选中时**没有**刻线；取消选中后刻线**回来**（防止永久删掉）。
    """
    game = Game("desktop_complete")
    archer = next(piece for piece in game.state.pieces
                  if piece.type is PieceType.ARCHER and piece.color is Color.RED
                  and piece.position.col == 0)
    legal = [move for move in game.rules.legal_moves(game.state) if move.source == archer.position]
    stars = game.rules.archer_star_points
    on_star = [move.target for move in legal if move.target in stars]
    assert on_star, "这个局面里射的最远落点应当正好落在星位上"

    board = make_board("classic", game.state.pieces, legal)
    board.selected = archer.position
    selected = render(board)
    board.selected = None
    restored = render(board)

    target = on_star[0]
    assert _tick_pixel(selected, board, target) != _tick_pixel(restored, board, target), \
        "选中时该格的星位刻线应当被隐藏"
    # 控制组：另一个星位（不是可走点）刻线必须还在
    other = next(point for point in sorted(stars) if point not in {move.target for move in legal})
    assert _tick_pixel(selected, board, other) == _tick_pixel(restored, board, other), \
        "不相干的星位不该被隐藏"


# ---------------------------------------------------------------------------
# 3) 选中时，可走点所在格的星位刻线必须藏起来
# ---------------------------------------------------------------------------
def _tick_pixel(image: QImage, board: BoardWidget, position: Position) -> tuple[int, int, int, int]:
    """星位刻线**外端**的取样点：距格心 0.17 cell 的对角方向。

    可走点半径是 0.13 cell，这个位置在圆外，所以像素只反映"有没有刻线"。
    """
    _rect, left, top, cw, ch = board._geometry()
    shown = board._view_position(position)
    offset = 0.17 * min(cw, ch)
    return image.pixelColor(int(left + shown.col * cw + offset),
                            int(top + shown.row * ch + offset)).getRgb()


def test_star_ticks_are_hidden_under_legal_targets(qt_app: QApplication) -> None:
    """射的最远落点恰好是星位：不藏刻线的话，那一格会变成"一个星号"。

    验收两条：选中时**没有**刻线；取消选中后刻线**回来**（防止永久删掉）。
    """
    game = Game("desktop_complete")
    archer = next(piece for piece in game.state.pieces
                  if piece.type is PieceType.ARCHER and piece.color is Color.RED
                  and piece.position.col == 0)
    legal = [move for move in game.rules.legal_moves(game.state) if move.source == archer.position]
    stars = game.rules.archer_star_points
    on_star = [move.target for move in legal if move.target in stars]
    assert on_star, "这个局面里射的最远落点应当正好落在星位上"

    board = make_board("classic", game.state.pieces, legal)
    board.selected = archer.position
    selected = render(board)
    board.selected = None
    restored = render(board)

    target = on_star[0]
    assert _tick_pixel(selected, board, target) != _tick_pixel(restored, board, target), \
        "选中时该格的星位刻线应当被隐藏"
    # 控制组：另一个星位（不是可走点）刻线必须还在
    other = next(point for point in sorted(stars) if point not in {move.target for move in legal})
    assert _tick_pixel(selected, board, other) == _tick_pixel(restored, board, other), \
        "不相干的星位不该被隐藏"


# ---------------------------------------------------------------------------
# 4) 半径按主题取值：浅色 0.13 / 深色 0.15
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("theme_name", THEMES)
def test_dot_radius_per_theme(qt_app: QApplication, theme_name: str) -> None:
    """逐主题核对半径 —— 不要只测一个代表。

    深色主题单独放大是**对比度补偿**：`#9fbfa8@.60` 在 `#34302b` 上绿通道差 +86 虽然达标，
    但深底上小面积色块的显眼度还取决于面积。所有棋子仍然同尺寸（只是深色档整体大一档），
    所以这不是"只让射显眼"。
    """
    from xionghan_chess.desktop.ui.board_widget import LEGAL_DOT_RATIO, LEGAL_DOT_RATIO_DARK

    board = make_board(theme_name, [Piece.create(PieceType.KING, Color.RED, 11, 6)])
    expected = LEGAL_DOT_RATIO_DARK if theme_name == "dark" else LEGAL_DOT_RATIO
    assert board.legal_dot_ratio() == pytest.approx(expected), (
        f"{theme_name} 的可走点半径应为 {expected}，实际 {board.legal_dot_ratio()}")
    assert expected == pytest.approx(0.15 if theme_name == "dark" else 0.13)
