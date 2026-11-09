"""测量 `max_nodes` 的定标数据（**只测量，不改产品配置**）。

## 为什么需要它

`max_nodes` 要当"常规生效的界"，cap 只兜底 —— 否则截断点由机器速度决定，同一档在
不同机器上强度不同。数值不能拍：`nodes` 与单节点耗时都随局面变化，必须实测反解，
再用**实跑绑定率**选值（不能只靠分位数外推）。

## 两段口径

**A 段（统计）**：cap 设 300s（确保墙钟不绑），跑 `--limit` 个开局 × `--plies` 手，
记录每手 `nodes / wall / completed_depth`。输出：
- nodes 的 p50/p95/p99/p99.9/max；
- 每手 `wall/nodes`（同一手内相除，**不混分位数**）的 p50/p95/max；
- `max_wall_natural`（真实墙钟最大值，用于第 4 类归因）。

**B 段（验证）**：按 `c = floor(cap × 0.85 / rate)` 生成候选（rate 分别取 p50/p95/max），
在目标 cap 下实跑，数 `wallBound / nodesTrunc / degradeMoves / max_wall_over_cap`。
选值：**`wall==0 且 nodesTrunc ≤1% 且 max_wall < cap×0.9` 中 `max_nodes` 最大的一行**；
若初始三候全过，继续向上探 `×1.3`（最多 3 次）直到失败，保证候选里含"会失败的一侧"。

**全败归因**（不要用两个分位数相乘）：
`max_wall_natural > cap×0.9` → `cap_too_small`（报 lead 抬 cap）；
否则 → `depth_too_high`（报 lead 降 depth / 收宽度）。

## 用法

    python scripts/measure_node_budget.py --limit 2 --plies 2   # 联调（秒级）
    python scripts/measure_node_budget.py                        # 完整 64×8（小时级）
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import gen_opening_book as opening_book  # noqa: E402
from level_targets import LEVELS, TARGETS, Tier  # noqa: E402

from xionghan_chess.core.ai import ChessAI  # noqa: E402
from xionghan_chess.core.benchmark import time_stats  # noqa: E402

MEASURE_CAP = 300.0          # A 段"不绑墙钟"的测量 cap
INTERNAL_NODES_RATIO = 0.01  # 选值严于外部门禁（门禁 2%）
INTERNAL_WALL_RATIO = 0.9    # max_wall 距 cap 至少 10%


def percentile(values: list[float], q: float) -> float:
    """nearest-rank 分位数（不插值）——与报告里的 p95 口径一致。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return float(ordered[min(len(ordered) - 1, rank - 1)])


def sweep(level: str, tier: Tier, entries, plies: int, *,
          cap: float, max_nodes: int | None) -> list[dict[str, float | int | str | None]]:
    """在 `cap/max_nodes` 下跑一批局面，逐手记录 nodes / wall / depth / 理由。"""
    config = tier.config(cap=cap, max_nodes=max_nodes)
    records: list[dict[str, float | int | str | None]] = []
    for entry in entries:
        game = opening_book.build_game(entry.profile, entry.seed, entry.plies)
        for _ in range(plies):
            if game.state.finished:
                break
            engine = ChessAI(level, config=config, time_scale=1.0)
            started = time.perf_counter()
            move = engine.choose_move(game)
            wall = time.perf_counter() - started
            records.append({
                "nodes": engine.nodes,
                "qnodes": engine.qnodes,
                "wall": wall,
                "depth": engine.completed_depth,
                "reason": engine.bound_reason,
            })
            if move is None:
                break
            game.move(move)
    return records


def section_a(records: list[dict[str, float | int | str | None]],
              tier: Tier) -> dict[str, object]:
    nodes = [float(r["nodes"]) for r in records if int(r["nodes"]) > 0]
    rates = [float(r["wall"]) / float(r["nodes"])
             for r in records if int(r["nodes"]) > 0]
    walls = [float(r["wall"]) for r in records]
    return {
        "moves": len(records),
        "nodes": {
            "p50": percentile(nodes, 0.50),
            "p95": percentile(nodes, 0.95),
            "p99": percentile(nodes, 0.99),
            "p99_9": percentile(nodes, 0.999),
            "max": max(nodes, default=0.0),
        },
        "rate": {
            "p50": percentile(rates, 0.50),
            "p95": percentile(rates, 0.95),
            "max": max(rates, default=0.0),
        },
        "wall_natural": time_stats(walls),
        "max_wall_natural": max(walls, default=0.0),
        "target_depth": tier.depth,
    }


def section_b(records: list[dict[str, float | int | str | None]],
              tier: Tier) -> dict[str, float | int]:
    total = len(records)
    wall_bound = sum(r["reason"] == "wall" for r in records)
    nodes_trunc = sum(r["reason"] == "nodes" for r in records)
    degrade = sum(int(r["depth"]) < tier.depth for r in records)
    walls = [float(r["wall"]) for r in records]
    return {
        "moves": total,
        "wallBound": wall_bound,
        "nodesTrunc": nodes_trunc,
        "degradeMoves": degrade,
        "maxWallSeconds": max(walls, default=0.0),
        "max_wall_over_cap": round(max(walls, default=0.0) / tier.cap, 4),
        "nodesTruncRatio": nodes_trunc / total if total else 0.0,
    }


def internal_pass(result: dict[str, float | int]) -> bool:
    return (result["wallBound"] == 0
            and result["nodesTruncRatio"] <= INTERNAL_NODES_RATIO
            and result["max_wall_over_cap"] < INTERNAL_WALL_RATIO)


def candidates_from(a: dict[str, object], tier: Tier) -> list[tuple[str, int]]:
    rates = a["rate"]
    assert isinstance(rates, dict)
    out: list[tuple[str, int]] = []
    for source in ("p50", "p95", "max"):
        rate = float(rates[source])
        if rate <= 0:
            continue
        value = math.floor(tier.cap * 0.85 / rate)
        if value > 0:
            out.append((source, value))
    # 去重（保序：p50 → p95 → max 的预算单调递减）并按 max_nodes 从大到小排。
    seen: set[int] = set()
    unique: list[tuple[str, int]] = []
    for source, value in out:
        if value in seen:
            continue
        seen.add(value)
        unique.append((source, value))
    return sorted(unique, key=lambda item: item[1], reverse=True)


def measure_level(level: str, entries, plies: int, *, skip_b: bool) -> dict[str, object]:
    tier = TARGETS[level]
    print(f"[{level}] A 段：{len(entries)} 开局 × {plies} 手，cap={MEASURE_CAP}s（不绑墙钟）",
          flush=True)
    base_records = sweep(level, tier, entries, plies, cap=MEASURE_CAP, max_nodes=None)
    a = section_a(base_records, tier)
    report: dict[str, object] = {
        "level": level,
        "tier": asdict(tier),
        "a": a,
        "candidates": [],
        "selected": None,
        "verdict": None,
    }
    nodes = a["nodes"]
    assert isinstance(nodes, dict)
    print(f"  moves={a['moves']} nodes p50/p95/p99/p99.9/max="
          f"{nodes['p50']:.0f}/{nodes['p95']:.0f}/{nodes['p99']:.0f}/"
          f"{nodes['p99_9']:.0f}/{nodes['max']:.0f}  "
          f"max_wall={a['max_wall_natural']:.2f}s", flush=True)

    if skip_b:
        return report

    candidates = candidates_from(a, tier)
    results: list[dict[str, object]] = []
    print(f"  B 段：cap={tier.cap}s，候选 {[(source, value) for source, value in candidates]}",
          flush=True)
    for source, value in candidates:
        outcome = section_b(
            sweep(level, tier, entries, plies, cap=tier.cap, max_nodes=value), tier)
        outcome.update({"rate_source": source, "max_nodes": value})
        outcome["passes_internal"] = internal_pass(outcome)
        results.append(outcome)

    selected = next((item for item in results if bool(item["passes_internal"])), None)
    if selected is not None and all(bool(item["passes_internal"]) for item in results):
        # 上界没夹住：向上探，直到出现失败（最多 3 次）。
        probe = int(selected["max_nodes"])
        for _ in range(3):
            probe = math.floor(probe * 1.3)
            outcome = section_b(
                sweep(level, tier, entries, plies, cap=tier.cap, max_nodes=probe), tier)
            outcome.update({"rate_source": "probe", "max_nodes": probe})
            outcome["passes_internal"] = internal_pass(outcome)
            results.append(outcome)
            if not outcome["passes_internal"]:
                break
            selected = outcome

    report["candidates"] = results
    report["selected"] = selected
    if selected is None:
        max_wall_natural = float(a["max_wall_natural"])
        report["verdict"] = ("cap_too_small" if max_wall_natural > tier.cap * INTERNAL_WALL_RATIO
                             else "depth_too_high")
    else:
        report["verdict"] = "ok"
    return report


def render_table(report: dict[str, object]) -> str:
    lines = [f"{'candidate':>10} {'rate':>6} {'max_nodes':>9} {'wall':>5} "
             f"{'nodesTrunc':>10} {'degrade':>8} {'maxW/cap':>9} {'pass':>5}"]
    for item in report["candidates"]:  # type: ignore[union-attr]
        lines.append(
            f"{str(item['max_nodes']):>10} {str(item['rate_source']):>6} "
            f"{int(item['max_nodes']):>9} {int(item['wallBound']):>5} "
            f"{int(item['nodesTrunc']):>10} {int(item['degradeMoves']):>8} "
            f"{float(item['max_wall_over_cap']):9.3f} {str(item['passes_internal']):>5}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="测量 max_nodes 定标数据（只读）")
    parser.add_argument("--levels", default=",".join(LEVELS))
    parser.add_argument("--limit", type=int, default=64, help="开局书前 N 条（联调用小值）")
    parser.add_argument("--plies", type=int, default=8)
    parser.add_argument("--skip-b", action="store_true", help="只跑 A 段统计")
    parser.add_argument("--out", default=str(ROOT / "benchmarks" / f"node_budget_{date.today()}.json"))
    args = parser.parse_args(argv)

    book = opening_book.load_book()
    entries = book[: max(1, args.limit)]
    payload: dict[str, object] = {
        "generated": date.today().isoformat(),
        "book": {"size": len(book), "used": min(len(book), args.limit), "plies": args.plies},
        "measure_cap": MEASURE_CAP,
        "levels": {},
    }
    for level in [item.strip() for item in args.levels.split(",") if item.strip()]:
        if level not in TARGETS:
            parser.error(f"未知档位：{level}")
        print("=" * 100, flush=True)
        report = measure_level(level, entries, args.plies, skip_b=args.skip_b)
        payload["levels"][level] = report  # type: ignore[index]
        if not args.skip_b:
            print(render_table(report), flush=True)
        print(f"  verdict={report['verdict']}  selected={report['selected']}", flush=True)

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告：{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
