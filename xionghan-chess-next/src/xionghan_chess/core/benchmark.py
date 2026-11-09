from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from .ai import CONFIGS, ChessAI, Difficulty, SearchConfig
from .game import Game
from .mcts import MCTS
from .model import Color

# 单步耗时判据的容差与上限。
#
# `CONFIGS[MASTER].time_limit` 是搜索的**软预算**：MCTS 在 deadline 之后还要完成
# 当前节点的展开与反向传播，加上 Python 层开销，必然越过 deadline。满预算 50 局
# 实测峰值 13.645 s 对 12.0 s 超 13.7%（首轮 2 局探针只有 3%，随对局变长而上升）。
# 把这种不可避免的收尾开销记成缺陷，等于让判据永远无法通过 —— 判据应约束
# 「不得显著超预算」，故取 `time_limit × (1 + 15%)`。
#
# 注意：该判据只对**时间受限**搜索有意义。传 `a_simulations` 时按模拟次数
# 收敛、耗时由局面复杂度决定，验收口径不使用该参数。
MASTER_MOVE_TIME_TOLERANCE = 0.15
MASTER_MOVE_CEILING_SECONDS = round(
    CONFIGS[Difficulty.MASTER].time_limit * (1 + MASTER_MOVE_TIME_TOLERANCE), 3
)

# 开局书里的一条：`Game(profile)` 走 `build_position(profile, seed, plies)` 生成。
# `fp` 是生成时的局面指纹（`RulesEngine.position_key`）——只用于**核对重建是否一致**，
# 运行对局时不消费；有了它，"这条开局还是当初那条"才可验证。


@dataclass(frozen=True, slots=True)
class Opening:
    profile: str
    seed: int
    plies: int
    fp: str | None = None


# 由调用方提供局面生成器：`core` 不 import `scripts/`（分层），
# 所以 book 的构造方式必须**注入**而不是在此处写死。
PositionBuilder = Callable[[str, int, int], Game]
GameHook = Callable[["MatchResult"], None]


@dataclass(slots=True)
class MatchResult:
    """逐局结果。

    字段名沿用历史报告（`master_*` = **A 方**、`hard_*` = **B 方**）：
    `scripts/benchmark_ai.py --summarize` 与既有 JSONL 都按这套键读，
    泛化对局双方时改名会让旧报告读不出来。
    """

    game: int
    master_color: str
    winner: str | None
    adjudicated: bool
    plies: int
    master_seconds: float
    hard_seconds: float
    # 逐手耗时随局落盘：`--resume` 后仍能精确重算 median/p95（不能由 mean 反推）。
    # 旧 JSONL 没有这两个键，`scripts/benchmark_ai.py --summarize` 不读它们，兼容。
    a_move_times: list[float] = field(default_factory=list)
    b_move_times: list[float] = field(default_factory=list)
    # 逐局截断账本：`--resume` 后仍能汇总"这批数据能不能引用"。
    # 键：wall / nodes / cancel；`*_moves` 是该方总着数（算 nodes 占比的分母）。
    a_bound_reasons: dict[str, int] = field(default_factory=dict)
    b_bound_reasons: dict[str, int] = field(default_factory=dict)
    a_zero_depth_reasons: dict[str, int] = field(default_factory=dict)
    b_zero_depth_reasons: dict[str, int] = field(default_factory=dict)
    a_moves: int = 0
    b_moves: int = 0


def _move_ceiling(level_a: Difficulty, a_config: SearchConfig | None) -> float:
    """A 方单步耗时上限 = A 方预算 × (1 + 容差)。

    历史常量 `MASTER_MOVE_CEILING_SECONDS` 就是本式在 `level_a=master` 处的取值
    （12.0 × 1.15 = 13.8）；泛化到任意两档时不能继续拿 13.8 去判 0.5s 的档位。
    """
    budget = (a_config or CONFIGS[level_a]).time_limit
    return round(budget * (1 + MASTER_MOVE_TIME_TOLERANCE), 3)


def book_index(game_index: int, games: int, size: int) -> int:
    """第 `game_index` 局用开局书的哪一条：**等距、端点含**，不是"前 N 条"。

    旧写法 `(i // 2) % size` 在 n=50 时只用到前 25 条（书有 64 条），后 39 条一次不进。
    书按 `seed 主序 × plies` 排列时，"取前 N"还会让 n 较小的一批集中在前几个 seed。

    规则：
    - `openings = min(max(1, games // 2), size)`；局数超过书容量才允许复用；
    - 否则 `idx = round(k * (size-1) / (openings-1))`，`k = i // 2`（相邻两局同一开局）；
    - n=50 → 25 条、n=64 → 32 条、n=96 → 48 条；`index` 覆盖首尾。
    """
    if size <= 0:
        raise ValueError("开局书不能为空")
    if games // 2 >= size:
        return (game_index // 2) % size
    openings = min(max(1, games // 2), size)
    if openings == 1:
        return 0
    step = (size - 1) / (openings - 1)
    return round((game_index // 2) * step)


def _starting_game(game_index: int, games: int, profile: str,
                   book: Sequence[Opening] | None,
                   position_builder: PositionBuilder | None) -> Game:
    """第 `game_index` 局的起始局面（无 book 时从初始局面开局）。"""
    if book is None:
        return Game(profile)
    if position_builder is None:
        raise ValueError(
            "book 需要 position_builder：core 不 import scripts/bench_roots（分层），"
            "请由调用方注入，例如 "
            "position_builder=lambda p, s, n: bench_roots.build_position(p, s, n)[0]"
        )
    entry = book[book_index(game_index, games, len(book))]
    return position_builder(entry.profile, entry.seed, entry.plies)


def wilson_interval(wins: int, games: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% 置信区间（闭式，无第三方依赖）。

    小样本下正态近似会产生负下界（0/50 时尤其明显），Wilson 不会。边界：
    `0/50 → (0, 0.0714)`、`50/50 → (0.9286, 1.0)`。
    """
    if games <= 0:
        return (0.0, 0.0)
    if wins < 0 or wins > games:
        raise ValueError(f"wins={wins} 超出 [0, {games}]")
    p = wins / games
    denominator = 1 + z * z / games
    center = (p + z * z / (2 * games)) / denominator
    half = z * math.sqrt(p * (1 - p) / games + z * z / (4 * games * games)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def elo_from_win_rate(rate: float) -> float | None:
    """胜率 → Elo 差（`-400·log10(1/p - 1)`）；`p=0`/`p=1` 无定义，返回 `None`。

    不返回 `inf`：`inf` 会污染后续均值/中位数，调用方也没法区分"极强"和"算错了"。
    """
    if rate <= 0.0 or rate >= 1.0:
        return None
    return -400.0 * math.log10(1.0 / rate - 1.0)


def time_stats(values: Sequence[float]) -> dict[str, float | int]:
    """median / p95 / max（p95 用 nearest-rank，不插值）。

    三个数的分工（S4-2 定稿）：median 喂 `EXPECTED_MOVE_SECONDS`；p95 只作参考；
    max 只为兼容旧报告。**不能由 mean 推 median/p95。**
    """
    if not values:
        return {"n": 0, "median": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    count = len(ordered)
    rank = max(1, math.ceil(0.95 * count))
    return {
        "n": count,
        "median": float(statistics.median(ordered)),
        "p95": float(ordered[min(count - 1, rank - 1)]),
        "max": float(ordered[-1]),
    }


def benchmark_match(level_a: Difficulty | str = Difficulty.MASTER,
                    level_b: Difficulty | str = Difficulty.HARD,
                    games: int = 50, profile: str = "traditional",
                    max_plies: int = 240, seed: int = 0,
                    time_scale: float = 1.0,
                    a_simulations: int | None = None,
                    a_config: SearchConfig | None = None,
                    b_config: SearchConfig | None = None,
                    book: Sequence[Opening] | None = None,
                    position_builder: PositionBuilder | None = None,
                    on_game: GameHook | None = None,
                    start_game: int = 0) -> dict[str, Any]:
    """跑一场**任意两档**之间的对局，返回机器可读的验收数据。

    口径（与历史 `master vs hard` 完全一致，只是双方可换）：

    - **颜色互换**：`game_index` 偶数 A 执红、奇数执黑（`start_game` 是绝对编号，
      所以分块跑 `start_game=0,5,10,...` 与一次跑完逐局等价）；
    - **静态裁决**：`max_plies` 内未分胜负 → 用评估函数按 ±100 判红/黑/和；
    - **`acceptance`**：键与阈值沿用历史报告（`master*` = A 方）；
    - **`book`**：开局集（`Opening` 或注入 `position_builder` 的等价列表），
      不传则每局从初始局面开局；
    - **`a_config` / `b_config`**：实例级配置注入（见 `ChessAI`），标定只改这两个，
      不改全局 `CONFIGS`；
    - **`on_game`**：每局结束回调（长对局可逐局落盘，崩溃不丢已完成局）。

    `time_scale` 作用于**双方**，通过 `ChessAI(time_scale=...)` 注入实例，
    **不再写 `os.environ`**（进程级环境变量会让同进程并行的两场对局互相串）。
    传 `a_simulations` 时 A 方改走 MCTS 固定模拟次数。
    """
    level_a, level_b = Difficulty(level_a), Difficulty(level_b)
    if book is not None and position_builder is None:
        # 显式失败，不要静默退化成"从初始局面开局"——否则整批标定用了错的起点。
        raise ValueError("book 需要 position_builder（见 benchmark_match 文档）")
    a_ceiling = _move_ceiling(level_a, a_config)

    results: list[MatchResult] = []
    a_move_times: list[float] = []
    b_move_times: list[float] = []
    # 诊断账本：
    #   zeroDepth* = 一手都没搜完（强退化信号）；
    #   bound*     = 任何一手被截断（判据用，不论 depth）；
    #   totalMoves 用来算 nodesTrunc/totalMoves ≤2% 的比率。
    zero_depth = {"a": 0, "b": 0}
    zero_depth_reasons = {"a": {"wall": 0, "nodes": 0, "cancel": 0},
                          "b": {"wall": 0, "nodes": 0, "cancel": 0}}
    bound_reasons = {"a": {"wall": 0, "nodes": 0, "cancel": 0},
                     "b": {"wall": 0, "nodes": 0, "cancel": 0}}
    total_moves = {"a": 0, "b": 0}
    used_openings: list[Opening] = []
    for game_index in range(start_game, start_game + games):
        game = _starting_game(game_index, games, profile, book, position_builder)
        if book is not None:
            used_openings.append(book[book_index(game_index, games, len(book))])
        a_color = Color.RED if game_index % 2 == 0 else Color.BLACK
        totals = {"a": 0.0, "b": 0.0}
        game_times: dict[str, list[float]] = {"a": [], "b": []}
        game_bound = {"a": {"wall": 0, "nodes": 0, "cancel": 0},
                      "b": {"wall": 0, "nodes": 0, "cancel": 0}}
        game_zero = {"a": {"wall": 0, "nodes": 0, "cancel": 0},
                     "b": {"wall": 0, "nodes": 0, "cancel": 0}}
        game_moves = {"a": 0, "b": 0}
        for ply in range(max_plies):
            if game.state.finished:
                break
            is_a = game.state.turn is a_color
            side = "a" if is_a else "b"
            started = time.perf_counter()
            if is_a and a_simulations is not None:
                # 固定模拟次数：A 方走 MCTS，评分器借 B 方实例的 SEE（与档位无关）。
                scorer = ChessAI(level_b, config=b_config)._see_score
                move = MCTS(simulations=a_simulations,
                            seed=seed + game_index * max_plies + ply,
                            root_score=scorer).choose_move(game)
            else:
                level, config = (level_a, a_config) if is_a else (level_b, b_config)
                engine = ChessAI(level, seed=seed + game_index * max_plies + ply,
                                 config=config, time_scale=time_scale)
                move = engine.choose_move(game)
                total_moves[side] += 1
                game_moves[side] += 1
                if engine.zero_depth_moves:
                    zero_depth[side] += engine.zero_depth_moves
                    reason = engine.zero_depth_reason or "wall"
                    zero_depth_reasons[side][reason] += 1
                    game_zero[side][reason] += 1
                if engine.bound_reason is not None:
                    bound_reasons[side][engine.bound_reason] += 1
                    game_bound[side][engine.bound_reason] += 1
            elapsed = time.perf_counter() - started
            bucket = a_move_times if is_a else b_move_times
            bucket.append(elapsed)
            game_times[side].append(elapsed)
            totals[side] += elapsed
            if move is None:
                break
            game.move(move)
        adjudicated = not game.state.finished
        winner = game.state.winner
        if adjudicated:
            score = ChessAI(level_b)._evaluate(game, Color.RED)
            winner = Color.RED if score > 100 else Color.BLACK if score < -100 else None
        result = MatchResult(
            game_index + 1, a_color.value, winner.value if winner else None,
            adjudicated, len(game.state.history), totals["a"], totals["b"],
            game_times["a"], game_times["b"],
            game_bound["a"], game_bound["b"], game_zero["a"], game_zero["b"],
            game_moves["a"], game_moves["b"],
        )
        results.append(result)
        if on_game is not None:
            on_game(result)
    a_wins = sum(item.winner == item.master_color for item in results)
    b_wins = sum(item.winner is not None and item.winner != item.master_color
                 for item in results)
    draws = len(results) - a_wins - b_wins
    decisive = a_wins + b_wins
    completed_games = sum(not item.adjudicated for item in results)
    return {
        "games": games,
        "levels": {"a": level_a.value, "b": level_b.value},
        "masterWins": a_wins, "hardWins": b_wins, "draws": draws,
        "masterWinRate": a_wins / games if games else 0.0,
        "masterDecisiveWinRate": a_wins / decisive if decisive else 0.0,
        "masterMoveMeanSeconds": statistics.fmean(a_move_times) if a_move_times else 0.0,
        "masterMoveMaxSeconds": max(a_move_times, default=0.0),
        "masterMoveCeilingSeconds": a_ceiling,
        "aMoveCeilingSeconds": a_ceiling,
        "hardMoveMeanSeconds": statistics.fmean(b_move_times) if b_move_times else 0.0,
        "hardMoveMaxSeconds": max(b_move_times, default=0.0),
        "completedGames": completed_games,
        "adjudicatedGames": sum(item.adjudicated for item in results),
        # 诊断：A/B 各自"一手都没搜完"的着数。>0 说明该档预算低于一次排序成本，
        # 选点退化成排序首着 —— 这时讨论"棋力"没有意义，先看预算。
        "zeroDepthMoves": dict(zero_depth),
        # 判据账本：`boundReasons.wall > 0` → 本批不可引用；`nodes` 触发占比 ≤2%。
        "zeroDepthReasons": zero_depth_reasons,
        "boundReasons": bound_reasons,
        "totalMoves": total_moves,
        "moveTimeStats": {"a": time_stats(a_move_times), "b": time_stats(b_move_times)},
        "book": None if book is None else {
            "size": len(book),
            "used": [f"{entry.profile}#{entry.seed}@{entry.plies}"
                     for entry in used_openings],
        },
        "acceptance": {
            "enoughGames": games >= 50,
            "enoughCompletedGames": completed_games >= 50,
            "winRateAtLeast55Percent": completed_games >= 50 and a_wins / games >= 0.55,
            # 键名沿用历史报告；阈值以 `masterMoveCeilingSeconds` 为准。
            "masterMoveAtMost12Seconds": max(a_move_times, default=0.0) <= a_ceiling,
        },
        "results": [asdict(item) for item in results],
    }


def benchmark_master_vs_hard(games: int = 50, profile: str = "traditional",
                             max_plies: int = 240, seed: int = 0,
                             hard_time_scale: float = 1.0,
                             master_simulations: int | None = None,
                             on_game: GameHook | None = None,
                             start_game: int = 0,
                             book: Sequence[Opening] | None = None,
                             position_builder: PositionBuilder | None = None,
                             ) -> dict[str, Any]:
    """`benchmark_match(MASTER, HARD)` 的薄封装：旧调用（含位置参数）一律不改。"""
    return benchmark_match(
        Difficulty.MASTER, Difficulty.HARD,
        games=games, profile=profile, max_plies=max_plies, seed=seed,
        time_scale=hard_time_scale, a_simulations=master_simulations,
        book=book, position_builder=position_builder,
        on_game=on_game, start_game=start_game,
    )
