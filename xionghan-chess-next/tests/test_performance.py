"""Performance *regression guardrails* for the hot paths (audit P0-2).

These are guardrails, **not performance acceptance**. They answer "did some
change silently make a hot path an order of magnitude slower?" -- they make no
absolute performance promise. Accordingly:

* **Relative/complexity assertions are preferred** (a point query vs a full
  enumeration, a pool-cost delta) because they survive a fast or slow machine.
* **Absolute bounds are deliberately loose** (several times the value measured
  on the authoring box, recorded per test) so CI jitter cannot turn them red.

Whole module is marked ``slow``: run it with ``pytest tests/test_performance.py``
(CI does), skip it with ``pytest -m "not slow"``. The marker is registered in
``pyproject.toml`` so ``--strict-markers`` turns a typo into an error rather
than a silent no-op.

Baselines below were measured on the authoring box (Windows, CPython 3.13,
13x13 ``desktop_complete`` board) and are only a reference point for future
comparison -- do not tighten them to "make the number nicer".
"""
from __future__ import annotations

import time

import pytest

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.benchmark import benchmark_master_vs_hard
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType
from xionghan_chess.core.profiles import get_profile


pytestmark = pytest.mark.slow


def _best_time(call, *, repeat: int = 5, number: int = 100) -> float:
    """Seconds per call, taking the best of `repeat` batches.

    Best-of (not mean) on purpose: it discards GC pauses / scheduler spikes that
    would otherwise make a single unlucky batch the measured value.
    """
    best = float("inf")
    for _ in range(repeat):
        started = time.perf_counter()
        for _ in range(number):
            call()
        best = min(best, (time.perf_counter() - started) / number)
    return best


def _game_with_pool(pool: list[Piece]) -> Game:
    """A fixed sparse board whose only moving part is the capture pool."""
    profile = get_profile("desktop_complete")
    pieces = [
        Piece.create(PieceType.KING, Color.RED, 0, 0),
        Piece.create(PieceType.KING, Color.BLACK, profile.rows - 1, profile.cols - 1),
        Piece.create(PieceType.ROOK, Color.RED, 5, 0),
        Piece.create(PieceType.ROOK, Color.BLACK, 7, 12),
        Piece.create(PieceType.CANNON, Color.RED, 8, 4),
        Piece.create(PieceType.HORSE, Color.BLACK, 3, 6),
        Piece.create(PieceType.PAWN, Color.RED, 9, 3),
        Piece.create(PieceType.PAWN, Color.BLACK, 4, 9),
        Piece.create(PieceType.ARMOR, Color.RED, 10, 1),
        Piece.create(PieceType.ASSASSIN, Color.BLACK, 2, 11),
    ]
    state = GameState(profile.id, pieces, turn=Color.RED,
                      captured={Color.RED: list(pool), Color.BLACK: []})
    return Game.from_state(state)


# --------------------------------------------------------------------------- #
# 1. position_key -- scheme A added the `||pool:` segment (hot path).
# --------------------------------------------------------------------------- #

def test_position_key_pool_segment_stays_cheap():
    # Measured: empty ~7.3 us, stocked ~8.1 us (ratio ~1.1) -- the added pool
    # sort is a microsecond against the board sort, so a 5x ceiling is enormous.
    stocked_pool = [Piece.create(kind, Color.RED, 0, index) for index, kind in enumerate(
        (PieceType.ROOK, PieceType.HORSE, PieceType.CANNON, PieceType.ARMOR,
         PieceType.ARCHER, PieceType.THUNDER))]

    empty = _game_with_pool([])
    stocked = _game_with_pool(stocked_pool)
    empty_key = _best_time(lambda: empty.rules.position_key(empty.state), number=200)
    stocked_key = _best_time(lambda: stocked.rules.position_key(stocked.state), number=200)

    # Loose absolute ceiling: a single key build must stay far below a
    # millisecond (measured ~8 us; this only trips on a pathological blow-up).
    assert empty_key < 1e-3, f"position_key (empty pool) took {empty_key * 1e6:.1f} us"
    assert stocked_key < 1e-3, f"position_key (stocked pool) took {stocked_key * 1e6:.1f} us"
    # Relative: the pool segment may not multiply the whole cost. The +30 us
    # floor keeps timer resolution from turning a sub-microsecond delta into a
    # ratio failure.
    assert stocked_key <= empty_key * 5 + 3e-5, (
        f"pool made position_key {stocked_key / empty_key:.1f}x slower "
        f"({empty_key * 1e6:.1f} us -> {stocked_key * 1e6:.1f} us)"
    )


# --------------------------------------------------------------------------- #
# 2. evaluate -- P0-F added the pool term to `_evaluate` (hot path).
# --------------------------------------------------------------------------- #

def test_evaluate_single_call_within_loose_budget():
    # Measured: ~9 ms per call on the full 13x13 board. The 50 ms ceiling is a
    # ~5x guardrail: it catches an order-of-magnitude regression, not a wobble.
    game = Game("desktop_complete")
    ai = ChessAI(Difficulty.HARD)

    def evaluate_once() -> None:
        # Clear the memo so we time the real evaluation, not a dict hit.
        ai.evaluation_cache.clear()
        ai._evaluate(game, Color.RED)

    elapsed = _best_time(evaluate_once, repeat=3, number=30)
    assert elapsed < 5e-2, f"_evaluate took {elapsed * 1e3:.1f} ms (budget 50 ms)"


# --------------------------------------------------------------------------- #
# 3. capturable_squares -- point query vs full enumeration (O-6's whole point).
# --------------------------------------------------------------------------- #

def test_point_query_is_far_cheaper_than_full_enumeration():
    # The most valuable case here: `targets=` was added *because* `in_check` is
    # a hot path, so if the point query ever costs as much as a full sweep, the
    # optimisation is gone. Pure ratio -- immune to machine speed.
    # Measured: full ~36 ms, point ~0.76 ms (ratio ~48x).
    game = Game("desktop_complete")
    rules = game.rules
    victim = next(piece for piece in game.state.pieces if piece.color is Color.BLACK).position

    full = _best_time(lambda: rules.capturable_squares(game.state, Color.RED), number=10)
    point = _best_time(
        lambda: rules.capturable_squares(game.state, Color.RED, targets=(victim,)),
        number=30,
    )
    assert point <= full / 10, (
        f"point query {point * 1e6:.1f} us vs full {full * 1e6:.1f} us "
        f"(ratio {full / point:.1f}x, expected >= 10x)"
    )


# --------------------------------------------------------------------------- #
# 4. legal_moves -- full rule-engine generation.
# --------------------------------------------------------------------------- #

def test_legal_moves_full_generation_within_loose_budget():
    # Measured: ~270 ms for the full 13x13 board. 2 s is a ~7x guardrail.
    game = Game("desktop_complete")
    elapsed = _best_time(lambda: game.rules.legal_moves(game.state), repeat=3, number=3)
    assert elapsed < 2.0, f"legal_moves took {elapsed * 1e3:.1f} ms (budget 2000 ms)"


# --------------------------------------------------------------------------- #
# 5. benchmark.acceptance -- the shipped acceptance gate must stay consumable.
# --------------------------------------------------------------------------- #

def test_benchmark_acceptance_schema_is_consumable_at_small_scale():
    """`core/benchmark.py` ships an `acceptance` verdict nobody tested.

    Running the real 50-game match is far too slow for a unit test, so this runs
    a tiny match (2 games, 2 plies, 1 MCTS simulation) purely to prove the
    verdict is produced and *evaluable* -- every gate is a bool, and the 12s
    per-move budget can actually be checked. It does not assert chess strength.
    """
    report = benchmark_master_vs_hard(
        games=2, profile="traditional", max_plies=2, seed=7,
        master_simulations=1, hard_time_scale=0.1,
    )
    acceptance = report["acceptance"]
    assert set(acceptance) == {
        "enoughGames", "enoughCompletedGames",
        "winRateAtLeast55Percent", "masterMoveAtMost12Seconds",
    }
    assert all(isinstance(value, bool) for value in acceptance.values()), acceptance
    # A 2-game match is far below the 50-game gate -- the volume gates must say
    # so honestly rather than being silently skipped.
    assert acceptance["enoughGames"] is False
    assert acceptance["enoughCompletedGames"] is False
    # The per-move budget is the one gate a tiny match can still evaluate; with a
    # single MCTS simulation it trivially holds.
    assert acceptance["masterMoveAtMost12Seconds"] is True
