"""A3 星级：只罚「错着」与「提示」，不奖励速度。

解法是唯一强制线，不存在"更短的走法"，所以星级不衡量快慢，只衡量
"这一题有多少是你自己想出来的"。
"""

from __future__ import annotations

from pathlib import Path

from xionghan_chess.core.model import Move, Position
from xionghan_chess.core.puzzles import Puzzle, load_puzzles
from xionghan_chess.desktop import training

ROOT = Path(__file__).resolve().parents[1]


def _puzzle(steps: tuple[Move, ...]) -> Puzzle:
    base = load_puzzles()[0]
    return Puzzle("t-1", "测试题", "beginner", "描述", base.document, steps, ("提示一", "提示二"), ())


def _mv(sr: int, sc: int, tr: int, tc: int) -> Move:
    return Move(Position(sr, sc), Position(tr, tc))


STEPS = (_mv(8, 4, 7, 4), _mv(4, 4, 5, 4), _mv(7, 4, 6, 4))


def _solve_cleanly(session: training.PuzzleSession) -> None:
    for index, move in enumerate(STEPS):
        if index % 2 == 0:
            session.submit(move)
        else:
            session.advance_auto()


def test_unsolved_scores_zero() -> None:
    session = training.PuzzleSession(_puzzle(STEPS))
    assert session.stars == 0


def test_clean_solve_scores_three() -> None:
    session = training.PuzzleSession(_puzzle(STEPS))
    _solve_cleanly(session)
    assert session.solved and session.stars == 3


def test_one_miss_or_one_hint_drops_to_two() -> None:
    missed = training.PuzzleSession(_puzzle(STEPS))
    missed.submit(_mv(0, 0, 1, 0))          # 错一手
    _solve_cleanly(missed)
    assert missed.stars == 2

    hinted = training.PuzzleSession(_puzzle(STEPS))
    hinted.next_hint()                       # 看一次提示
    _solve_cleanly(hinted)
    assert hinted.stars == 2


def test_three_penalties_drop_to_one() -> None:
    session = training.PuzzleSession(_puzzle(STEPS))
    for _ in range(2):
        session.submit(_mv(0, 0, 1, 0))
    session.next_hint()
    _solve_cleanly(session)
    assert session.stars == 1


def test_web_mirrors_the_same_rule() -> None:
    """网页端同构：计数用 misses/hints，公式必须与 Python 一致。"""
    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    assert "function puzzleStars(session)" in js
    assert "penalty===0?3:(penalty<=2?2:1)" in js, "网页星级公式与 Python 不一致"
    assert "session.misses=(session.misses||0)+1" in js, "网页没在判错时计数"
    assert "app.puzzleSession.hints=" in js, "网页没在提示时计数"
