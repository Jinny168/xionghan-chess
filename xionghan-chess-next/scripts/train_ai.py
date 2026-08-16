from __future__ import annotations

import argparse
import json

from xionghan_chess.training.network import NumpyPolicyValueNet
from xionghan_chess.training.selfplay import append_jsonl, collect_game


def main() -> None:
    parser = argparse.ArgumentParser(description="Xionghan Chess local self-play trainer")
    parser.add_argument("--data", default="training-data/selfplay.jsonl")
    parser.add_argument("--model", default="training-data/policy-value-v1.npz")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--simulations", type=int, default=32)
    parser.add_argument("--max-plies", type=int, default=240)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    total = 0
    for game_index in range(args.games):
        total += append_jsonl(args.data, collect_game(
            simulations=args.simulations, max_plies=args.max_plies,
            seed=args.seed + game_index,
        ))
    network = NumpyPolicyValueNet(seed=args.seed)
    metrics = network.train_jsonl(args.data, epochs=args.epochs)
    network.save(args.model)
    print(json.dumps({"newSamples": total, **metrics, "model": args.model}, indent=2))


if __name__ == "__main__":
    main()
