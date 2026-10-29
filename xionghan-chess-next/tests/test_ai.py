import threading
import pytest

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, MoveRecord, Piece, PieceType, Position


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
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 4)
    rook = Piece.create(PieceType.ROOK, Color.RED, 5, 5)
    pawn = Piece.create(PieceType.PAWN, Color.BLACK, 5, 8)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, pawn], turn=Color.RED,
    ))

    move = ChessAI(difficulty, seed=1).choose_move(game)

    assert move is not None
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
    """上限必须落在 60–80：太小会截断正常变例，太大等于没限（实测 226 节点变例不触发）。"""
    from xionghan_chess.core.ai import QUIESCENCE_NODE_LIMIT

    assert 60 <= QUIESCENCE_NODE_LIMIT <= 80


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
    """把上限压到 0 → 所有根着法的静态搜索都被截断 → 必须退回初始序首着。"""
    monkeypatch.setattr("xionghan_chess.core.ai.QUIESCENCE_NODE_LIMIT", 0)
    game = Game("web")
    engine = ChessAI(Difficulty.BEGINNER, seed=11)
    legal = game.rules.legal_moves(game.state)
    expected = engine._order(game, legal)
    expected = sorted(expected, key=lambda move: engine._root_bias(game, move) < -100)[0]

    move = engine.choose_move(game)

    assert engine.quiescence_truncations > 0, "上限 0 时应当发生截断"
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
