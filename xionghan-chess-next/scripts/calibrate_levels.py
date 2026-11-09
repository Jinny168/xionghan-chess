"""档位标定 / 验收（**只注入实例 config，不改 `CONFIGS`**）。

## 判据

单侧：`点估计 ≥0.60 且 Wilson 下界 ≥0.50`（n=32 → ≥22 胜；n=64 → ≥40 胜）。
另加三条"这批数据能不能引用"的门禁：
- `boundReasons.wall == 0`；否则说明截断点由机器速度决定，胜率不可引用；
- `zeroDepthMoves == 0`；连一手都搜不完说明预算或配置标错；
- `boundReasons.nodes / totalMoves ≤ 2%`；`max_nodes` 成了常规截断器。

## 用法

    python scripts/calibrate_levels.py --level-a beginner --level-b medium --n 32
    python scripts/calibrate_levels.py --level-a medium --level-b hard --n 64 --resume

一进程一对（`AI_TIME_SCALE` 已改为实例参数，但长对局仍建议串行跑，避免 CPU 争抢
把 wall 门禁打红）。逐局落 JSONL，`--resume` 从已完成局数继续。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import gen_opening_book as opening_book  # noqa: E402
from level_targets import LEVELS, TARGETS  # noqa: E402

from xionghan_chess.core.benchmark import (  # noqa: E402
    benchmark_match,
    book_index,
    elo_from_win_rate,
    time_stats,
    wilson_interval,
)

DEFAULT_BOOK = opening_book.DEFAULT_OUT

DEFAULT_CHECKPOINT = ROOT / "benchmarks" / "calibration_runs" / f"{date.today()}.jsonl"


def _parse_max_nodes(raw: str, level: str) -> int | None:
    text = raw.strip().lower()
    if text == "auto":
        return TARGETS[level].max_nodes
    if text in {"none", "off", "0"}:
        return None
    return int(text)


def _load_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _aggregate_reasons(rows: list[dict[str, object]], side: str) -> dict[str, int]:
    total = {"wall": 0, "nodes": 0, "cancel": 0}
    for row in rows:
        reasons = row.get(f"{side}_bound_reasons") or {}
        for key in total:
            total[key] += int(reasons.get(key, 0))
    return total


def _zero_reasons(rows: list[dict[str, object]], side: str) -> dict[str, int]:
    total = {"wall": 0, "nodes": 0, "cancel": 0}
    for row in rows:
        reasons = row.get(f"{side}_zero_depth_reasons") or {}
        for key in total:
            total[key] += int(reasons.get(key, 0))
    return total


def summarize(rows: list[dict[str, object]], level_a: str, level_b: str,
              book_size: int) -> dict[str, object]:
    games = len(rows)
    wins = sum(row.get("winner") == row.get("master_color") for row in rows)
    losses = sum(row.get("winner") is not None
                 and row.get("winner") != row.get("master_color") for row in rows)
    draws = games - wins - losses
    point = wins / games if games else 0.0
    low, high = wilson_interval(wins, games)
    a_bound = _aggregate_reasons(rows, "a")
    b_bound = _aggregate_reasons(rows, "b")
    a_zero = _zero_reasons(rows, "a")
    b_zero = _zero_reasons(rows, "b")
    a_moves = sum(int(row.get("a_moves", 0)) for row in rows)
    b_moves = sum(int(row.get("b_moves", 0)) for row in rows)
    a_times = [float(value) for row in rows for value in (row.get("a_move_times") or [])]
    b_times = [float(value) for row in rows for value in (row.get("b_move_times") or [])]
    threshold = next((count for count in range(games + 1)
                      if games and count / games >= 0.60
                      and wilson_interval(count, games)[0] >= 0.50), None)
    nodes_ratio_a = a_bound["nodes"] / a_moves if a_moves else 0.0
    nodes_ratio_b = b_bound["nodes"] / b_moves if b_moves else 0.0
    gates = {
        "enoughGames": games >= 2,
        "wallClean": a_bound["wall"] == 0 and b_bound["wall"] == 0,
        "noZeroDepth": sum(a_zero.values()) == 0 and sum(b_zero.values()) == 0,
        "nodesRatioAtMost2Percent": nodes_ratio_a <= 0.02 and nodes_ratio_b <= 0.02,
    }
    return {
        "levels": {"a": level_a, "b": level_b},
        "games": games,
        "wins": wins, "losses": losses, "draws": draws,
        "winRate": round(point, 4),
        "wilson95": [round(low, 4), round(high, 4)],
        "elo": (None if (elo_value := elo_from_win_rate(point)) is None
                else round(elo_value, 1) or 0.0),
        "thresholdWins": threshold,
        "winRatePass": point >= 0.60 and low >= 0.50,
        "moveTimes": {"a": time_stats(a_times), "b": time_stats(b_times)},
        "boundReasons": {"a": a_bound, "b": b_bound},
        "zeroDepthReasons": {"a": a_zero, "b": b_zero},
        "moves": {"a": a_moves, "b": b_moves},
        "gates": gates,
        "pass": (point >= 0.60 and low >= 0.50 and gates["wallClean"]
                 and gates["noZeroDepth"] and gates["nodesRatioAtMost2Percent"]),
        "book": {
            "size": book_size,
            "used": [f"{row.get('opening')}" for row in rows if row.get("opening")],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="任意两档标定 / 验收对局")
    parser.add_argument("--level-a", choices=LEVELS, required=True)
    parser.add_argument("--level-b", choices=LEVELS, required=True)
    parser.add_argument("--n", type=int, default=32, help="总局数（必须偶数：每开局红黑各一）")
    parser.add_argument("--max-plies", type=int, default=100)
    parser.add_argument("--book", default=str(DEFAULT_BOOK))
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    parser.add_argument("--output", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cap-a", default="auto", help="auto / 秒数")
    parser.add_argument("--cap-b", default="auto")
    parser.add_argument("--max-nodes-a", default="auto", help="auto / none / 整数")
    parser.add_argument("--max-nodes-b", default="auto")
    args = parser.parse_args(argv)

    if args.n % 2 != 0:
        parser.error("--n 必须是偶数：每开局恰好两局（红黑各一），奇数最后一局不成对")
    book = opening_book.load_book(Path(args.book))
    checkpoint = Path(args.checkpoint)
    rows = _load_rows(checkpoint) if args.resume else []
    start_game = len(rows)
    if start_game >= args.n:
        print(f"checkpoint 已有 {start_game} 局 ≥ n={args.n}，直接汇总")
    else:
        tier_a, tier_b = TARGETS[args.level_a], TARGETS[args.level_b]
        config_a = tier_a.config(
            cap=None if args.cap_a == "auto" else float(args.cap_a),
            max_nodes=_parse_max_nodes(args.max_nodes_a, args.level_a))
        config_b = tier_b.config(
            cap=None if args.cap_b == "auto" else float(args.cap_b),
            max_nodes=_parse_max_nodes(args.max_nodes_b, args.level_b))
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        handle = checkpoint.open("a" if args.resume else "w", encoding="utf-8")

        def on_game(result: object) -> None:
            handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
            handle.flush()

        try:
            benchmark_match(
                args.level_a, args.level_b,
                games=args.n - start_game, max_plies=args.max_plies,
                seed=0, time_scale=1.0,
                a_config=config_a, b_config=config_b,
                book=book, position_builder=opening_book.build_game,
                on_game=on_game, start_game=start_game,
            )
        finally:
            handle.close()
        rows = _load_rows(checkpoint)

    report = summarize(rows, args.level_a, args.level_b, len(book))
    # 开局 provenance（按绝对局号还原取样规则；报告可逐局审计）。
    for row in rows:
        game = int(row.get("game", 0))
        if 0 < game <= args.n:
            entry = book[book_index(game - 1, args.n, len(book))]
            row["opening"] = f"{entry.profile}#{entry.seed}@{entry.plies}"
    report["book"]["used"] = [str(row.get("opening")) for row in rows]  # type: ignore[index]

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    output = Path(args.output) if args.output else checkpoint.with_suffix(".report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")

    print(f"{args.level_a} vs {args.level_b}  n={report['games']}  "
          f"{report['wins']}-{report['losses']}-{report['draws']}  "
          f"winRate={report['winRate']:.3f}  Wilson={report['wilson95']}  "
          f"threshold={report['thresholdWins']}  pass={report['pass']}")
    print(f"gates={report['gates']}  bound={report['boundReasons']}")
    print(f"报告：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
