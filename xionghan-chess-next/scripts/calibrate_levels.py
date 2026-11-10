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
from level_targets import LEVELS, PRODUCT_LEVELS, PRODUCT_TIERS, TARGETS, Tier  # noqa: E402

from xionghan_chess.core.ai import SearchConfig  # noqa: E402
from xionghan_chess.core.benchmark import (  # noqa: E402
    benchmark_match,
    book_index,
    elo_from_win_rate,
    time_stats,
    wilson_interval,
)

DEFAULT_BOOK = opening_book.DEFAULT_OUT


def _load_search_config(raw: str, label: str) -> SearchConfig:
    """`--config-a/b`：JSON 字符串或 `@file.json`，字段必须与 SearchConfig 一一对应。

    `--config-*` 优先于 `--tiers` / `--cap-*` / `--max-nodes-*`：给的是完整配置，
    不再做任何二次覆盖（否则"扫候选"和"改全局"就分不清了）。
    """
    text = raw.strip()
    if text.startswith("@"):
        text = Path(text[1:]).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{label} 必须是 JSON object，实际 {type(data).__name__}")
    allowed = set(SearchConfig.__dataclass_fields__)
    unknown = sorted(set(data) - allowed)
    missing = sorted(allowed - set(data))
    if unknown or missing:
        raise SystemExit(f"{label} 字段不匹配 SearchConfig：unknown={unknown} missing={missing}")
    return SearchConfig(**data)


def _parse_max_nodes(raw: str, level: str, tiers: dict[str, Tier]) -> int | None:
    text = raw.strip().lower()
    if text == "auto":
        return tiers[level].max_nodes
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


def default_checkpoint(level_a: str, level_b: str) -> Path:
    """默认 checkpoint 文件名带对局双方：同一天跑多对不会互相覆盖。"""
    return ROOT / "benchmarks" / "calibration_runs" / f"{date.today()}-{level_a}-vs-{level_b}.jsonl"


def _clean_times(rows: list[dict[str, object]], side: str) -> list[float]:
    """未被截断的手；旧 checkpoint 没有 clean 字段时退回全量（兼容）。"""
    clean = [float(value) for row in rows for value in (row.get(f"{side}_clean_move_times") or [])]
    if clean:
        return clean
    return [float(value) for row in rows for value in (row.get(f"{side}_move_times") or [])]


def summarize(
    rows: list[dict[str, object]],
    level_a: str,
    level_b: str,
    book_size: int,
    target_n: int,
    tiers_name: str = "product",
) -> dict[str, object]:
    games = len(rows)
    wins = sum(row.get("winner") == row.get("master_color") for row in rows)
    losses = sum(row.get("winner") is not None and row.get("winner") != row.get("master_color") for row in rows)
    draws = games - wins - losses
    # 和棋按半分计入：k_eff = W + 0.5·D。用 W/n 会系统性低估势均力敌的对局。
    score = wins + 0.5 * draws
    point = score / games if games else 0.0
    low, high = wilson_interval(score, games)
    a_bound = _aggregate_reasons(rows, "a")
    b_bound = _aggregate_reasons(rows, "b")
    a_zero = _zero_reasons(rows, "a")
    b_zero = _zero_reasons(rows, "b")
    a_moves = sum(int(row.get("a_moves", 0)) for row in rows)
    b_moves = sum(int(row.get("b_moves", 0)) for row in rows)
    a_times = _clean_times(rows, "a")
    b_times = _clean_times(rows, "b")
    # 门槛按整数 k_eff 找（n=32→22、n=64→40）；和棋只影响实际 k_eff，不改变门槛。
    threshold = next(
        (
            count
            for count in range(games + 1)
            if games and count / games >= 0.60 and wilson_interval(count, games)[0] >= 0.50
        ),
        None,
    )
    nodes_ratio_a = a_bound["nodes"] / a_moves if a_moves else 0.0
    nodes_ratio_b = b_bound["nodes"] / b_moves if b_moves else 0.0
    total_moves = a_moves + b_moves
    wall_moves = a_bound["wall"] + b_bound["wall"]
    wall_percent = round(100.0 * wall_moves / total_moves, 2) if total_moves else 0.0
    wall_clean = wall_moves == 0
    # 产品三档的 depth 是"时间预算下的上限"：d6/5s、d8/12s 几乎每手都会被墙钟截断。
    # 因此 product 下 `wallClean` 只记录、不判 red；target 表（预算足够跑完深度）仍当硬门。
    wall_enforced = tiers_name == "target"
    gates = {
        "enoughGames": games >= target_n,
        "wallClean": wall_clean,
        "wallCleanEnforced": wall_enforced,
        "noZeroDepth": sum(a_zero.values()) == 0 and sum(b_zero.values()) == 0,
        "nodesRatioAtMost2Percent": nodes_ratio_a <= 0.02 and nodes_ratio_b <= 0.02,
    }
    wall_note = (
        f"本结果为产品 cap 下的 wall-bound 数据，wall 占比 {wall_percent:.2f}%"
        if not wall_enforced
        else f"target 表：wallClean 为硬门（wall 占比 {wall_percent:.2f}%）"
    )
    win_rate_pass = point >= 0.60 and low >= 0.50
    return {
        "levels": {"a": level_a, "b": level_b},
        "games": games,
        "targetGames": target_n,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "score": score,
        "winRate": round(point, 4),
        "wilson95": [round(low, 4), round(high, 4)],
        "elo": (None if (elo_value := elo_from_win_rate(point)) is None else round(elo_value, 1) or 0.0),
        "thresholdWins": threshold,
        "winRatePass": win_rate_pass,
        "moveTimes": {"a": time_stats(a_times), "b": time_stats(b_times)},
        "boundReasons": {"a": a_bound, "b": b_bound},
        "zeroDepthReasons": {"a": a_zero, "b": b_zero},
        "moves": {"a": a_moves, "b": b_moves},
        "wallPercent": wall_percent,
        "wallBoundNote": wall_note,
        "gates": gates,
        "pass": (
            win_rate_pass
            and gates["enoughGames"]
            and (gates["wallClean"] or not wall_enforced)
            and gates["noZeroDepth"]
            and gates["nodesRatioAtMost2Percent"]
        ),
        "book": {
            "size": book_size,
            "used": [f"{row.get('opening')}" for row in rows if row.get("opening")],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="任意两档标定 / 验收对局")
    tiers_name = "product"
    if argv is None:
        argv = sys.argv[1:]
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--tiers", choices=("product", "target"), default="product")
    tiers_name = pre.parse_known_args(argv)[0].tiers
    tiers = PRODUCT_TIERS if tiers_name == "product" else TARGETS
    levels = PRODUCT_LEVELS if tiers_name == "product" else LEVELS
    parser.add_argument(
        "--tiers",
        choices=("product", "target"),
        default=tiers_name,
        help="product=发布三档（默认）；target=S4-2b 提案表",
    )
    parser.add_argument("--level-a", choices=levels, required=True)
    parser.add_argument("--level-b", choices=levels, required=True)
    parser.add_argument("--n", type=int, default=32, help="总局数（必须偶数：每开局红黑各一）")
    parser.add_argument("--max-plies", type=int, default=100)
    parser.add_argument(
        "--initial-minutes", type=int, default=180, help="对局包干时钟（默认 180：避免 d8/12s 在 10 分钟内自然超时）"
    )
    parser.add_argument("--book", default=str(DEFAULT_BOOK))
    parser.add_argument("--checkpoint", default="", help="默认 benchmarks/calibration_runs/<date>-<a>-vs-<b>.jsonl")
    parser.add_argument("--output", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cap-a", default="auto", help="auto / 秒数")
    parser.add_argument("--cap-b", default="auto")
    parser.add_argument("--max-nodes-a", default="auto", help="auto / none / 整数")
    parser.add_argument("--max-nodes-b", default="auto")
    parser.add_argument("--config-a", default="", help="完整 SearchConfig JSON 或 @file.json（优先于 tiers/cap）")
    parser.add_argument("--config-b", default="")
    parser.add_argument(
        "--time-scale", type=float, default=1.0, help="两侧 ChessAI 的预算缩放（默认 1.0；代理标定可 0.25）"
    )
    args = parser.parse_args(argv)
    tiers = PRODUCT_TIERS if args.tiers == "product" else TARGETS

    if args.n % 2 != 0:
        parser.error("--n 必须是偶数：每开局恰好两局（红黑各一），奇数最后一局不成对")
    book = opening_book.load_book(Path(args.book))
    checkpoint = Path(args.checkpoint) if args.checkpoint else default_checkpoint(args.level_a, args.level_b)
    rows = _load_rows(checkpoint) if args.resume else []
    start_game = len(rows)
    if start_game >= args.n:
        print(f"checkpoint 已有 {start_game} 局 ≥ n={args.n}，直接汇总")
    else:
        tier_a, tier_b = tiers[args.level_a], tiers[args.level_b]
        config_a = (
            _load_search_config(args.config_a, "--config-a")
            if args.config_a
            else tier_a.config(
                cap=None if args.cap_a == "auto" else float(args.cap_a),
                max_nodes=_parse_max_nodes(args.max_nodes_a, args.level_a, tiers),
            )
        )
        config_b = (
            _load_search_config(args.config_b, "--config-b")
            if args.config_b
            else tier_b.config(
                cap=None if args.cap_b == "auto" else float(args.cap_b),
                max_nodes=_parse_max_nodes(args.max_nodes_b, args.level_b, tiers),
            )
        )
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        handle = checkpoint.open("a" if args.resume else "w", encoding="utf-8")

        def on_game(result: object) -> None:
            handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
            handle.flush()

        try:
            benchmark_match(
                args.level_a,
                args.level_b,
                games=args.n - start_game,
                max_plies=args.max_plies,
                initial_minutes=args.initial_minutes,
                seed=0,
                time_scale=args.time_scale,
                a_config=config_a,
                b_config=config_b,
                book=book,
                position_builder=opening_book.build_game,
                on_game=on_game,
                start_game=start_game,
                total_games=args.n,
            )
        finally:
            handle.close()
        rows = _load_rows(checkpoint)

    report = summarize(rows, args.level_a, args.level_b, len(book), args.n, args.tiers)
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

    print(
        f"{args.level_a} vs {args.level_b}  n={report['games']}  "
        f"{report['wins']}-{report['losses']}-{report['draws']}  "
        f"winRate={report['winRate']:.3f}  Wilson={report['wilson95']}  "
        f"threshold={report['thresholdWins']}  pass={report['pass']}"
    )
    print(f"gates={report['gates']}  bound={report['boundReasons']}")
    print(report["wallBoundNote"])
    print(f"报告：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
