"""生成的多步题必须能真的被走完 —— 判题器、数据、自动应着三者串起来的端到端检查。

只靠单测各层都绿是不够的：解法是交替序列、判题器要自动落对手应着、
最后一手必须真的把对方将死。这三件事任何一件对不上，玩家体验就是"走对了也不过关"。
"""

from __future__ import annotations

import importlib.util
import re
import time
from pathlib import Path

import pytest

from xionghan_chess.core.model import Color, Move, PieceType, Position
from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.desktop import training

ROOT = Path(__file__).resolve().parents[1]
GENERATED = [item for item in load_puzzles() if item.id.startswith("gen-")]
# 杀题全集：mate2|mate3|mate5|mate7 标签的全部题（围杀/连环/长算/垭下定鼎三大系列）。
# 门禁按**行为与承诺**圈定，**无白名单、无例外**——D8/D9 漏网就是因为旧门禁只看 counter。
MATED = ("mate2", "mate3", "mate5", "mate7")
MATE = [p for p in GENERATED if any(t in MATED for t in p.tags)]
LE5 = [p for p in MATE if len(p.solution) <= 5]  # 3/5 ply，G4 穷举
GT5 = [p for p in MATE if len(p.solution) >= 7]  # 7 ply，G4 slow+预算（当前应为空）
# 文案里承诺了末手类型（连杀→将死 / 无路可走→困毙）的 mate 题 —— G3 圈定。
PROMISED_END = [p for p in MATE if "连杀" in p.description or "无路可走" in p.description]
# 承诺末手类型、但两个关键词都不含的题（G3 不表态，只回报列出）——应为空。
NO_KEYWORD_END = [p for p in MATE if "连杀" not in p.description and "无路可走" not in p.description]

_MATELIB = None


def _matelib():
    """加载出题器的强制胜搜索（与生成器同口径；只加载一次，模块级缓存）。"""
    global _MATELIB
    if _MATELIB is None:
        spec = importlib.util.spec_from_file_location("gen_forced_mate_puzzles", ROOT / "scripts" / "gen_forced_mate_puzzles.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _MATELIB = module
    return _MATELIB


def _solution_moves(puzzle) -> list[Move]:
    return [Move(Position(s.source.row, s.source.col), Position(s.target.row, s.target.col)) for s in puzzle.solution]


def _play(puzzle):
    """按真实加载路径走完 solution，返回终局 Game（末手类型看 state.result_reason）。"""
    game = game_from_document(puzzle.document)
    for move in _solution_moves(puzzle):
        game.move(move)
    return game


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
    """35 条配比：难度 beginner 9 / advanced 12 / master 14；ply 覆盖 1/3/5。

    E1 起**全库无 7 ply 题**——mate7 档位在稀疏残局里无法真实成立「唯一强制线」（必带 5 ply
    更短胜），已全部退役为 5 ply。故 ply 集合不再含 7。"""
    from collections import Counter

    levels = Counter(item.difficulty for item in GENERATED)
    plies = Counter(len(item.solution) for item in GENERATED)
    assert levels == {"beginner": 9, "advanced": 12, "master": 14}, levels
    assert sum(plies.values()) == 35
    assert set(plies) == {1, 3, 5}, plies
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


# ============================================================================
# 杀题真实性门禁 G1~G6（按**行为与承诺**圈定，不按 counter 标签 —— D8/D9 漏网正因旧门
# 只看 counter）。困毙（stalemate）在本作算走方胜，但只有**承诺困毙**的题才算它；承诺
# 「连杀」的题末手必须是真将死。下面「黑方无合法应手」一律含困毙与吃王，一视同仁。
# ============================================================================


def test_g1_root_position_is_legal() -> None:
    """G1：所有 mate5/mate7 题根局面合法 —— 未终局、黑方未被将、黑方有合法应手。"""
    assert MATE, "G6：没有 mate 题，门禁失去意义"
    for puzzle in MATE:
        game = game_from_document(puzzle.document)
        assert not game.state.finished, f"{puzzle.id} 根局面已是终局"
        assert not game.rules.in_check(game.state, Color.BLACK), f"{puzzle.id} 根局面黑方已被将军（非法）"
        assert game.rules.has_any_legal_move(game.state, Color.BLACK), f"{puzzle.id} 根局面黑方无合法应手"


def test_g2_no_shorter_forced_win() -> None:
    """G2：所有 mate 题无更短强制胜。更短深度通用取 `for k in range(1, ply, 2)`（5ply→1,3；
    7ply→1,3,5；含吃王与困毙）。D8 三道（gen-18/21/22）就是被这条抓出的——玩家走对首着后
    还能找到更快赢法。"""
    lib = _matelib()
    assert MATE, "G6：没有 mate 题"
    for puzzle in MATE:
        game = game_from_document(puzzle.document)
        plies = len(puzzle.solution)
        cache: dict = {}
        for k in range(1, plies, 2):
            assert not lib._forced_win(game.rules, game.state, k, king_only=False, cache=cache), (
                f"{puzzle.id} 存在 {k} ply 强制胜（比声明的 {plies} ply 更短）"
            )


def test_g3_last_move_matches_promise() -> None:
    """G3：末手类型与文案承诺一致 —— 文案含「连杀」→ 末手必须 checkmate；含「无路可走」
    → 末手必须 stalemate。D9 的老题（说连杀实为困毙）就是被这条挡住的。"""
    assert PROMISED_END, "G6：没有承诺末手类型的题"
    # 既有 mate 题必须至少含一个承诺关键词，否则 G3 对它无法判断（会静默漏检）。
    # 将来谁写出一道既不提「连杀」也不提「无路可走」的 mate 题，这条会先红，逼先修文案。
    assert not NO_KEYWORD_END, (
        "这些 mate 题既没说「连杀」也没说「无路可走」，G3 无法判断末手类型，须先修文案："
        + ", ".join(p.id for p in NO_KEYWORD_END)
    )
    mismatches: list[str] = []
    for puzzle in PROMISED_END:
        reason = _play(puzzle).state.result_reason
        if "连杀" in puzzle.description and reason != "checkmate":
            mismatches.append(f"{puzzle.id} 承诺连杀但末手={reason}（应 checkmate）")
        if "无路可走" in puzzle.description and reason != "stalemate":
            mismatches.append(f"{puzzle.id} 承诺无路可走但末手={reason}（应 stalemate）")
    assert not mismatches, "末手与文案不符：\n" + "\n".join(mismatches)


def _check_unique(puzzle, lib, *, deadline: float | None = None) -> None:
    """G4：直接复用生成器的 `_unique_line`（**b 口径同源**，C3 与 G4 共用一个实现）。

    b 口径 = 每红节点"走完黑方任意应手都输"的红着恰 1；每黑节点应手恰 1；末手强制取胜
    （将死/困毙/吃王任一）。末手**类型**由 G3 按文案断言——G4 只管"唯一 + 取胜"。
    """
    game = game_from_document(puzzle.document)
    plies = len(puzzle.solution)
    line = lib._unique_line(game.rules, game.state, plies, cache={}, deadline=deadline)
    assert line is not None, f"{puzzle.id} 非唯一强制线（某红节点致胜着法≠1 / 黑应手≠1 / 末手非取胜）"
    assert [m.key() for m in line] == [m.key() for m in _solution_moves(puzzle)], (
        f"{puzzle.id} 唯一强制线与 solution 不一致：{[m.key() for m in line]}"
    )


def test_g4_unique_forced_line_five_ply() -> None:
    """G4（5 ply 穷举）：每红节点致胜着法恰 1、每黑节点应手恰 1。7 ply 见下面的 slow 版。"""
    lib = _matelib()
    assert LE5, "G6：没有 3/5 ply mate 题"
    for puzzle in LE5:
        _check_unique(puzzle, lib)


@pytest.mark.slow
def test_g4_unique_forced_line_seven_ply() -> None:
    """G4（7 ply）：唯一性穷举是 PSPACE 级指数搜索，单题**20 秒预算**，超预算显式 skip 并点名
    （项目纪律：不许静默跳过）。**当前全库已无 7 ply 题**（mate7 全部退役为 5 ply），此分支是
    为将来谁再加 mate7 时的保护——新增 mate7 必然触发它。"""
    lib = _matelib()
    if not GT5:
        pytest.skip("当前无 7 ply 题，G4 7ply 分支为未来 mate7 保护（本轮无题可选）")
    timed_out: list[str] = []
    for puzzle in GT5:
        try:
            _check_unique(puzzle, lib, deadline=time.monotonic() + 20)
        except lib._Budget:
            timed_out.append(puzzle.id)
    if timed_out:
        pytest.skip("7 ply 唯一性穷举超 20s 预算（指数爆炸），跳过并点名：" + ", ".join(timed_out))


# ---- G4 独立实现（QA 要求：不复用生成器搜索，避免"一致地错"）------------------


def _ind_black_lost(eng, state) -> bool:
    if not any(p.type is PieceType.KING and p.color is Color.BLACK for p in state.pieces):
        return True
    return not eng.has_any_legal_move(state, Color.BLACK)


def _ind_poskey(state) -> tuple:
    """独立实现自己的局面签名（不复用生成器），只用于本自写的记忆化。"""
    return (state.turn.value, tuple(sorted((p.type.value, p.color.value, p.position.row, p.position.col) for p in state.pieces)))


def _ind_forced_win(eng, state, plies: int, memo: dict) -> bool:
    """独立实现的「红方 plies 内强制取胜」：红走一手，黑所有应手都应能被红更强取胜。

    带本函数自写的 `memo`（(签名, plies)→bool）——纯性能优化，不引用生成器任何代码，独立性不变。
    """
    key = (_ind_poskey(state), plies)
    if key in memo:
        return memo[key]
    result = False
    for move in eng.legal_moves(state, Color.RED):
        nxt = eng.apply_unchecked(state, move)
        if _ind_black_lost(eng, nxt):
            result = True
            break
        if plies <= 1:
            continue
        replies = eng.legal_moves(nxt, Color.BLACK)
        if replies and all(_ind_forced_win(eng, eng.apply_unchecked(nxt, r), plies - 2, memo) for r in replies):
            result = True
            break
    memo[key] = result
    return result


def _ind_winning_red_moves(eng, state, plies: int, memo: dict) -> list[Move]:
    out: list[Move] = []
    for move in eng.legal_moves(state, Color.RED):
        nxt = eng.apply_unchecked(state, move)
        if _ind_black_lost(eng, nxt):
            out.append(move)
        elif plies > 1:
            replies = eng.legal_moves(nxt, Color.BLACK)
            if replies and all(_ind_forced_win(eng, eng.apply_unchecked(nxt, r), plies - 2, memo) for r in replies):
                out.append(move)
        if len(out) >= 2:
            break
    return out


@pytest.mark.parametrize("pid", ["gen-04", "gen-02", "gen-31", "gen-13"])
def test_g4_independent_unique(pid: str) -> None:
    """G4 的**独立实现**（不复用生成器 `_unique_line`）：2×2 覆盖 {3ply,5ply}×{将死,困毙}。

    gen-04(3ply/将死) · gen-02(3ply/困毙) · gen-31(5ply/将死) · gen-13(5ply/困毙)。
    自己枚举/递归（`_ind_*`），与生成器的强制胜搜索互不引用——防止"生成器判据写错、门禁跟着
    一致地错"。原先只有 5ply+将死一格的独立兜底，现补齐另外三格。
    """
    puzzle = next((p for p in MATE if p.id == pid), None)
    assert puzzle is not None, f"缺 {pid}"
    game = game_from_document(puzzle.document)
    eng, state = game.rules, game.state
    moves = _solution_moves(puzzle)
    plies = len(moves)
    memo: dict = {}
    for index, move in enumerate(moves):
        remaining = plies - index
        if index % 2 == 0:
            wins = _ind_winning_red_moves(eng, state, remaining, memo)
            assert len(wins) == 1, f"{pid} 第 {index + 1} 红节点独立枚举出 {len(wins)} 个致胜着法（应恰 1）"
            assert wins[0].key() == move.key(), f"{pid} 第 {index + 1} 红节点唯一致胜着法 != solution"
        else:
            replies = eng.legal_moves(state, Color.BLACK)
            assert len(replies) == 1 and replies[0].key() == move.key(), f"{pid} 第 {index + 1} 黑节点应手不唯一"
        state = eng.apply_unchecked(state, move)
    assert _ind_black_lost(eng, state), f"{pid} 末手不是强制取胜（独立判定，末手类型由 G3 另判）"


def test_g5_description_numbers() -> None:
    """G5：文案里的手数必须等于 `(len(solution)+1)//2`；「四十余着」必须 40<=首着数<50。"""
    hand_map = {"一": 1, "两": 2, "三": 3, "四": 4, "五": 5}
    for puzzle in GENERATED:
        if not puzzle.description:
            continue
        need = (len(puzzle.solution) + 1) // 2
        for match in re.finditer(r"([一二三四五])手", puzzle.description):
            said = hand_map[match.group(1)]
            assert said == need, f"{puzzle.id} 文案说「{match.group(0)}」但实际是 {need} 手（{len(puzzle.solution)} ply）"
        if "四十余着" in puzzle.description:
            game = game_from_document(puzzle.document)
            first_moves = len(game.rules.legal_moves(game.state, Color.RED))
            assert 40 <= first_moves < 50, f"{puzzle.id} 文案说「四十余着」但根局面首着数={first_moves}，不在 [40,50)"


def test_g6_gate_sets_not_empty() -> None:
    """G6：G2/G3/G4 各自的候选集必须非空，否则空跑假绿。"""
    assert MATE, "G2 候选（mate5/mate7）为空"
    assert PROMISED_END, "G3 候选（承诺末手类型）为空"
    assert LE5, "G4 候选（3/5ply mate）为空"


# G7 判据：题名里「数字 + 手」的字面（如「围杀·2 手」「连环·3 手」）＝手数编码，禁止。
# 判据用正则「数字+手」而非「含手字」：**只抓手数编码，天然不误伤「射手」这类构词**
# （"射手"里「手」前没有数字），所以可放心扩到**全库**，把所有系列都纳入防护。
TITLE_HAND_RE = re.compile(r"[0-9一二三四五六七八九十]+\s*手")


def test_g7_title_has_no_hand_count() -> None:
    """G7：任何题的题名不得编码手数（title 不含「数字+手」字面）。范围＝全库 GENERATED。

    历史教训：手数写进题名，重生成一次就变假话（mate7→mate5 已改过两次题名）。手数只准
    出现在 description 里、且必须与事实一致（G5 守卫）。因为「数字+手」正则天然不匹配
    「星轨射手」这类构词，所以覆盖全库不会误伤它。
    """
    offenders = [f"{p.id}:{p.title}" for p in GENERATED if TITLE_HAND_RE.search(p.title)]
    assert not offenders, "题名编码了手数（数字+手），禁止：" + ", ".join(offenders)
