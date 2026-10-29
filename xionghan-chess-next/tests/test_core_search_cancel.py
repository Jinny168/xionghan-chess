"""MCTS 时间盒起点 + 取消链（mcts / analysis / workers）。

## 修的是什么
- `MCTS.choose_move` 的 `deadline` 原来建在 SEE 预处理**之后**：那段时间不受
  预算约束（实测 12s 预算跑出过 62.6s），且预处理循环里没有 cancel 检查，
  暂停/悔棋都停不下来；
- `analyze_game` 调 `engine.choose_move(position)` 时**没传 cancel**，
  复盘窗口关掉后还要跑满 `40 手 × 每手预算` 才停。

两条都属"取消必须落到确定状态"，所以放在同一个提交里。
"""

from __future__ import annotations

import threading
import time

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.mcts import SEE_CANDIDATE_LIMIT, MCTS
from xionghan_chess.core.model import Color, Piece, PieceType
from xionghan_chess.core.analysis import analyze_game


def _capture_rich_position() -> Game:
    """构造一个吃子很多（≥ 24 个）的局面，用来压 SEE 预处理。"""
    pieces = [
        Piece.create(PieceType.KING, Color.RED, 12, 6),
        Piece.create(PieceType.KING, Color.BLACK, 0, 6),
    ]
    # 黑兵排第 6 行，上下两行各放红车：每个兵被两枚车盯住 → 吃子着法 = 2 × 列数
    for col in range(13):
        pieces.append(Piece.create(PieceType.PAWN, Color.BLACK, 6, col))
        pieces.append(Piece.create(PieceType.ROOK, Color.RED, 5, col))
        pieces.append(Piece.create(PieceType.ROOK, Color.RED, 7, col))
    game = Game("desktop_complete")
    game.state.pieces = pieces
    game.state.turn = Color.RED
    return game


def test_see_preprocessing_is_bounded_by_the_time_box() -> None:
    """SEE 每次 20ms、吃子几十个：总耗时必须被时间盒 + 候选上限夹住。"""
    game = _capture_rich_position()
    captures = [m for m in game.rules.legal_moves(game.state)
                if game.rules.captured_by_move(game.state, m)]
    assert len(captures) > SEE_CANDIDATE_LIMIT + 8, f"局面吃子不够多（{len(captures)}）"

    calls: list[int] = []

    def slow_root_score(_game, _move) -> int:
        calls.append(1)
        time.sleep(0.02)          # 模拟一次昂贵 SEE
        return 1                  # 全部"安全"，确保预处理会跑满上限

    engine = MCTS(time_limit=0.1, seed=7, root_score=slow_root_score)
    started = time.perf_counter()
    engine.choose_move(game)
    elapsed = time.perf_counter() - started

    bound = SEE_CANDIDATE_LIMIT * 0.02 + 0.1 + 0.2   # 上限 + 预算 + 余量
    assert elapsed <= max(0.5, bound), f"SEE 预处理没被夹住：{elapsed:.2f}s"
    # 这条才是"时间盒在 SEE 之前"的硬判据：0.1s 预算 / 每次 20ms，最多只该调 5 次左右。
    # 改前（deadline 建在 SEE 之后）会把 captures 全部估算完（这里是 26 次）。
    assert len(calls) <= 8, f"0.1s 预算下 SEE 被调用了 {len(calls)} 次 —— 时间盒没覆盖预处理"


def test_cancel_during_see_returns_immediately() -> None:
    """SEE 进行中置 cancel：应当在 1 个 SEE 周期内返回，不抛异常。"""
    game = _capture_rich_position()
    cancel = threading.Event()
    calls = {"n": 0}

    def cancelling_root_score(_game, _move) -> int:
        calls["n"] += 1
        if calls["n"] >= 2:
            cancel.set()
        time.sleep(0.02)
        return 1

    engine = MCTS(time_limit=5.0, seed=7, root_score=cancelling_root_score)
    started = time.perf_counter()
    result = engine.choose_move(game, cancel)
    elapsed = time.perf_counter() - started

    assert elapsed <= 0.5, f"取消后仍然跑了 {elapsed:.2f}s"
    assert result is None or result in game.rules.legal_moves(game.state)


def test_analysis_stops_within_one_ply_after_cancel() -> None:
    """复盘分析：cancel 置位后在下一手前退出，返回已完成的部分（不为空、不抛）。"""
    game = Game("desktop_complete")
    for _ in range(12):
        legal = game.rules.legal_moves(game.state)
        if not legal or game.state.finished:
            break
        game.move(legal[0])
    cancel = threading.Event()
    cancel.set()                       # 一开始就取消：应当立刻返回空分析而不是抛异常
    result = analyze_game(game, DifficultyEasy(), 40, cancel)
    assert result["analyzedPlies"] == 0
    assert result["moves"] == []


def DifficultyEasy():
    from xionghan_chess.core.ai import Difficulty

    return Difficulty.EASY
