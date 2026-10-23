"""训练模式判定单测（阶段2 S2-7 配套）。

`TrainingDialog` 原本只把题面载入成普通对局，`Puzzle.solution` 从未被读过 ——
玩家走任意一步都没反馈。`desktop/training.py` 补上判定，本文件锁住它的语义。

不依赖 PySide6：判定是纯状态机，界面只负责翻译结论。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from xionghan_chess.core.model import Move, Position
from xionghan_chess.core.puzzles import Puzzle, load_puzzles
from xionghan_chess.desktop import training


def _puzzle(steps: tuple[Move, ...] = (), hints: tuple[str, ...] = ("提示一", "提示二")) -> Puzzle:
    """造一个最小题目：只看解法与提示，`document` 用真实题库的一条顶上。"""
    base = load_puzzles()[0]
    return Puzzle("t-1", "测试题", "beginner", "描述", base.document, steps, hints, ())


def _mv(sr: int, sc: int, tr: int, tc: int) -> Move:
    return Move(Position(sr, sc), Position(tr, tc))


def test_correct_move_advances_and_reports_solved_for_single_step() -> None:
    session = training.PuzzleSession(_puzzle((_mv(8, 4, 7, 4),)))
    assert session.expected is not None
    assert session.submit(_mv(8, 4, 7, 4)) == training.VERDICT_SOLVED
    assert session.solved
    assert session.expected is None


def test_wrong_move_counts_attempt_but_does_not_advance() -> None:
    session = training.PuzzleSession(_puzzle((_mv(8, 4, 7, 4),)))
    assert session.submit(_mv(8, 0, 7, 0)) == training.VERDICT_WRONG
    assert session.attempts == 1
    assert session.cursor == 0
    assert not session.solved


def test_multi_step_needs_every_step_in_order() -> None:
    steps = (_mv(8, 4, 7, 4), _mv(4, 4, 5, 4))
    session = training.PuzzleSession(_puzzle(steps))
    assert session.submit(steps[1]) == training.VERDICT_WRONG   # 顺序错也算错
    assert session.submit(steps[0]) == training.VERDICT_CORRECT
    assert session.cursor == 1 and not session.solved
    assert session.submit(steps[1]) == training.VERDICT_SOLVED


def test_submit_after_solved_is_idempotent() -> None:
    """过关后继续走棋不该抛异常，也不该把 attempts 弄脏。"""
    session = training.PuzzleSession(_puzzle((_mv(8, 4, 7, 4),)))
    session.submit(_mv(8, 4, 7, 4))
    assert session.submit(_mv(1, 1, 2, 2)) == training.VERDICT_SOLVED
    assert session.attempts == 0


def test_promotion_field_is_ignored() -> None:
    """玩家走兵到底线会带上 promotion，而解法里从不写 —— 按整对象比会把正解判错。"""
    from xionghan_chess.core.model import PieceType

    session = training.PuzzleSession(_puzzle((_mv(1, 4, 0, 4),)))
    assert session.submit(Move(Position(1, 4), Position(0, 4), PieceType.ROOK)) == training.VERDICT_SOLVED


def test_hint_escalates_with_attempts_and_then_sticks() -> None:
    session = training.PuzzleSession(_puzzle((_mv(8, 4, 7, 4),), hints=("一", "二")))
    assert session.next_hint() == "一"       # 还没错，先给第一条
    session.submit(_mv(0, 0, 0, 1))
    assert session.next_hint() == "一"       # 错 1 次仍给第一条
    session.submit(_mv(0, 0, 0, 1))
    assert session.next_hint() == "二"       # 错 2 次给第二条
    session.submit(_mv(0, 0, 0, 1))
    assert session.next_hint() == "二"       # 到底后不无限加码


def test_hint_empty_when_puzzle_has_none() -> None:
    session = training.PuzzleSession(_puzzle((_mv(8, 4, 7, 4),), hints=()))
    assert session.next_hint() == ""


def test_session_for_none_means_not_training() -> None:
    assert training.session_for(None) is None
    puzzle = _puzzle((_mv(8, 4, 7, 4),))
    session = training.session_for(puzzle)
    assert isinstance(session, training.PuzzleSession) and session.puzzle is puzzle


@pytest.mark.parametrize("index", range(len(load_puzzles())))
def test_every_built_in_puzzle_accepts_its_own_first_solution(index: int) -> None:
    """真实题库逐条过一遍：题目的解法首着必须被自己的判定认作正确。

    这条能挡住一类很难发现的错位：判定的坐标口径与题库的坐标口径不一致
    （比如行列颠倒），此时所有题都会「怎么走都错」。
    """
    puzzles = load_puzzles()
    puzzle = puzzles[index]
    session = training.PuzzleSession(puzzle)
    verdict = session.submit(puzzle.solution[0])
    assert verdict in (training.VERDICT_CORRECT, training.VERDICT_SOLVED)
    assert session.cursor == 1


def test_training_module_has_no_qt_dependency() -> None:
    tree = ast.parse(Path(training.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "PySide6" not in imported, imported
