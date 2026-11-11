"""两种「吃子提示」不许混成一个（展示层护栏）。

## 为什么要有这个文件

`captured_by_move` 回答的是「**这一步会吃掉哪些子**」，而"落点可吃"问的是
「**点哪一格能吃掉它站着的那枚子**」。三连吃子是 **away-from-target** 吃法：
被吃的子不在落点上（一格行军时最多隔两格，多格行军时正好在落点正前方）。

两个前端都曾经把 `captured_by_move` 的位置集合**整个**当成"落点可吃"来画，
于是红叉落在了棋子根本去不了的格子上 —— 用户报的「兵长途行军，落点被标成可吃、
但规则并不允许吃子」就是这一条。

现在两边都拆成两个集合，语义各自独立：
- `capturable` / `capturesOnLanding` —— **落点可吃**（`captured.position == move.target`），实心叉；
- `victims` / `capturesAway` —— **旁吃受害者**（`captured.position != move.target`），空心圈。

本文件盯三件事：
1. 引擎层：多格位移与超长线都不再产出吃子（R1/R2 的正例已在 `test_three_line_capture.py`）；
2. 服务层：`/legal` 的 `capturesOnLanding` 必须落在自己的 `moves` 里，且与 `capturesAway` 不相交；
3. 桌面层：`_select` 算出的两个集合与上面同一口径。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType, Position
from xionghan_chess.core.profiles import RULE_VERSION
from xionghan_chess.service import app as service
from xionghan_chess.service.app import app


def pc(kind: str, color: Color, row: int, col: int) -> Piece:
    return Piece.create(PieceType(kind), color, row, col)


# 黑王放 (0,4)：红王在 (11,6)，避免开局就照面。
KINGS = (pc(PieceType.KING, Color.RED, 11, 6), pc(PieceType.KING, Color.BLACK, 0, 4))

# 红兵 (6,4) 前进一格到 (5,4)，与 (5,5) 我兵、(5,6) 黑士成三连 → 吃 (5,6)。
# (5,6) 既不在落点上，也不是任何合法落点 —— 这正是 away-from-target 的形态。
AWAY_BOARD = [
    *KINGS,
    pc(PieceType.PAWN, Color.RED, 6, 4),
    pc(PieceType.PAWN, Color.RED, 5, 5),
    pc(PieceType.ADVISOR, Color.BLACK, 5, 6),
]

# 红兵 (8,4) 快速行军 3 格落到 (5,4)，路径全空；落点同一列前方 (4,4) 是黑马。
# 修复前：这一步会触发三连吃子，(4,4) 被画成"可吃"，可兵永远落不到 (4,4)。
MARCH_BOARD = [
    *KINGS,
    pc(PieceType.PAWN, Color.RED, 8, 4),
    pc(PieceType.ROOK, Color.RED, 3, 4),
    pc(PieceType.HORSE, Color.BLACK, 4, 4),
]


def _room_with(client: TestClient, pieces: list[Piece]) -> tuple[str, str]:
    """开一间 offline 房间，把棋盘替换成给定局面。"""
    created = client.post(
        "/api/rooms",
        json={"ruleVersion": RULE_VERSION, "profileId": "web", "mode": "local", "playerName": "本机玩家"},
    ).json()
    room_id, token = created["roomId"], created["token"]
    room = service.manager.require(room_id)
    state = GameState("web", list(pieces), turn=Color.RED, captured={Color.RED: [], Color.BLACK: []})
    room.game.state.pieces = list(state.pieces)
    room.game.state.turn = Color.RED
    return room_id, token


def _legal(client: TestClient, room_id: str, token: str, row: int, col: int) -> dict:
    response = client.get(
        f"/api/rooms/{room_id}/legal", headers={"X-Room-Token": token}, params={"row": row, "col": col}
    )
    assert response.status_code == 200
    return response.json()


def _key(item: dict) -> tuple[int, int]:
    return item["row"], item["col"]


def test_legal_endpoint_keeps_landing_and_away_captures_apart() -> None:
    """`/legal` 必须把"落点可吃"和"旁吃受害者"分开下发，且三个字段自洽。"""
    with TestClient(app) as client:
        room_id, token = _room_with(client, AWAY_BOARD)
        payload = _legal(client, room_id, token, 6, 4)

        moves = {_key(m) for m in payload["moves"]}
        on_landing = {_key(m) for m in payload["capturesOnLanding"]}
        away = {_key(m) for m in payload["capturesAway"]}
        union = {_key(m) for m in payload["captures"]}

        assert on_landing <= moves, "落点可吃必须在自己的合法落点里"
        assert on_landing.isdisjoint(away), "两个集合语义互斥"
        assert union == on_landing | away, "captures 保留为并集（棋子图谱等按受害者格读它）"
        # 本例是三连旁吃：(5,6) 只在 away 里，不在任何落点上
        assert (5, 6) in away
        assert (5, 6) not in on_landing
        assert (5, 6) not in moves


def test_fast_march_reports_no_capture_hint_at_all() -> None:
    """用户报的那个局面：3 格行军不再挂任何吃子提示（R1 修好后的终态）。"""
    with TestClient(app) as client:
        room_id, token = _room_with(client, MARCH_BOARD)
        payload = _legal(client, room_id, token, 8, 4)

        moves = {_key(m) for m in payload["moves"]}
        assert (5, 4) in moves, "3 格快速行军应当仍可走"
        assert payload["capturesOnLanding"] == []
        assert payload["capturesAway"] == []
        assert payload["captures"] == []
        # 兵永远落不到 (4,4)，那里不该出现任何吃子提示
        assert (4, 4) not in {_key(m) for m in payload["captures"]}


# ---------------------------------------------------------------------------
# 桌面端：`_select` 算出的两个集合与端点同一口径
# ---------------------------------------------------------------------------
pyqt = pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import BoardWidget  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _board(qt_app: QApplication, pieces: list[Piece]) -> BoardWidget:
    game = Game("desktop_complete")
    game.state.pieces = list(pieces)
    board = BoardWidget()
    board.set_game(game, Color.RED, True)
    theme.load_bundled_fonts()
    board.set_appearance("classic", "none", "traditional", "glyph")
    board.show_legal_targets = True
    board.show_capture_hints = True
    return board


def test_desktop_marks_away_capture_as_victim_not_as_landing(qt_app: QApplication) -> None:
    """三连旁吃的被吃子进 `victims`（空心圈），不进 `capturable`（实心叉）。"""
    board = _board(qt_app, AWAY_BOARD)
    board._select(Position(6, 4))

    assert board.capturable == set(), "三连是旁吃，落点上没有可吃的子"
    assert board.victims == {Position(5, 6)}, "被吃的子应作为受害者标出"


def test_desktop_fast_march_shows_no_capture_hint(qt_app: QApplication) -> None:
    """用户报的局面：多格行军的落点与落点正前方都不得出现吃子提示。"""
    board = _board(qt_app, MARCH_BOARD)
    board._select(Position(8, 4))

    assert {m.target for m in board.legal} >= {Position(5, 4), Position(6, 4), Position(7, 4)}
    assert board.capturable == set()
    assert board.victims == set()
    assert Position(4, 4) not in board.capturable | board.victims


def test_desktop_direct_capture_still_lands_in_capturable(qt_app: QApplication) -> None:
    """直接吃子（落点有敌子）照旧进 `capturable` —— R3 不许把正常吃子弄丢。"""
    board = _board(
        qt_app,
        [
            *KINGS,
            pc(PieceType.PAWN, Color.RED, 6, 4),
            pc(PieceType.HORSE, Color.BLACK, 5, 4),
        ],
    )
    board._select(Position(6, 4))

    assert board.capturable == {Position(5, 4)}
    assert board.victims == set()
    # 「落点有敌子」的盘面标记仍由 `piece_at(move.target)` 负责，与本集合无冲突
    assert board.game.state.piece_at(Position(5, 4)) is not None
