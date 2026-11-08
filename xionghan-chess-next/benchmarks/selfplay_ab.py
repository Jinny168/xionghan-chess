"""夜间自对弈 A/B：旧 `VALUES`（A）vs 新 `VALUES`（B）。

## 为什么能在同一进程里逐手切换

`ai.VALUES` 是**模块级字典**，`_evaluate` / `static_exchange_score` / SEE 都在**调用时**
读它（`ai.py:504,557,569,684,769,782`），没有任何模块在 import 时把它复制走。
另外 `ChessAI.choose_move` 每次进入都会 `clear()` 掉 TT / evaluation / see / in_check
四张表（`ai.py:201-206`），所以「切字典 + 清缓存 + 再搜索」不会串味。
本脚本仍然显式清一遍缓存，并在冒烟时断言「清完确实是空」——**不依赖实现的清缓存行为**。

## 口径

- 开局：`benchmarks/baseline_2026-10-30/base2_corpus16.json` 的 16 个局面，
  用 `scripts/bench_roots.build_position(profile, seed, plies)` 确定性重建；
- 每个开局 2 局：A 先手一局、B 先手一局（先手 = 该局第一步由谁走，**不改局面轮次**）；
- 预算：固定深度 + 兜底时间上限，**两侧同值**（`CONFIGS[medium]` 的 `dataclasses.replace`，
  只改运行期字典项，不改 `ai.py` 文件）；
- `randomness=0`；
- 结束：终局判定，或达到 `--max-plies` 截断（截断记和棋并单独计数）。

## 产出

JSON：`--out`（默认 `benchmarks/selfplay_ab_<date>.json`），含 `meta / games[] / summary`。
`summary` 给三个数：胜负比、物质差（统一**旧价**计）、功能性棋子平均存活手数。

## 用法

    python benchmarks/selfplay_ab.py --games 2  --depth 2 --time 3 --smoke
    python benchmarks/selfplay_ab.py --games 32 --depth 2 --time 3

只读 `ai.py` / `rules.py` 的接口，不改任何实现文件。
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from xionghan_chess.core import ai as ai_mod  # noqa: E402
from xionghan_chess.core.ai import CONFIGS, ChessAI, Difficulty  # noqa: E402
from xionghan_chess.core.model import Color, PieceType  # noqa: E402
import bench_roots as BR  # noqa: E402

DEFAULT_CORPUS = ROOT / "benchmarks" / "baseline_2026-10-30" / "base2_corpus16.json"

# A 侧（旧价，9c8d0bf）与当前 HEAD（新价 0f00d6b）只有这六项不同，其余一致。
OLD_OVERRIDES = {
    PieceType.THUNDER: 650,
    PieceType.SHIELD: 600,
    PieceType.ASSASSIN: 430,
    PieceType.GUARD: 520,
    PieceType.PATROL: 360,
    PieceType.ARMOR: 420,
}

# 功能性棋子：验证「降价值后是否更早被牺牲」
FUNCTIONAL = (PieceType.SHIELD, PieceType.THUNDER, PieceType.ASSASSIN, PieceType.GUARD)

NEW_VALUES: dict[PieceType, int] = {}
OLD_VALUES: dict[PieceType, int] = {}


def load_values() -> None:
    """抓当前 HEAD 的 VALUES 作为 B，按 OLD_OVERRIDES 造 A。"""
    global NEW_VALUES, OLD_VALUES
    NEW_VALUES = dict(ai_mod.VALUES)
    OLD_VALUES = dict(ai_mod.VALUES)
    OLD_VALUES.update(OLD_OVERRIDES)


def use_values(values: dict[PieceType, int]) -> None:
    """原地改写 `ai.VALUES`（clear+update，不重新绑定）。

    原地改是为了让任何持有该字典引用的调用点
    （如 `static_exchange_score(game, move, VALUES, guard)`）也一起看到新值。
    """
    ai_mod.VALUES.clear()
    ai_mod.VALUES.update(values)


def set_budget(depth: int, seconds: float) -> None:
    """把 medium 档换成「固定深度 + 时间兜底 + 零随机」的同值配置。

    `choose_move` 每次调用都读 `CONFIGS[self.difficulty]`（`ai.py:186`），
    替换字典项即时生效；不碰 `ai.py` 文件。
    """
    base = CONFIGS[Difficulty.MEDIUM]
    CONFIGS[Difficulty.MEDIUM] = replace(base, depth=depth, time_limit=seconds, randomness=0.0)


def clear_caches(engine: ChessAI) -> bool:
    """清空该实例的全部记忆表，返回「evaluation_cache 已确认空」。"""
    for name in ("evaluation_cache", "transposition", "see_cache", "in_check_memo"):
        table = getattr(engine, name, None)
        if table is not None:
            table.clear()
    return not getattr(engine, "evaluation_cache", {})


def material(state, values: dict[PieceType, int], color: Color) -> int:
    """棋盘上某方子力总值（不含阵亡池——池中棋子仍可能复活/升变，另计会重复）。"""
    return sum(values[p.type] for p in state.pieces if p.color is color)


def snapshot(state) -> dict[str, tuple[PieceType, Color]]:
    return {p.id: (p.type, p.color) for p in state.pieces}


def play_game(profile: str, seed: int, plies: int, *, a_color: Color,
              depth: int, seconds: float, max_plies: int) -> dict:
    """从语料局面下完一局：A 执 `a_color`，B 执另一色。"""
    game, _ = BR.build_position(profile, seed, plies)
    engines = {Color.RED: ChessAI(Difficulty.MEDIUM, seed=0),
               Color.BLACK: ChessAI(Difficulty.MEDIUM, seed=0)}
    side_of = {a_color: "A", a_color.opponent: "B"}
    values_of = {"A": OLD_VALUES, "B": NEW_VALUES}
    original = snapshot(game.state)

    alive = dict(original)
    death_ply: dict[str, int] = {}
    cache_clean = True
    switch_log: list[str] = []
    move_log: list[str] = []
    first_mover: str | None = None

    ply = 0
    t0 = time.perf_counter()
    while not game.state.finished and ply < max_plies:
        color = game.state.turn
        who = side_of[color]
        use_values(values_of[who])
        cache_clean &= clear_caches(engines[color])
        switch_log.append(f"{ply + 1}:{who}")
        if first_mover is None:
            first_mover = who
        move = engines[color].choose_move(game, None)
        if move is None:
            break
        game.move(move)
        ply += 1
        move_log.append(f"{who}:{move.key()}")
        now = snapshot(game.state)
        for pid in alive:
            if pid not in now and pid not in death_ply:
                death_ply[pid] = ply
        alive = now
    elapsed = time.perf_counter() - t0

    truncated = not game.state.finished
    winner = game.state.winner
    if truncated:
        result, winner_side = "truncated", None
    elif winner is None:
        result, winner_side = "draw", None
    else:
        result, winner_side = "win", side_of[winner]

    # 物质统一用**旧价**计，避免「各用各的价」把口径差读成实力差
    red_old = material(game.state, OLD_VALUES, Color.RED)
    black_old = material(game.state, OLD_VALUES, Color.BLACK)
    a_old, b_old = (red_old, black_old) if a_color is Color.RED else (black_old, red_old)
    winner_minus_loser = None
    if winner is not None:
        w = red_old if winner is Color.RED else black_old
        l = black_old if winner is Color.RED else red_old
        winner_minus_loser = w - l

    survival: dict[str, dict[str, list[int]]] = {"A": {}, "B": {}}
    for pid, (kind, owner) in original.items():
        if kind not in FUNCTIONAL:
            continue
        end_ply = death_ply.get(pid, ply)  # 活到终局记终局手数
        survival[side_of[owner]].setdefault(kind.value, []).append(end_ply)

    return {
        "profile": profile, "seed": seed, "plies": plies,
        "a_color": a_color.value, "b_color": a_color.opponent.value,
        "first_mover": first_mover,
        "result": result, "winner_side": winner_side,
        "winner_color": winner.value if winner else None,
        "reason": "ply_cap" if truncated else game.state.result_reason,
        "total_plies": ply,
        "material_unified_old": {
            "red": red_old, "black": black_old, "a": a_old, "b": b_old,
            "winner_minus_loser": winner_minus_loser, "a_minus_b": a_old - b_old,
        },
        "material_own_price": {
            "a": material(game.state, OLD_VALUES, a_color),
            "b": material(game.state, NEW_VALUES, a_color.opponent),
        },
        "survival": {k: v for k, v in survival.items()},
        "cache_cleared_every_move": cache_clean,
        "switch_log_head": switch_log[:4],
        "moves": move_log,
        "elapsed_sec": round(elapsed, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="旧 VALUES(A) vs 新 VALUES(B) 自对弈")
    ap.add_argument("--games", type=int, default=32, help="总局数（2 局/开局）")
    ap.add_argument("--depth", type=int, default=2, help="固定搜索深度")
    ap.add_argument("--time", type=float, default=3.0, help="每手时间兜底（秒）")
    ap.add_argument("--max-plies", type=int, default=200, help="截断手数")
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--out", default=str(ROOT / "benchmarks" / f"selfplay_ab_{date.today()}.json"))
    ap.add_argument("--smoke", action="store_true", help="追加打印切价/缓存细节")
    args = ap.parse_args()

    load_values()
    set_budget(args.depth, args.time)

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    openings = max(1, (args.games + 1) // 2)

    games: list[dict] = []
    t_start = time.perf_counter()
    for item in corpus[:openings]:
        if len(games) >= args.games:
            break
        probe, _ = BR.build_position(item["profile"], item["seed"], item["plies"])
        first = probe.state.turn
        for a_color in (first, first.opponent):
            if len(games) >= args.games:
                break
            rec = play_game(item["profile"], item["seed"], item["plies"],
                            a_color=a_color, depth=args.depth, seconds=args.time,
                            max_plies=args.max_plies)
            rec["opening_id"] = item.get("id")
            games.append(rec)
            print(f"[{len(games):2d}/{args.games}] {str(item.get('id'))[:8]} A={rec['a_color']:5s} "
                  f"{rec['result']:9s} winner={str(rec['winner_side']):4s} "
                  f"plies={rec['total_plies']:3d} {rec['elapsed_sec']:6.2f}s", flush=True)

    total = time.perf_counter() - t_start
    wins = {"A": 0, "B": 0, "draw": 0, "truncated": 0}
    for g in games:
        if g["result"] == "truncated":
            wins["truncated"] += 1
        elif g["result"] == "draw":
            wins["draw"] += 1
        else:
            wins[g["winner_side"]] += 1

    diffs = [g["material_unified_old"]["winner_minus_loser"] for g in games
             if g["material_unified_old"]["winner_minus_loser"] is not None]
    survival: dict[str, dict[str, float | None]] = {"A": {}, "B": {}}
    for s in ("A", "B"):
        for kind in FUNCTIONAL:
            vals = [v for g in games for v in g["survival"][s].get(kind.value, [])]
            survival[s][kind.value] = round(statistics.fmean(vals), 2) if vals else None

    summary = {
        "games": len(games),
        "wins": wins,
        "material_diff_unified_old": {
            "mean": round(statistics.fmean(diffs), 1) if diffs else None,
            "median": statistics.median(diffs) if diffs else None,
            "n": len(diffs),
        },
        "survival_plies": survival,
        "elapsed_sec": round(total, 1),
        "sec_per_game": round(total / max(1, len(games)), 2),
    }

    payload = {
        "meta": {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "values_new": {k.value: v for k, v in NEW_VALUES.items()},
            "values_old": {k.value: v for k, v in OLD_VALUES.items()},
            "changed_old_new": {k.value: [OLD_OVERRIDES[k], NEW_VALUES[k]] for k in OLD_OVERRIDES},
            "budget": {"depth": args.depth, "time_limit": args.time,
                       "randomness": 0.0, "max_plies": args.max_plies},
            "corpus": str(args.corpus),
            "openings_used": sorted({str(g.get("opening_id")) for g in games}),
        },
        "games": games,
        "summary": summary,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n=== summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"out: {out}")
    if args.smoke:
        for i, g in enumerate(games, 1):
            print(f"  #{i} cache_cleared={g['cache_cleared_every_move']} "
                  f"first={g['first_mover']} switch={g['switch_log_head']} "
                  f"reason={g['reason']} mat_old={g['material_unified_old']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
