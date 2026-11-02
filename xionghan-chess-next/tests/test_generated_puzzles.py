"""生成的多步题必须能真的被走完 —— 判题器、数据、自动应着三者串起来的端到端检查。

只靠单测各层都绿是不够的：解法是交替序列、判题器要自动落对手应着、
最后一手必须真的把对方将死。这三件事任何一件对不上，玩家体验就是"走对了也不过关"。
"""

from __future__ import annotations

from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.desktop import training

GENERATED = [item for item in load_puzzles() if item.id.startswith("gen-mate3")]


def test_generated_puzzles_exist() -> None:
    assert GENERATED, "题库里没有生成的多步题 —— 出题器的产物没合并进来？"


def test_every_generated_puzzle_can_be_played_to_the_end() -> None:
    for puzzle in GENERATED:
        session = training.PuzzleSession(puzzle)
        game = game_from_document(puzzle.document)
        for index, move in enumerate(puzzle.solution):
            if index % 2 == 0:
                verdict = session.submit(move)
                assert verdict in (training.VERDICT_CORRECT, training.VERDICT_SOLVED), \
                    f"{puzzle.id} 第 {index + 1} 手被判错"
                game.move(move)
            else:
                # 对手应着：必须由 `auto_reply` 自动给出，玩家不该提交它
                assert session.auto_reply is not None, f"{puzzle.id} 没有给出自动应着"
                assert session.auto_reply.key() == move.key()
                session.advance_auto()
                game.move(move)
        assert session.solved, f"{puzzle.id} 走完解法仍未判定通过"
        assert game.state.finished, f"{puzzle.id} 解完后局面没有结束 —— 末手不是杀棋"


def test_generated_puzzles_declare_hands_not_plies() -> None:
    """提示条数按「手」算：3 ply 的题要有 2 条提示。"""
    for puzzle in GENERATED:
        hands = (len(puzzle.solution) + 1) // 2
        assert len(puzzle.hints) >= hands, f"{puzzle.id} 提示不足 {hands} 条"
        assert len(puzzle.solution) % 2 == 1, f"{puzzle.id} 解法长度必须是奇数"
