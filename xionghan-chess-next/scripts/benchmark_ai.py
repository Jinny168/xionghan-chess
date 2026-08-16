from __future__ import annotations

import argparse
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
    args = parser.parse_args()
    report = benchmark_master_vs_hard(
        args.games, args.profile, args.max_plies, args.seed,
        args.hard_scale, args.master_simulations,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
