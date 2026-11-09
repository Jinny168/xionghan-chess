import threading

import pytest

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import (
    Color,
    GameState,
    Move,
    MoveRecord,
    Piece,
    PieceType,
    Position,
)


def test_ai_returns_only_legal_move():
    game = Game("web")
    move = ChessAI(Difficulty.BEGINNER, seed=7).choose_move(game)
    assert move is not None
    assert game.rules.is_legal(game.state, move)


def test_ai_can_be_cancelled_without_hanging():
    game = Game("desktop_complete")
    cancel = threading.Event()
    cancel.set()
    move = ChessAI(Difficulty.HARD).choose_move(game, cancel)
    assert move is not None


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_every_difficulty_prefers_a_clean_material_capture(monkeypatch, difficulty):
    # 预算必须**按档位**给，不能一刀切 0.1：
    #   beginner 的 time_limit 是 0.5s，×0.1 只剩 **50ms** —— 连 depth 1 都跑不完。
    #   实测（本机，同一局面 5 轮）：50ms 下 `completed_depth` 停在 0，`_root` 在写
    #   `root_scores` 之前就抛 `SearchTimeout`，选点退化成"排序首着"（一个王步），
    #   于是这条用例红在"没算"而不是"不吃子"。CI 机器更慢，是**稳定红**；本机是
    #   5 次里 2 次的边缘抖动（实测），所以它既不能被当成 flaky 跳过，也不能靠重试掩盖。
    #   弱档给 0.5（= 250ms / 750ms）刚好够跑完 depth 1~2；强档维持 0.1 以免单条
    #   hard/expert 各吃 1.2–2.8s 把整跑拖长。
    time_scale = "0.5" if difficulty in (Difficulty.BEGINNER, Difficulty.EASY) else "0.1"
    monkeypatch.setenv("AI_TIME_SCALE", time_scale)
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 4)
    rook = Piece.create(PieceType.ROOK, Color.RED, 5, 5)
    pawn = Piece.create(PieceType.PAWN, Color.BLACK, 5, 8)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, pawn], turn=Color.RED,
    ))

    ai = ChessAI(difficulty, seed=1)
    move = ai.choose_move(game)

    assert move is not None
    if difficulty is not Difficulty.MASTER:
        # MASTER 走 MCTS，不写 `completed_depth`；其余档必须真的算过。
        # 这条是本次最重要的护栏：它把"红"钉在**预算不足**这个真因上。没有它，
        # 下次再有人调小 `AI_TIME_SCALE`（或用更快/更慢的机器），失败信息只会是
        # "AI 没吃子"，看起来像引擎退化，实际上引擎根本没开始算。
        assert ai.completed_depth >= 1, (
            f"{difficulty.value} 在 AI_TIME_SCALE={time_scale} 下未完成任何深度，"
            "用例前提不成立（不是 AI 不吃子，是预算不够）"
        )
    assert move.source == rook.position
    assert move.target == pawn.position


def test_hard_ai_prefers_the_more_valuable_capture(monkeypatch):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 4)
    rook = Piece.create(PieceType.ROOK, Color.RED, 5, 5)
    black_pawn = Piece.create(PieceType.PAWN, Color.BLACK, 5, 8)
    black_rook = Piece.create(PieceType.ROOK, Color.BLACK, 8, 5)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, black_pawn, black_rook],
        turn=Color.RED,
    ))

    move = ChessAI(Difficulty.HARD, seed=2).choose_move(game)

    assert move is not None
    assert move.source == rook.position
    assert move.target == black_rook.position


def test_ai_avoids_an_immediate_reverse_when_useful_moves_exist(monkeypatch):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 6)
    blocker = Piece.create(PieceType.ADVISOR, Color.BLACK, 2, 6)
    rook = Piece.create(PieceType.ROOK, Color.BLACK, 2, 2)
    red_pawn = Piece.create(PieceType.PAWN, Color.RED, 8, 2)
    state = GameState(
        "desktop_complete", [red_king, black_king, blocker, rook, red_pawn],
        turn=Color.BLACK,
    )
    previous = Move(Position(1, 2), Position(2, 2))
    state.history.append(MoveRecord(previous, Color.BLACK, PieceType.ROOK, (), "俥 2,3 至 3,3"))
    game = Game.from_state(state)

    move = ChessAI(Difficulty.HARD, seed=3).choose_move(game)

    assert move is not None
    assert move != Move(Position(2, 2), Position(1, 2))


# ---------------------------------------------------------------------------
# 静态搜索（quiescence）节点上限：只截断"跑飞"的吃子链
# ---------------------------------------------------------------------------
def test_quiescence_node_limit_is_bounded():
    """上限 = 80：有上限防跑飞，又不会切到正常搜索。

    依据见 `ai.QUIESCENCE_NODE_LIMIT` 上方注释的实测：同一批四个回归局面，
    cap 80 的 trunc 全为 0，cap 40 则**四个局面各触发 1 次**（切到正常链）。
    """

    from xionghan_chess.core.ai import QUIESCENCE_NODE_LIMIT

    assert 20 <= QUIESCENCE_NODE_LIMIT <= 200, f"上限 {QUIESCENCE_NODE_LIMIT} 不在合理区间"
    assert QUIESCENCE_NODE_LIMIT == 80


def test_quiescence_truncations_is_reported_and_reset():
    """计数器存在、初值为 0，且每次 `choose_move` 重新计数（不跨局累加）。"""
    engine = ChessAI(Difficulty.BEGINNER, seed=7)
    game = Game("web")
    engine.choose_move(game)
    first = engine.quiescence_truncations
    assert isinstance(first, int) and first >= 0
    engine.choose_move(Game("web"))
    assert engine.quiescence_truncations >= 0  # 已重置，不是累加


def test_truncated_root_moves_never_become_best(monkeypatch):
    """把上限压到 0 → 所有根着法的静态搜索都被截断 → 必须退回初始序首着。

    **为什么用 4 子残局而不是 `Game("web")`**：本用例验的是「截断兜底」这条逻辑，
    与开局有多少合法着**无关**。而 `Game("web")` 有 104 个合法着，`choose_move` 一上来
    要对它们逐个做将军预筛（`apply_unchecked + in_check`）—— 实测这笔排序**本身就要
    125ms**（5 轮 125–125ms），吃掉 BEGINNER 500ms 预算的四分之一；一旦它把预算吃光，
    `_root` 的第一个 `_guard` 就抛 `SearchTimeout`，**一次根着法都没轮到**，
    `quiescence_truncations` 停在 0 —— 失败信息看起来像「截断逻辑坏了」，其实是没轮到算。
    实测（`Game("web")` + 默认 1×）：同一命令连跑 5 轮 **2 红 3 绿**，负载决定；
    撞穿预算只需要 4 倍慢机，与 CI 的 2 倍量级太近。

    换成 28 着的残局后，排序只要 **15ms**，撞穿 500ms 预算需要 **31 倍**慢机（本机 20 核
    全部占满的压力测试下仍是 13/13 绿）；8 轮复测 trunc 恒为 27、中位 0.16s。
    **所以换局面不是为了跑得快，是为了让"红"只可能由截断逻辑引起，而不是由机器速度引起。**
    """
    monkeypatch.setattr("xionghan_chess.core.ai.QUIESCENCE_NODE_LIMIT", 0)
    # 4 子残局：28 个合法着（vs 开局的 104 个），足以产出 27 次截断，覆盖不受影响。
    game = Game.from_state(GameState("desktop_complete", [
        Piece.create(PieceType.KING, Color.RED, 11, 6),
        Piece.create(PieceType.KING, Color.BLACK, 1, 4),
        Piece.create(PieceType.ROOK, Color.RED, 5, 5),
        Piece.create(PieceType.PAWN, Color.BLACK, 5, 8),
    ], turn=Color.RED))
    engine = ChessAI(Difficulty.BEGINNER, seed=11)
    legal = game.rules.legal_moves(game.state)
    expected = engine._order(game, legal)
    expected = sorted(expected, key=lambda move: engine._root_bias(game, move) < -100)[0]

    move = engine.choose_move(game)

    assert engine.quiescence_truncations > 0, (
        f"上限 0 时应当发生截断（实际 {engine.quiescence_truncations}）；若为 0，"
        "先怀疑预算不足导致排序阶段就超时，而不是截断逻辑坏了"
    )
    assert move == expected, "全部根着法被截断时必须退回初始序首着"


# ---------------------------------------------------------------------------
# 将军预筛：只许「多算一次」，不许「漏掉一次」
# ---------------------------------------------------------------------------
def test_check_prescreen_never_misses_a_real_check():
    """`_may_give_check` 为假时，这一步**确实**不给将军。

    预筛只用来省 `apply_unchecked + in_check`（0.5 ms/着）；一旦出现假阴性，
    排序里那 +900 就会少给，等同于悄悄改了搜索顺序。逐局面逐着法对一遍。
    """
    engine = ChessAI(Difficulty.MEDIUM, seed=5)
    misses: list[str] = []
    for profile in ("desktop_complete", "desktop_classic", "web"):
        game = Game(profile)
        for _ in range(5):
            moves = game.rules.legal_moves(game.state)
            if not moves:
                break
            for move in moves:
                exact = game.rules.in_check(
                    game.rules.apply_unchecked(game.state, move),
                    game.state.turn.opponent)
                if exact and not engine._may_give_check(game, move):
                    misses.append(f"{profile}:{move.key()}")
            game.move(moves[0])
    assert not misses, f"预筛漏掉了真实的将军着法：{misses[:5]}"


def test_check_prescreen_keeps_move_ordering_identical():
    """预筛前后 `_order()` 的输出顺序必须**完全一致**（少算但结果不改）。"""
    engine = ChessAI(Difficulty.MEDIUM, seed=6)
    for profile in ("desktop_complete", "web"):
        game = Game(profile)
        for _ in range(4):
            moves = game.rules.legal_moves(game.state)
            if not moves:
                break
            fast = [move.key() for move in engine._order(game, moves)]
            original = engine._may_give_check
            engine._may_give_check = lambda *args, **kwargs: True
            slow = [move.key() for move in engine._order(game, moves)]
            engine._may_give_check = original
            assert fast == slow, f"{profile} 的着法排序被预筛改变了"
            game.move(moves[0])
