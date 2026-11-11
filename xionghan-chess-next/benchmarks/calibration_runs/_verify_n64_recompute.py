"""n=64 终验独立复算工具（只读数据产物，不修改任何产品代码）。

从 .jsonl 逐行重算所有验收字段，并与 .report.json 逐项对照。
刻意 **不调用** calibrate_levels.summarize —— 否则等于用同一份逻辑自证。

用法：
    PYTHONPATH=src .venv/Scripts/python.exe \
        benchmarks/calibration_runs/_verify_n64_recompute.py <checkpoint.jsonl> [report.json] [target_n]
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# 只取带宽常量（单一真相源）；判定公式全部在本文件独立重算，不调用 summarize / band_pass。
from calibrate_levels import BAND_HIGH, BAND_LOW  # noqa: E402


# ---- 独立实现的数学口径（与 core/benchmark.py 同公式，但不 import 它） ----

def wilson(wins: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = wins / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, center - half), min(1.0, center + half))


def nearest_rank(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return float(ordered[min(len(ordered) - 1, rank - 1)])


def time_stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"n": 0, "median": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "median": float(statistics.median(ordered)),
        "p95": nearest_rank(values, 0.95),
        "max": float(ordered[-1]),
    }


def clean_times(rows: list[dict], side: str) -> list[float]:
    clean = [float(v) for r in rows for v in (r.get(f"{side}_clean_move_times") or [])]
    if clean:
        return clean
    return [float(v) for r in rows for v in (r.get(f"{side}_move_times") or [])]


def max_true_run(flags: list[bool]) -> int:
    best = run = 0
    for flag in flags:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def aggregate(rows: list[dict], side: str, key: str) -> dict[str, int]:
    out = {"wall": 0, "nodes": 0, "cancel": 0}
    for r in rows:
        d = r.get(f"{side}_{key}") or {}
        for k in out:
            out[k] += int(d.get(k, 0))
    return out


def flags_of(rows: list[dict], side: str) -> list[bool]:
    return [bool(f) for r in rows for f in (r.get(f"{side}_zero_depth_flags") or [])]


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


# ---- 主复算 ----

def recompute(rows: list[dict], target_n: int = 64, tiers: str = "product") -> dict:
    n = len(rows)
    wins = sum(r.get("winner") == r.get("master_color") for r in rows)
    losses = sum(r.get("winner") is not None and r.get("winner") != r.get("master_color") for r in rows)
    draws = n - wins - losses
    score = wins + 0.5 * draws
    point = score / n if n else 0.0
    low, high = wilson(score, n)
    elo = None if point <= 0.0 or point >= 1.0 else -400.0 * math.log10(1.0 / point - 1.0)

    a_moves = sum(int(r.get("a_moves", 0)) for r in rows)
    b_moves = sum(int(r.get("b_moves", 0)) for r in rows)
    a_bound = aggregate(rows, "a", "bound_reasons")
    b_bound = aggregate(rows, "b", "bound_reasons")
    a_zero = aggregate(rows, "a", "zero_depth_reasons")
    b_zero = aggregate(rows, "b", "zero_depth_reasons")
    a_flags, b_flags = flags_of(rows, "a"), flags_of(rows, "b")
    a_zero_count = sum(a_flags) if a_flags else sum(a_zero.values())
    b_zero_count = sum(b_flags) if b_flags else sum(b_zero.values())
    a_rate = a_zero_count / a_moves if a_moves else 0.0
    b_rate = b_zero_count / b_moves if b_moves else 0.0
    a_consec = max(
        max((int(r.get("a_zero_depth_max_consecutive", 0)) for r in rows), default=0),
        max_true_run(a_flags),
    )
    b_consec = max(
        max((int(r.get("b_zero_depth_max_consecutive", 0)) for r in rows), default=0),
        max_true_run(b_flags),
    )
    a_gt1 = sum(1 for r in rows if sum(bool(f) for f in (r.get("a_zero_depth_flags") or [])) > 1)
    b_gt1 = sum(1 for r in rows if sum(bool(f) for f in (r.get("b_zero_depth_flags") or [])) > 1)
    k2 = a_moves >= 300 and b_moves >= 300

    total_moves = a_moves + b_moves
    wall_moves = a_bound["wall"] + b_bound["wall"]
    wall_percent = round(100.0 * wall_moves / total_moves, 2) if total_moves else 0.0
    nodes_ratio_a = a_bound["nodes"] / a_moves if a_moves else 0.0
    nodes_ratio_b = b_bound["nodes"] / b_moves if b_moves else 0.0
    wall_enforced = tiers == "target"

    gates = {
        "enoughGames": n >= target_n,
        "wallClean": wall_moves == 0,
        "wallCleanEnforced": wall_enforced,
        "noZeroDepth": sum(a_zero.values()) == 0 and sum(b_zero.values()) == 0,
        "nodesRatioAtMost2Percent": nodes_ratio_a <= 0.02 and nodes_ratio_b <= 0.02,
        "zeroDepthEvaluated": k2,
        "zeroDepthRateAtMost1Percent": (a_rate <= 0.01 and b_rate <= 0.01) if k2 else True,
        "zeroDepthNoConsecutive": (a_consec <= 1 and b_consec <= 1) if k2 else True,
        "zeroDepthAtMostOnePerGame": (a_gt1 == 0 and b_gt1 == 0) if k2 else True,
    }
    # v2 强档方向：A 常排弱档，不能拿 A 的 point 直接判；Wilson 对称故 strong_low 取 max。
    strong_side = "a" if point >= 0.5 else "b"
    strong_score = max(point, 1.0 - point)
    strong_low = max(low, 1.0 - high)
    win_rate_pass = strong_score >= 0.60 and strong_low >= 0.50
    script_pass = (
        win_rate_pass
        and gates["enoughGames"]
        and (gates["wallClean"] or not wall_enforced)
        and gates["noZeroDepth"]
        and gates["nodesRatioAtMost2Percent"]
        and gates["zeroDepthRateAtMost1Percent"]
        and gates["zeroDepthNoConsecutive"]
        and gates["zeroDepthAtMostOnePerGame"]
    )
    band_pass = BAND_LOW <= strong_score <= BAND_HIGH
    contract_pass = script_pass and band_pass
    contract_failed_gates = (
        []
        if band_pass
        else [
            f"band: {strong_score:.4f} > {BAND_HIGH:.2f}"
            if strong_score > BAND_HIGH
            else f"band: {strong_score:.4f} < {BAND_LOW:.2f}"
        ]
    )

    hangs = {}
    for side in ("a", "b"):
        for kind in ("raw_hangs", "avoidable_hangs"):
            vals = [int(r.get(f"{side}_{kind}", 0)) for r in rows]
            hangs[f"{side}_{kind}"] = {"sum": sum(vals), "per_game": mean([float(v) for v in vals])}

    gaps = {}
    for side in ("a", "b"):
        vals = [float(v) for r in rows for v in (r.get(f"{side}_gaps") or [])]
        gaps[side] = {
            "n": len(vals),
            "p50": float(statistics.median(vals)) if vals else 0.0,
            "p90": nearest_rank(vals, 0.90),
            "ge450": sum(1 for v in vals if v >= 450),
            "ge450_rate": (sum(1 for v in vals if v >= 450) / len(vals)) if vals else 0.0,
        }

    depth = {
        side: mean([float(r.get(f"{side}_completed_depth", 0)) for r in rows])
        for side in ("a", "b")
    }

    return {
        "games": n,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "score": score,
        "winRate": round(point, 4),
        "wilson95": [round(low, 4), round(high, 4)],
        "elo": (None if elo is None else round(elo, 1) or 0.0),
        "winRatePass": win_rate_pass,
        "strongSide": strong_side,
        "strongScore": round(strong_score, 4),
        "strongLow": round(strong_low, 4),
        "bandPass": band_pass,
        "contractPass": contract_pass,
        "contractFailedGates": contract_failed_gates,
        "gates": gates,
        "pass": script_pass,
        "moveTimes": {"a": time_stats(clean_times(rows, "a")), "b": time_stats(clean_times(rows, "b"))},
        "boundReasons": {"a": a_bound, "b": b_bound},
        "zeroDepthReasons": {"a": a_zero, "b": b_zero},
        "moves": {"a": a_moves, "b": b_moves},
        "zeroDepthK2": {
            "a_moves": a_moves, "b_moves": b_moves,
            "a_zero": a_zero_count, "b_zero": b_zero_count,
            "a_rate": round(a_rate, 4), "b_rate": round(b_rate, 4),
            "a_max_consecutive": a_consec, "b_max_consecutive": b_consec,
            "a_games_gt1": a_gt1, "b_games_gt1": b_gt1,
            "evaluated": k2,
        },
        "hangs": hangs,
        "gaps": gaps,
        "completedDepthMean": depth,
        "adjudicated": sum(1 for r in rows if r.get("adjudicated")),
        "avgPlies": mean([float(r.get("plies", 0)) for r in rows]),
        "avgMovesPerGame": {
            "a": mean([float(r.get("a_moves", 0)) for r in rows]),
            "b": mean([float(r.get("b_moves", 0)) for r in rows]),
        },
        "wallPercent": wall_percent,
        "gameIds": [r.get("game") for r in rows],
    }


def compare(report: dict, calc: dict) -> list[str]:
    """逐项对照 report；返回不一致项列表。"""
    diffs: list[str] = []

    def chk(name: str, got, want) -> None:
        if got != want:
            diffs.append(f"{name}: report={want!r} recomputed={got!r}")

    for k in ("games", "wins", "losses", "draws", "score", "winRate", "wilson95", "elo", "wallPercent"):
        chk(k, calc.get(k), report.get(k))
    chk("gates", calc["gates"], report.get("gates"))
    chk("moveTimes", calc["moveTimes"], report.get("moveTimes"))
    chk("boundReasons", calc["boundReasons"], report.get("boundReasons"))
    chk("zeroDepthReasons", calc["zeroDepthReasons"], report.get("zeroDepthReasons"))
    chk("moves", calc["moves"], report.get("moves"))
    chk("zeroDepthRate", {"a": calc["zeroDepthK2"]["a_rate"], "b": calc["zeroDepthK2"]["b_rate"]}, report.get("zeroDepthRate"))
    chk("zeroDepthMaxConsecutive", {"a": calc["zeroDepthK2"]["a_max_consecutive"], "b": calc["zeroDepthK2"]["b_max_consecutive"]}, report.get("zeroDepthMaxConsecutive"))
    chk("zeroDepthGamesWithGt1", {"a": calc["zeroDepthK2"]["a_games_gt1"], "b": calc["zeroDepthK2"]["b_games_gt1"]}, report.get("zeroDepthGamesWithGt1"))
    chk("zeroDepthK2Evaluated", calc["zeroDepthK2"]["evaluated"], report.get("zeroDepthK2Evaluated"))
    chk("pass", calc["pass"], report.get("pass"))
    for k in (
        "winRatePass",
        "strongSide",
        "strongScore",
        "strongLow",
        "bandPass",
        "contractPass",
        "contractFailedGates",
    ):
        chk(k, calc.get(k), report.get(k))
    return diffs


def main() -> int:
    ckpt = Path(sys.argv[1])
    report_path = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "-" else ckpt.with_suffix(".report.json")
    target_n = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    rows = [json.loads(l) for l in ckpt.read_text(encoding="utf-8").splitlines() if l.strip()]
    games = [r.get("game") for r in rows]
    print(f"checkpoint = {ckpt.resolve()}")
    print(f"rows={len(rows)}  games={min(games) if games else None}..{max(games) if games else None}  "
          f"dup={len(games) - len(set(games))}  continuous={sorted(games) == list(range(1, len(rows) + 1))}")
    calc = recompute(rows, target_n=target_n)
    print("\n===== 独立复算结果 =====")
    print(json.dumps(calc, ensure_ascii=False, indent=2))
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        print(f"\n===== 与 report 逐项对照：{report_path.resolve()} =====")
        diffs = compare(report, calc)
        if diffs:
            for d in diffs:
                print("MISMATCH:", d)
        else:
            print("ALL CHECKED FIELDS MATCH (共 20 组字段)")
        print(f"\nreport.judgementVersion = {report.get('judgementVersion')}  "
              f"winRatePass = {report.get('winRatePass')}  pass = {report.get('pass')}")
        print(f"report.contractPass = {report.get('contractPass')}  "
              f"contractFailedGates = {report.get('contractFailedGates')}")
        print(f"report.failedGates = {report.get('failedGates')}")
    else:
        print(f"\n[no report yet] {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
