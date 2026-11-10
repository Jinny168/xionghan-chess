"""B1 陪练档：取样集合与「必须走最强着」闸门的行为守卫。

设计口径（docs/IMPROVEMENT_PLAN.md）：
- 取样只从**名次 2..N**里挑，**不含第 1 名** —— 含了会让名义概率与真实弱化率脱节；
- 五条闸门任一成立就必须走最强着：被将军 / 一步制胜 / 最佳着是净正吃 /
  有效候选不足 / 本轮搜索没算完（`completed_depth == 0`）；
- 吃子要过 SEE 闸门：弱档可以走次优，但不该白送子。

这几条都不能只写在注释里 —— 取样分支藏在搜索尾部，一旦被改回"从第 1 名起选"，
肉眼看代码很难发现，测试能直接拦下。
"""

from __future__ import annotations

from xionghan_chess.core.ai import CONFIGS, VALUES, ChessAI
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, Move, PieceType


def _ai(difficulty: str = "beginner") -> ChessAI:
    # 固定种子：取样本身是随机的，测试要能复现
    return ChessAI(difficulty, seed=20261102)


def _moves(game: Game) -> list[Move]:
    return game.rules.legal_moves(game.state, game.state.turn)


def _rig(ai: ChessAI, scores: list[float], moves: list[Move]) -> None:
    """把根着法打分摆成指定形状（不跑搜索，只测取样策略）。"""
    assert len(scores) <= len(moves)
    ai.root_scores = [(score, move, False) for score, move in zip(scores, moves)]
    ai.completed_depth = 2


def test_sampling_never_picks_the_best_move() -> None:
    """取样集合必须是名次 2..N —— 第 1 名不许出现在候选里。

    这条是"概率可标定"的前提：命中第 1 名等于没弱化，名义 0.55 会缩水成 0.44。
    """
    game = Game("web")
    ai = _ai("beginner")
    moves = _moves(game)
    _rig(ai, [0, -10, -20, -30], moves)
    best = ai.root_scores[0][1]

    for _ in range(50):
        picked = ai._sample_weaker(game, CONFIGS[ai.difficulty])
        if picked is None:
            continue
        assert picked.key() != best.key(), "取样命中了最强着 —— 等于没弱化"


def test_sampling_respects_the_margin() -> None:
    """超出 `sample_margin` 的着法不进候选池（beginner 是 150）。"""
    game = Game("web")
    ai = _ai("beginner")
    moves = _moves(game)
    cfg = CONFIGS[ai.difficulty]
    near = moves[1]
    far = moves[2]
    ai.root_scores = [(0, moves[0], False), (-50, near, False), (-(cfg.sample_margin + 50), far, False)]
    ai.completed_depth = 2

    for _ in range(50):
        picked = ai._sample_weaker(game, cfg)
        assert picked is None or picked.key() != far.key(), f"分差超过 {cfg.sample_margin} 的着法被取样了"


def test_gate_blocks_sampling_when_search_unfinished() -> None:
    """`completed_depth == 0` 时分数不可信，不许取样。"""
    game = Game("web")
    ai = _ai("beginner")
    moves = _moves(game)
    _rig(ai, [0, -10, -20], moves)
    ai.completed_depth = 0
    assert ai._sample_weaker(game, CONFIGS[ai.difficulty]) is None


def test_gate_blocks_sampling_when_in_check() -> None:
    """被将军时必须应着 —— 弱档乱走会被立刻将死，一眼看破。"""
    game = Game("web")
    ai = _ai("beginner")
    moves = _moves(game)
    _rig(ai, [0, -10, -20], moves)
    # 直接打桩：`_sampling_blocked` 只问"轮到谁被将"
    game.rules.in_check = lambda state, color: True  # type: ignore[method-assign]
    assert ai._sample_weaker(game, CONFIGS[ai.difficulty]) is None


def test_gate_blocks_sampling_on_a_forced_win() -> None:
    """有一手能直接制胜时必须走它 —— "能赢不赢"是最刺眼的放水。"""
    game = Game("web")
    ai = _ai("beginner")
    moves = _moves(game)
    _rig(ai, [VALUES[PieceType.KING], -10, -20], moves)
    assert ai._sample_weaker(game, CONFIGS[ai.difficulty]) is None


def test_gate_blocks_sampling_when_best_is_a_clean_capture() -> None:
    """最佳着是"净赚一个兵以上"的吃子时不许换着。"""
    from xionghan_chess.core.model import Piece

    game = Game("web")
    ai = _ai("beginner")
    # 造一个"白送的兵"：红车贴脸，黑兵无保护
    game.state.pieces = [
        Piece.create(PieceType.KING, Color.RED, 0, 0),
        Piece.create(PieceType.KING, Color.BLACK, 12, 12),
        Piece.create(PieceType.ROOK, Color.RED, 5, 5),
        Piece.create(PieceType.PAWN, Color.BLACK, 5, 6),
    ]
    game.state.turn = Color.RED
    moves = _moves(game)
    capture = next((m for m in moves if game.state.piece_at(m.target) is not None), None)
    assert capture is not None, "局面构造失败：没有任何吃子着法"
    others = [m for m in moves if m.key() != capture.key()]
    _rig(ai, [0, -10, -20], [capture, *others[:2]])
    assert ai._sample_weaker(game, CONFIGS[ai.difficulty]) is None, "最佳着是净正吃却仍在取样 —— 会出现'有子不吃'"


def test_practice_difficulty_parameters_are_the_agreed_ones() -> None:
    """并档后 easy 只是 beginner 的别名；入门陪练参数仍是设计定稿值。"""
    beginner = CONFIGS["beginner"]
    easy = CONFIGS["easy"]
    assert easy is beginner
    assert (beginner.randomness, beginner.candidate_count, beginner.sample_margin) == (0.55, 4, 150)


def test_strong_difficulties_never_sample() -> None:
    """hard 及以上 randomness 必须为 0；medium 只允许既有的一点点。"""
    hard = CONFIGS["hard"]
    for level in ("expert", "master"):
        assert CONFIGS[level] is hard, f"{level} 应只是 hard 的别名"
    assert hard.randomness == 0.0
    assert CONFIGS["medium"].randomness <= 0.05, "medium 的取样概率不该被本轮放大"
