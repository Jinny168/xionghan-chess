from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from xionghan_chess.core.benchmark import (
    MASTER_MOVE_CEILING_SECONDS,
    benchmark_master_vs_hard,
)


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def summarize(rows: list[dict], games_target: int) -> dict:
    wins = sum(1 for r in rows if r["winner"] == r["master_color"])
    losses = sum(1 for r in rows if r["winner"] is not None and r["winner"] != r["master_color"])
    draws = len(rows) - wins - losses
    adjudicated = sum(1 for r in rows if r["adjudicated"])
    completed = len(rows) - adjudicated

    master_moves = 0
    hard_moves = 0
    for r in rows:
        first = r["master_color"] == "red"
        master_moves += (r["plies"] + 1) // 2 if first else r["plies"] // 2
        hard_moves += r["plies"] // 2 if first else (r["plies"] + 1) // 2
    master_total = sum(r["master_seconds"] for r in rows)
    hard_total = sum(r["hard_seconds"] for r in rows)
    master_max = max((r.get("master_max_move_seconds", 0.0) for r in rows), default=0.0)

    return {
        "games": len(rows),
        "gamesTarget": games_target,
        "masterWins": wins,
        "hardWins": losses,
        "draws": draws,
        "adjudicatedGames": adjudicated,
        "completedGames": completed,
        "masterWinRate": round(wins / len(rows), 4) if rows else 0.0,
        "masterMoveMeanSeconds": round(master_total / master_moves, 3) if master_moves else 0.0,
        "masterMoveMaxSeconds": master_max,
        "masterMoveCeilingSeconds": MASTER_MOVE_CEILING_SECONDS,
        "hardMoveMeanSeconds": round(hard_total / hard_moves, 3) if hard_moves else 0.0,
        "pliesMean": round(sum(r["plies"] for r in rows) / len(rows), 1) if rows else 0.0,
        "engineHours": round((master_total + hard_total) / 3600, 2),
        "acceptance": {
            "enoughGames": len(rows) >= 50,
            "enoughCompletedGames": completed >= 50,
            "winRateAtLeast55Percent": len(rows) >= 50 and wins / len(rows) >= 0.55,
            # 键名沿用历史报告；阈值取「预算 × (1+15%)」，见 core/benchmark.py 常量注释。
            "masterMoveAtMost12Seconds": master_max <= MASTER_MOVE_CEILING_SECONDS,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark master MCTS against hard AI")
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--start-game", type=int, default=0)
    parser.add_argument("--profile", default="traditional")
    parser.add_argument("--max-plies", type=int, default=240)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hard-scale", type=float, default=1.0)
    parser.add_argument("--master-simulations", type=int)
    parser.add_argument("--output")
    parser.add_argument("--checkpoint", help="逐局追加写入的 JSONL 路径（崩溃可保留已完成局）")
    parser.add_argument("--resume", action="store_true", help="从 checkpoint 已有局数继续，追加写入")
    parser.add_argument("--summarize", metavar="JSONL", help="只汇总现有 JSONL，不跑对局")
    parser.add_argument("--quiet", action="store_true", help="不逐局打印进度")
    args = parser.parse_args()

    if args.summarize:
        rows = load_rows(Path(args.summarize))
        print(json.dumps(summarize(rows, args.games), ensure_ascii=False, indent=2))
        return

    start_game = args.start_game
    append = False
    if args.resume:
        if not args.checkpoint:
            parser.error("--resume 需要 --checkpoint")
        rows = load_rows(Path(args.checkpoint))
        start_game = len(rows)
        append = True
        if start_game >= args.games:
            print(f"已完成 {start_game} 局，无需再跑")
            print(json.dumps(summarize(rows, args.games), ensure_ascii=False, indent=2))
            return

    handle = None
    if args.checkpoint:
        target = Path(args.checkpoint)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = target.open("a" if append else "w", encoding="utf-8")

    def on_game(result) -> None:
        if not args.quiet:
            print(f"[{result.game:2d}/{args.games}] master={result.master_color:5s} "
                  f"winner={str(result.winner):5s} plies={result.plies:3d} "
                  f"adjudicated={result.adjudicated} "
                  f"t={result.master_seconds:6.1f}/{result.hard_seconds:6.1f}s", flush=True)
        if handle is not None:
            handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
            handle.flush()

    try:
        run_games = max(0, args.games - start_game)
        report = benchmark_master_vs_hard(
            run_games, args.profile, args.max_plies, args.seed,
            args.hard_scale, args.master_simulations, on_game, start_game,
        )
    finally:
        if handle is not None:
            handle.close()

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
