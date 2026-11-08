"""射的对角路径预览：虚线、端点、方向数与开关。

## 这条能力解决什么

可走点只回答"能停哪几格"，回答不了"为什么第五格走不过去"。射是斜向滑行 + 每步
不能夹 + 最近星位限距，单看圆点分不清「被子挡住」还是「到头了」。所以补一条
弱化的虚线：从射的中心连到**最远可停格**，被挡住时在最后一格与障碍之间加一个
短横标记。

## 判据为什么都按"有无路径像素"

线是 `.35` 透明度的虚线，绝对值会随主题/DPI 漂；而"这一处有没有线"是稳定判据：
把「选中 + 开落点提示」与「未选中」两帧逐像素比对，差异只可能来自
选中环、可走点、路径线 —— 取样点刻意选在**两个可走点之间的空隙**，
于是差异只可能来自路径线。
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

SIZE = 900
ARCHER = Position(12, 0)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def build(pieces: list[Piece] | None = None) -> tuple[Game, list]:
    game = Game("desktop_complete")
    if pieces is not None:
        game.state.pieces = list(pieces)
    archer = next(piece for piece in game.state.pieces if piece.position == ARCHER)
    legal = [move for move in game.rules.legal_moves(game.state) if move.source == ARCHER]
    return game, legal


def render(game: Game, legal: list, *, selected: Position | None,
           show: bool = True) -> tuple[QImage, BoardWidget]:
    board = BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", "glyph")
    board.legal = list(legal)
    board.selected = selected
    board.show_legal_targets = show
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage(), board


def probe(board: BoardWidget, source: Position, step_row: int, step_col: int,
          cells: float) -> tuple[int, int]:
    """从 `source` 沿 (step_row, step_col) 走 `cells` 格处的像素坐标。"""
    _rect, left, top, cw, ch = board._geometry()
    shown = board._view_position(source)
    return (int(left + shown.col * cw + step_col * cells * cw),
            int(top + shown.row * ch + step_row * cells * ch))


def has_ink(marked: QImage, plain: QImage, x: int, y: int, span: int = 3) -> bool:
    """`(x, y)` 周围 `span` 像素内是否存在两帧差异（= 那里画了东西）。"""
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            if marked.pixelColor(x + dx, y + dy) != plain.pixelColor(x + dx, y + dy):
                return True
    return False


# ---------------------------------------------------------------------------
# 1) 不越界：障碍格与其外一格不得有路径像素
# ---------------------------------------------------------------------------
def test_path_stops_before_the_blocker(qt_app: QApplication) -> None:
    """在 (10,2) 放一枚己方子：最远可停格变成 (11,1)，线不得越过它。"""
    game, _ = build([
        Piece.create(PieceType.KING, Color.RED, 12, 6),
        Piece.create(PieceType.KING, Color.BLACK, 1, 1),   # 不能与红帅同列（会"照面"→无合法着法）
        Piece.create(PieceType.ARCHER, Color.RED, ARCHER.row, ARCHER.col),
        Piece.create(PieceType.PAWN, Color.RED, 10, 2),      # 挡在斜线上
        Piece.create(PieceType.PAWN, Color.RED, 8, 4),       # 阻挡之后的格子
    ])
    legal = [move for move in game.rules.legal_moves(game.state) if move.source == ARCHER]
    assert legal and max(legal, key=lambda m: abs(m.target.row - ARCHER.row)).target == Position(11, 1)

    marked, board = render(game, legal, selected=ARCHER)
    plain, _ = render(game, legal, selected=None)
    # 终点之后 0.4 格（仍在通往障碍格的路上）：不该有线
    x, y = probe(board, Position(11, 1), -1, 1, 0.4)
    assert not has_ink(marked, plain, x, y), "线越过最远可停格，画到了障碍格方向"
    # 障碍格再外一格（8,4）：更不该有
    x, y = probe(board, Position(10, 2), -1, 1, 0.6)
    assert not has_ink(marked, plain, x, y), "线越过了障碍格"


# ---------------------------------------------------------------------------
# 2) 端点对齐：线端 = 最远可走点
# ---------------------------------------------------------------------------
def test_path_endpoint_is_the_farthest_legal_target(qt_app: QApplication) -> None:
    game, legal = build()
    rays = BoardWidget().archer_rays()
    marked, board = render(game, legal, selected=ARCHER)
    plain, _ = render(game, legal, selected=None)

    board.archer_rays()  # 仅为触发一致性检查
    board.selected = ARCHER
    board.show_legal_targets = True
    board.legal = legal
    (source, farthest, _obstacle, step_row, step_col), = board.archer_rays()
    assert source == ARCHER
    assert farthest == max(legal, key=lambda move: abs(move.target.row - ARCHER.row)).target

    before = probe(board, ARCHER, step_row, step_col, 2.2)      # 终点前 0.8 格
    assert has_ink(marked, plain, *before), "终点前应当有路径线"
    beyond = probe(board, farthest, step_row, step_col, 0.35)   # 沿射线方向再走 0.35 格
    assert not has_ink(marked, plain, *beyond), "线越过了最远可走点"


# ---------------------------------------------------------------------------
# 3) 方向数：初始局面只有"右上"一条
# ---------------------------------------------------------------------------
def test_only_the_open_direction_gets_a_path(qt_app: QApplication) -> None:
    game, legal = build()
    marked, board = render(game, legal, selected=ARCHER)
    plain, _ = render(game, legal, selected=None)
    for step_row, step_col, label in ((-1, 1, "右上"), (-1, -1, "左上"),
                                      (1, 1, "右下"), (1, -1, "左下")):
        x, y = probe(board, ARCHER, step_row, step_col, 0.6)
        drawn = has_ink(marked, plain, x, y)
        if (step_row, step_col) == (-1, 1):
            assert drawn, f"{label}方向有落点，应当画线"
        else:
            assert not drawn, f"{label}方向没有落点，不应当画线"


# ---------------------------------------------------------------------------
# 4) 关闭落点提示即消失
# ---------------------------------------------------------------------------
def test_path_disappears_when_targets_are_off(qt_app: QApplication) -> None:
    game, legal = build()
    open_marks, board = render(game, legal, selected=ARCHER)
    closed_marks, _ = render(game, legal, selected=ARCHER, show=False)
    plain, _ = render(game, legal, selected=None, show=False)
    x, y = probe(board, ARCHER, -1, 1, 0.6)
    assert has_ink(open_marks, plain, x, y), "开启时应画线"
    assert not has_ink(closed_marks, plain, x, y), "关闭落点提示后不应残留路径线"
