"""`_root` 局部结果保留 + 无超时路径逐位不变。"""

from __future__ import annotations

import time

from xionghan_chess.core.ai import ChessAI, SearchConfig
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType

# 战术局面：红車 5,0 可吃黑車 5,4，根着法少、排序便宜，适合做确定性基线。
SPECS = [
    (PieceType.KING, Color.RED, 9, 4),
    (PieceType.ROOK, Color.RED, 5, 0),
    (PieceType.CANNON, Color.RED, 7, 1),
    (PieceType.KING, Color.BLACK, 0, 4),
    (PieceType.ROOK, Color.BLACK, 5, 4),
    (PieceType.PAWN, Color.BLACK, 4, 0),
    (PieceType.HORSE, Color.BLACK, 0, 1),
]


def _game() -> Game:
    state = GameState(
        "traditional",
        [Piece.create(*spec) for spec in SPECS],
        turn=Color.RED,
    )
    return Game.from_state(state)


def test_partial_root_results_survive_timeout(monkeypatch) -> None:
    """cap 超时时，已跑完的根着法不许全丢：completed_depth>=1 且 root_scores 非空。

    真实 13×13 上 0.05s 连前缀都跑不完（fix 2 会按时抛 wall）；这里用 4 个根着法
    的战术局面 + 0.03s/根的假 `_search`，精确复现「第一根完成后超时」的场景。
    修前：超时穿出 `_root`，scores 全丢 → completed_depth=0、返回排序首着。
    修后：保留已完成根，按原「残缺根不夺标」规则返回。
    """
    cfg = SearchConfig(
        depth=1,
        time_limit=0.05,
        randomness=0.0,
        quiescence_depth=0,
        candidate_count=4,
        branch_limit=2,
        root_limit=5,
    )

    def slow_search(self, *args, **kwargs):
        time.sleep(0.03)
        return 0.0

    monkeypatch.setattr(ChessAI, "_search", slow_search)
    ai = ChessAI("medium", seed=123, config=cfg)
    game = _game()
    move = ai.choose_move(game)

    assert move is not None
    assert ai.completed_depth >= 1
    assert ai.root_scores, "超时前完成的根着法必须保留"
    legal = {item.key() for item in game.rules.legal_moves(game.state)}
    assert all(root_move.key() in legal for _, root_move, _ in ai.root_scores)


def test_no_timeout_selection_and_scores_are_bit_identical() -> None:
    """无超时路径：选点与 root_scores 必须与修前基线逐位一致。

    基线由修改前 HEAD 实测（tactical 局面、seed=123、d2/30s/root5）。
    """
    cfg = SearchConfig(
        depth=2,
        time_limit=30.0,
        randomness=0.0,
        quiescence_depth=2,
        candidate_count=5,
        branch_limit=10,
        root_limit=5,
    )
    ai = ChessAI("medium", seed=123, config=cfg)
    move = ai.choose_move(_game())

    assert move is not None and move.key() == "5,0-5,4"
    assert ai.completed_depth == 2
    assert ai.bound_reason is None
    assert [(round(score, 6), item.key(), truncated) for score, item, truncated in ai.root_scores] == [
        (857.367021, "5,0-5,4", False),
        (857.367021, "9,4-9,3", False),
        (857.367021, "9,4-9,5", False),
        (857.367021, "7,1-7,4", False),
    ]
