"""生成的多步题必须能真的被走完 —— 判题器、数据、自动应着三者串起来的端到端检查。

只靠单测各层都绿是不够的：解法是交替序列、判题器要自动落对手应着、
最后一手必须真的把对方将死。这三件事任何一件对不上，玩家体验就是"走对了也不过关"。
"""

from __future__ import annotations

from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.desktop import training

GENERATED = [item for item in load_puzzles() if item.id.startswith("gen-")]


def test_generated_puzzles_exist() -> None:
    assert GENERATED, "题库里没有生成的多步题 —— 出题器的产物没合并进来？"


def test_every_generated_puzzle_can_be_played_to_the_end() -> None:
    for puzzle in GENERATED:
        session = training.PuzzleSession(puzzle)
        game = game_from_document(puzzle.document)
        for index, move in enumerate(puzzle.solution):
            if index % 2 == 0:
                verdict = session.submit(move)
                assert verdict in (training.VERDICT_CORRECT, training.VERDICT_SOLVED), (
                    f"{puzzle.id} 第 {index + 1} 手被判错"
                )
                game.move(move)
            else:
                # 对手应着：必须由 `auto_reply` 自动给出，玩家不该提交它
                assert session.auto_reply is not None, f"{puzzle.id} 没有给出自动应着"
                assert session.auto_reply.key() == move.key()
                session.advance_auto()
                game.move(move)
        assert session.solved, f"{puzzle.id} 走完解法仍未判定通过"
        # 批次 A：守题（defense / equilibrium）的正解是"化解威胁"，不是将死对方，
        # 末手局面**不该**结束（否则就不是守题了）。只有杀题/特色子题才要求末手将死。
        is_defense = {"defense", "equilibrium"} & set(puzzle.tags)
        if is_defense:
            assert not game.state.finished, f"{puzzle.id} 守题解完却成了将死 —— 判据②被破坏"
        else:
            assert game.state.finished, f"{puzzle.id} 解完后局面没有结束 —— 末手不是杀棋"


def test_generated_puzzle_mix_matches_the_plan() -> None:
    """批次 A 后 35 条的配比：难度 beginner 9 / advanced 12 / master 14；
    ply 覆盖 1/3/5/7（新增守题与特色子题为 1 ply 单步）。"""
    from collections import Counter

    levels = Counter(item.difficulty for item in GENERATED)
    plies = Counter(len(item.solution) for item in GENERATED)
    assert levels == {"beginner": 9, "advanced": 12, "master": 14}, levels
    assert sum(plies.values()) == 35
    assert set(plies) == {1, 3, 5, 7}, plies
    assert all(len(item.solution) % 2 == 1 for item in GENERATED)


def test_batch_a_new_puzzles_shape() -> None:
    """gen-23~35 的专题、章节、id 结构锁定（批次 A / P1-1）。"""
    from collections import Counter

    new = [p for p in GENERATED if 23 <= int(p.id.split("-")[1]) <= 35]
    assert len(new) == 13, f"新题应有 13 条，实际 {len(new)}"
    assert {p.id for p in new} == {f"gen-{n}" for n in range(23, 36)}
    chapters = Counter(p.chapter for p in new)
    assert chapters == {"破釜": 3, "逐鹿": 2, "垓下": 4, "定鼎": 4}, chapters
    # 专题配额：守题 6 / 特色子 4 / 长算 3
    defense = sum(1 for p in new if "defense" in p.tags)
    feature = sum(1 for p in new if any(t.startswith("feature:") for t in p.tags))
    long = sum(1 for p in new if "mate5" in p.tags or "mate7" in p.tags)
    assert (defense, feature, long) == (6, 4, 3), (defense, feature, long)
    # 特色子四种各一
    kinds = {t for p in new for t in p.tags if t.startswith("feature:")}
    assert kinds == {"feature:archer", "feature:patrol", "feature:thunder", "feature:guard"}, kinds


def test_generated_puzzles_declare_hands_not_plies() -> None:
    """提示条数按「手」算：3 ply 的题要有 2 条提示。"""
    for puzzle in GENERATED:
        hands = (len(puzzle.solution) + 1) // 2
        assert len(puzzle.hints) >= hands, f"{puzzle.id} 提示不足 {hands} 条"
        assert len(puzzle.solution) % 2 == 1, f"{puzzle.id} 解法长度必须是奇数"
