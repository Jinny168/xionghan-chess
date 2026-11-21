"""生成的多步题必须能真的被走完 —— 判题器、数据、自动应着三者串起来的端到端检查。

只靠单测各层都绿是不够的：解法是交替序列、判题器要自动落对手应着、
最后一手必须真的把对方将死。这三件事任何一件对不上，玩家体验就是"走对了也不过关"。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from xionghan_chess.core.model import Color, Move, Position
from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.desktop import training

ROOT = Path(__file__).resolve().parents[1]
GENERATED = [item for item in load_puzzles() if item.id.startswith("gen-")]
COUNTER = [item for item in GENERATED if "counter" in item.tags]


def _matelib():
    """加载出题器的强制胜搜索（与生成器同口径，避免测试另写一套判据漂移）。"""
    spec = importlib.util.spec_from_file_location("gen_forced_mate_puzzles", ROOT / "scripts" / "gen_forced_mate_puzzles.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _solution_moves(puzzle) -> list[Move]:
    return [Move(Position(s.source.row, s.source.col), Position(s.target.row, s.target.col)) for s in puzzle.solution]


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
        elif "counter" in puzzle.tags:
            # 长算「连杀」题（gen-31/34/35）承诺末手真将死。困毙（stalemate）同样会
            # finished=True 但没将军，拿它冒充连杀就是 D1 的假绿 —— 必须按引擎的
            # checkmate 判据收紧。老 `calibrated` 题是另一套口径（stalemate 即胜），
            # 不在本批次范围，仍只要求 finished。
            assert game.rules.checkmate(game.state, Color.BLACK), (
                f"{puzzle.id} 解完后黑方未被将死 —— 末手不是连杀（困毙不算）"
            )
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


# ---- D6：长算「连杀」题（counter）的三道真实性门禁 ----------------------------
# 困毙（stalemate）在本作算走方胜，但 counter 题承诺的是**连杀**，所以困毙同样
# 不能算「更短解」或末手 —— 下面「黑方无合法应手」一律含困毙与吃王，一视同仁。


def test_counter_puzzles_root_position_is_legal() -> None:
    """C1：根局面合法 —— 未终局、黑方没被将军、黑方至少有 1 个合法应手。

    gen-35 原来的烂题根局面 `in_check(BLACK)=True`（轮到红走却黑被将），红方首着白吃王。
    """
    assert COUNTER, "没有 counter 题，门禁失去意义"
    for puzzle in COUNTER:
        game = game_from_document(puzzle.document)
        assert not game.state.finished, f"{puzzle.id} 根局面已是终局"
        assert not game.rules.in_check(game.state, Color.BLACK), f"{puzzle.id} 根局面黑方已被将军（非法）"
        assert game.rules.has_any_legal_move(game.state, Color.BLACK), f"{puzzle.id} 根局面黑方无合法应手"


def test_counter_puzzles_have_no_immediate_finish() -> None:
    """C2 必要部分：红方**任一**合法首着都不会立刻终局（吃王 / 黑无应手 / 困毙都算立刻终止）。

    gen-35 原来首着 `1,10-0,10` 一手吃黑王，就是被这条挡住的那类烂题。
    """
    lib = _matelib()
    for puzzle in COUNTER:
        game = game_from_document(puzzle.document)
        for move in game.rules.legal_moves(game.state, Color.RED):
            nxt = game.rules.apply_unchecked(game.state, move)
            assert not lib._black_lost(game.rules, nxt), (
                f"{puzzle.id} 首着 {move.key()} 让黑方立刻无应手/被吃王 —— 更短解，破坏连杀承诺"
            )


def test_counter_puzzles_unique_forced_line() -> None:
    """C3：正解线路上**每一个红方节点**致胜着法恰 1、每个黑方节点应手恰 1、末手真将死。

    gen-34 原来的第 2 个红方节点有 48 个旁支致胜着法（如红帅平移 `12,8-11,8` 完全不将军
    也能赢），「唯一四手连杀」是假的。这条是 QA 第 3 轮复签的硬判据。
    """
    lib = _matelib()
    for puzzle in COUNTER:
        game = game_from_document(puzzle.document)
        eng = game.rules
        state = game.state
        moves = _solution_moves(puzzle)
        plies = len(moves)
        for index, move in enumerate(moves):
            remaining = plies - index
            if index % 2 == 0:  # 红方节点
                wins = lib._winning_red_moves(eng, state, remaining, max_need=2)
                assert len(wins) == 1, (
                    f"{puzzle.id} 第 {index + 1} 手（红方节点）有 {len(wins)} 个致胜着法，不唯一"
                )
                assert wins[0].key() == move.key(), (
                    f"{puzzle.id} 第 {index + 1} 手唯一致胜着法 {wins[0].key()} != solution {move.key()}"
                )
            else:  # 黑方节点
                replies = eng.legal_moves(state, Color.BLACK)
                assert len(replies) == 1, f"{puzzle.id} 第 {index + 1} 手（黑方节点）有 {len(replies)} 个应手"
                assert replies[0].key() == move.key(), f"{puzzle.id} 第 {index + 1} 手黑应手 != solution"
            state = eng.apply_unchecked(state, move)
        assert eng.checkmate(state, Color.BLACK), f"{puzzle.id} 末手不是真将死（困毙不算连杀）"
