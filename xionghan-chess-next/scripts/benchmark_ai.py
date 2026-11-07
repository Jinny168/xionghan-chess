from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from xionghan_chess.core.benchmark import benchmark_master_vs_hard


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark master MCTS against hard AI")
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--profile", default="traditional")
    parser.add_argument("--max-plies", type=int, default=240)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hard-scale", type=float, default=1.0)
    parser.add_argument("--master-simulations", type=int)
    parser.add_argument("--output")
    parser.add_argument("--checkpoint", help="每局结束后追加写入的 JSONL 路径（崩溃可保留已完成局）")
    parser.add_argument("--quiet", action="store_true", help="不逐局打印进度")
    args = parser.parse_args()

    handle = None
    if args.checkpoint:
        target = Path(args.checkpoint)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = target.open("w", encoding="utf-8")

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
        report = benchmark_master_vs_hard(
            args.games, args.profile, args.max_plies, args.seed,
            args.hard_scale, args.master_simulations, on_game,
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
