"""`benchmark_match` 泛化门禁：任意两档、成对开局、逐局回调、判据口径不变。

## 为什么不再写死 MASTER vs HARD

标定要对 **6 档里的每一对** 跑 n=50，写死一方等于每换一对就复制一份函数，
复制出来的判据迟早分叉（历史报告里的 `acceptance` 键就是这么变成"只对 master
成立"的）。泛化后必须钉住四件事：

1. **旧调用不改**：`benchmark_master_vs_hard` 仍是薄封装，位置参数照旧；
2. **判据口径不变**：`acceptance` 键集合与阈值仍是历史那一套（`master*` = A 方），
   单步上限由 **A 方预算** 推出（`level_a=master` 时仍是 12.0 × 1.15 = 13.8）；
3. **颜色互换 + 成对开局**：相邻两局同一开局、颜色互换（`book[(i//2) % n]`）；
4. **core 不 import scripts**：开局书必须由调用方注入 `position_builder`，
   缺了要显式报错，不能静默退化成"从初始局面开局"。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.ai import Difficulty, SearchConfig
from xionghan_chess.core.benchmark import (
    MASTER_MOVE_CEILING_SECONDS,
    Opening,
    benchmark_master_vs_hard,
    benchmark_match,
    book_index,
)
from xionghan_chess.core.game import Game

ACCEPTANCE_KEYS = {
    "enoughGames",
    "enoughCompletedGames",
    "winRateAtLeast55Percent",
    "masterMoveAtMost12Seconds",
}


def _cheap_config(time_limit: float = 5.0) -> SearchConfig:
    return SearchConfig(
        depth=1,
        time_limit=time_limit,
        randomness=0.0,
        quiescence_depth=0,
        candidate_count=1,
        branch_limit=1,
        root_limit=2,
    )


def test_any_two_levels_produce_the_legacy_acceptance_schema() -> None:
    seen: list[int] = []
    report = benchmark_match(
        Difficulty.BEGINNER,
        Difficulty.EASY,
        games=2,
        profile="traditional",
        max_plies=2,
        seed=0,
        time_scale=0.1,
        on_game=lambda result: seen.append(result.game),
    )
    assert report["levels"] == {"a": "beginner", "b": "easy"}
    assert set(report["acceptance"]) == ACCEPTANCE_KEYS
    assert all(isinstance(value, bool) for value in report["acceptance"].values())
    assert seen == [1, 2], "on_game 必须逐局回调、顺序一致"
    assert set(report["zeroDepthMoves"]) == {"a", "b"}
    # 2 局远低于 50 局口径：体量门必须诚实说"不够"，不能悄悄跳过。
    assert report["acceptance"]["enoughGames"] is False


def test_book_pairs_openings_and_swaps_colors() -> None:
    calls: list[tuple[str, int, int]] = []

    def builder(profile: str, seed: int, plies: int) -> Game:
        calls.append((profile, seed, plies))
        return Game(profile)

    book = [Opening("traditional", 700, 2), Opening("traditional", 701, 2)]
    report = benchmark_match(
        "beginner",
        "easy",
        games=4,
        profile="traditional",
        max_plies=1,
        seed=0,
        time_scale=0.1,
        book=book,
        position_builder=builder,
    )

    # 相邻两局同一开局（成对），第 3/4 局换下一条 —— 50 局才能拿到 25 个不同起点。
    assert calls == [("traditional", 700, 2), ("traditional", 700, 2), ("traditional", 701, 2), ("traditional", 701, 2)]
    assert [item["master_color"] for item in report["results"]] == [
        "red",
        "black",
        "red",
        "black",
    ]
    assert report["book"] == {
        "size": 2,
        "used": ["traditional#700@2", "traditional#700@2", "traditional#701@2", "traditional#701@2"],
    }


def test_book_without_builder_fails_loudly() -> None:
    with pytest.raises(ValueError, match="position_builder"):
        benchmark_match("beginner", "easy", games=1, book=[Opening("traditional", 700, 2)])


def test_start_game_keeps_absolute_numbering() -> None:
    """分块跑 `start_game=0,5,10,...` 必须与一次跑完逐局等价：编号/颜色都取绝对索引。"""
    seen: list[tuple[int, str]] = []
    report = benchmark_match(
        "beginner",
        "easy",
        games=1,
        profile="traditional",
        max_plies=1,
        seed=0,
        time_scale=0.1,
        start_game=3,
        a_simulations=1,
        on_game=lambda result: seen.append((result.game, result.master_color)),
    )
    assert seen == [(4, "black")], "第 4 局（索引 3）A 方执黑"
    assert report["results"][0]["game"] == 4


def test_ceiling_follows_side_a_budget_not_the_master_constant() -> None:
    """泛化后单步上限由 A 方预算推出；0.5s 的档位不能被 13.8s 的常量豁免。"""
    a_config = _cheap_config(time_limit=2.0)
    report = benchmark_match("beginner", "easy", games=0, a_config=a_config)
    assert report["masterMoveCeilingSeconds"] == pytest.approx(2.3)
    assert report["aMoveCeilingSeconds"] == pytest.approx(2.3)


def test_legacy_wrapper_still_targets_master_vs_hard() -> None:
    """旧封装仍是 `MASTER vs HARD`，且 `level_a=master` 的上限就是历史常量。"""
    report = benchmark_master_vs_hard(games=0)
    assert report["levels"] == {"a": "master", "b": "hard"}
    assert report["masterMoveCeilingSeconds"] == MASTER_MOVE_CEILING_SECONDS
    # 旧脚本按位置参数调用（games, profile, max_plies, seed, scale, simulations,
    # on_game, start_game）——签名必须继续吃下这 8 个位置参数。
    again = benchmark_master_vs_hard(0, "traditional", 2, 7, 0.1, 1, None, 0)
    assert again["games"] == 0


def test_injected_configs_are_used_and_globals_stay_clean() -> None:
    """两侧都注入 config 跑一局：全局 CONFIGS 不变，且没有"一手都没搜完"的退化。

    `zeroDepthMoves == 0` 是**行为证据**：这份配置 depth 1 / 5s 一定搜得完；
    若 benchmark 没把 `b_config` 传下去（或某处又回头读全局表拿到 12s/hard 的
    参数），计数不会是 0 而会随机器负载漂。
    """
    from xionghan_chess.core.ai import CONFIGS

    before = dict(CONFIGS)
    report = benchmark_match(
        "beginner",
        "easy",
        games=1,
        profile="traditional",
        max_plies=2,
        seed=0,
        time_scale=0.1,
        a_config=_cheap_config(),
        b_config=_cheap_config(),
    )
    assert CONFIGS == before
    assert report["zeroDepthMoves"] == {"a": 0, "b": 0}
    assert report["results"][0]["plies"] >= 1


def test_book_index_spreads_evenly_and_mixes_plies() -> None:
    """等距取样：n=64 用满 32 个 seed、plies 16/16；n=50 → 25 seed、14/11。"""
    book = [Opening("p", 700 + seed, plies) for seed in range(32) for plies in (6, 10)]
    expected = {
        32: {"openings": 16, "seeds": 16, "plies6": 8},
        50: {"openings": 25, "seeds": 25, "plies6": 14},
        64: {"openings": 32, "seeds": 32, "plies6": 16},
        96: {"openings": 48, "seeds": 32, "plies6": 24},
    }
    for games, spec in expected.items():
        used = [book[book_index(index, games, len(book))] for index in range(games)]
        unique = {(entry.seed, entry.plies) for entry in used}
        assert len(unique) == spec["openings"]
        assert len({entry.seed for entry in used}) == spec["seeds"]
        assert sum(plies == 6 for _seed, plies in unique) == spec["plies6"]
        assert {entry.plies for entry in used} == {6, 10}, "两档 plies 必须都进入样本"


def test_report_carries_reason_ledgers_and_move_time_stats() -> None:
    """截断原因分账 + 耗时统计：median/p95 只用**未截断**的手。"""
    zero_budget = SearchConfig(
        depth=2, time_limit=1e-9, randomness=0.0, quiescence_depth=0, candidate_count=1, branch_limit=1, root_limit=2
    )
    report = benchmark_match(
        "beginner",
        "easy",
        games=1,
        profile="traditional",
        max_plies=1,
        seed=0,
        a_config=zero_budget,
        b_config=_cheap_config(),
    )
    assert report["boundReasons"]["a"]["wall"] >= 1
    assert report["zeroDepthReasons"]["a"]["wall"] >= 1
    assert report["totalMoves"]["a"] == 1
    stats = report["moveTimeStats"]["a"]
    assert stats["n"] == 0, "被墙钟截断的手不能进 median/p95（它代表预算，不代表档位）"
    assert set(stats) == {"n", "median", "p95", "max"}
    # 全量耗时仍保留（acceptance 的 max 判据要用）
    assert len(report["results"][0]["a_move_times"]) == 1
    assert report["results"][0]["a_clean_move_times"] == []


def test_clean_move_times_exclude_truncated_moves() -> None:
    report = benchmark_match(
        "beginner",
        "easy",
        games=1,
        profile="traditional",
        max_plies=1,
        seed=0,
        a_config=_cheap_config(),
        b_config=_cheap_config(),
    )
    stats = report["moveTimeStats"]["a"]
    assert stats["n"] == 1
    assert stats["median"] == stats["p95"] == stats["max"]


def test_chunked_run_uses_total_games_for_book_sampling() -> None:
    """分块跑（start_game=32）必须与整批的 [32:64] 用同一批开局。"""
    book = [Opening("p", 700 + seed, plies) for seed in range(32) for plies in (6, 10)]
    calls: list[tuple[str, int, int]] = []

    def builder(profile: str, seed: int, plies: int) -> Game:
        calls.append((profile, seed, plies))
        return Game("traditional")

    report = benchmark_match(
        "beginner", "easy", games=32, start_game=32, total_games=64, max_plies=0, book=book, position_builder=builder
    )
    expected = [
        f"{entry.profile}#{entry.seed}@{entry.plies}"
        for entry in (book[book_index(i, 64, len(book))] for i in range(32, 64))
    ]
    assert report["book"]["used"] == expected
    assert len(report["book"]["used"]) == 32
    assert all(index < 64 for index in (book_index(i, 64, len(book)) for i in range(32, 64)))


def test_calibration_clock_can_be_raised_for_product_caps() -> None:
    """产品 hard 12s×50 手会超过默认 10 分钟包干；标定必须能显式放大时钟。"""
    from xionghan_chess.core.benchmark import _starting_game

    game = _starting_game(0, 1, "traditional", None, None, initial_minutes=180)
    assert set(game.state.clocks_ms.values()) == {180 * 60_000}


def test_result_rows_carry_completed_depth_and_wall_moves() -> None:
    """逐局 JSONL 必须能看出"实际完成几层"，否则只看到 wall 占比。"""
    report = benchmark_match(
        Difficulty.BEGINNER,
        Difficulty.MEDIUM,
        games=2,
        max_plies=2,
        a_config=_cheap_config(1.0),
        b_config=_cheap_config(1.0),
    )
    row = report["results"][0]
    assert "a_completed_depth" in row and "b_completed_depth" in row
    assert "a_wall_moves" in row and "b_wall_moves" in row
    assert 0 <= row["a_completed_depth"] <= 1
    assert 0 <= row["b_completed_depth"] <= 1
    assert row["a_wall_moves"] <= row["a_moves"]
    assert row["b_wall_moves"] <= row["b_moves"]
    assert len(row["a_zero_depth_flags"]) == row["a_moves"]
    assert len(row["b_zero_depth_flags"]) == row["b_moves"]


def test_k3_counts_a_hanging_horse(monkeypatch) -> None:
    """A 走一步把马留在黑車口里 → a_blunders=1、hang_share=1。"""
    from xionghan_chess.core.ai import ChessAI
    from xionghan_chess.core.benchmark import Opening
    from xionghan_chess.core.model import Color, GameState, Piece, PieceType

    state = GameState(
        "traditional",
        [
            Piece.create(PieceType.KING, Color.RED, 9, 4),
            Piece.create(PieceType.HORSE, Color.RED, 5, 4),
            Piece.create(PieceType.KING, Color.BLACK, 0, 4),
            Piece.create(PieceType.ROOK, Color.BLACK, 5, 0),
        ],
        turn=Color.RED,
    )

    def choose_king_move(self, game, cancel=None):
        # 只走王，故意不救 5,4 的马。
        return next(
            move
            for move in game.rules.legal_moves(game.state)
            if game.state.piece_at(move.source).type is PieceType.KING
        )

    monkeypatch.setattr(ChessAI, "choose_move", choose_king_move)
    report = benchmark_match(
        Difficulty.BEGINNER,
        Difficulty.MEDIUM,
        games=1,
        max_plies=1,
        a_config=_cheap_config(1.0),
        b_config=_cheap_config(1.0),
        book=[Opening("traditional", 0, 0)],
        position_builder=lambda profile, seed, plies: Game.from_state(state),
    )

    row = report["results"][0]
    assert row["a_blunders"] >= 1
    assert row["a_blunder_hangs"] >= 1
    assert report["aBlunderHangShare"] > 0


def test_k3b_gap_stats_are_reported() -> None:
    """K3-b：每手与最佳根着法的分差要能出 p50/p90/≥450 占比。"""
    report = benchmark_match(
        Difficulty.BEGINNER,
        Difficulty.MEDIUM,
        games=2,
        max_plies=4,
        a_config=_cheap_config(1.0),
        b_config=_cheap_config(1.0),
    )
    for side in ("a", "b"):
        stats = report[f"{side}GapStats"]
        assert set(stats) == {"p50", "p90", "ge450Share"}
        assert 0.0 <= stats["ge450Share"] <= 1.0
        assert stats["p50"] <= stats["p90"]
