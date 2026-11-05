"""C2 两段式提示：先指子、再指招。

直接给整句等于替玩家想完；第一段只说"用哪枚子"，能把他按到正确的那几行上，
落点仍要自己找。两端必须同构 —— 桌面 `PuzzleSession.staged_hint` 与网页
`#puzzleHintButton` 的 handler 走同一套两段。
"""

from __future__ import annotations

from pathlib import Path

from xionghan_chess.core.model import Move, Position
from xionghan_chess.core.puzzles import Puzzle, load_puzzles, piece_type_at
from xionghan_chess.desktop import training

ROOT = Path(__file__).resolve().parents[1]
STEPS = (Move(Position(8, 4), Position(7, 4)), Move(Position(4, 4), Position(5, 4)),
         Move(Position(7, 4), Position(6, 4)))


def _puzzle() -> Puzzle:
    base = load_puzzles()[0]
    return Puzzle("t-1", "测试题", "beginner", "描述", base.document, STEPS,
                  ("第一手提示", "第二手提示"), ())


def test_first_hint_points_at_the_piece_not_the_move() -> None:
    session = training.PuzzleSession(_puzzle())
    kind, text = session.staged_hint()
    assert kind == "piece", "第一段必须先指子"
    assert text, "指子这一步没给出子力类型"


def test_second_hint_gives_the_move_text() -> None:
    session = training.PuzzleSession(_puzzle())
    session.staged_hint()
    kind, text = session.staged_hint()
    assert kind == "move"
    assert text == "第一手提示"


def test_hint_stage_resets_after_a_correct_move() -> None:
    """换到下一手要重新从"指子"开始 —— 否则第二手会直接给走法。"""
    session = training.PuzzleSession(_puzzle())
    session.staged_hint()
    session.staged_hint()
    session.submit(STEPS[0])
    assert session.staged_hint()[0] == "piece"


def test_hints_cost_stars() -> None:
    """两段都看 = 两次扣分；这题仍然只算 2 星（penalty 2）。"""
    session = training.PuzzleSession(_puzzle())
    session.staged_hint()
    session.staged_hint()
    for index, move in enumerate(STEPS):
        if index % 2 == 0:
            session.submit(move)
        else:
            session.advance_auto()
    assert session.solved
    assert session.stars == 2


def test_piece_type_at_reads_the_document_without_rebuilding() -> None:
    puzzle = _puzzle()
    first = puzzle.solution[0]
    assert piece_type_at(puzzle, first.source) is not None

    occupied = {(piece["row"], piece["col"])
                for piece in puzzle.document["state"]["pieces"]}
    empty = next((Position(r, c) for r in range(13) for c in range(13)
                  if (r, c) not in occupied), None)
    assert empty is not None, "整盘都摆满了，这条断言失去意义"
    assert piece_type_at(puzzle, empty) is None, "空格子上不该报出子力"


def test_web_mirrors_the_two_stage_flow() -> None:
    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    assert "hintStage" in js, "网页没有两段式状态"
    assert "session.hintStage=0" in js, "网页换手时没重置提示阶段"
    assert "先看这一枚" in js, "网页第一段没指子"
