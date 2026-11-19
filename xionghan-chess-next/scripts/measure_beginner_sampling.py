"""入门档软取样可复现测量（D4 验收留档）。

用**真实 `CONFIGS.beginner`** 配置自对弈 N 局，统计软取样层触发与非最佳着法占比。
所有参数写在本文件头部并在运行时打印；结果以**一行 JSON** 打到 stdout，便于核验方
独立复算。

口径：
- `layer_triggered`：取样层从名次 2..N 候选池挑出了一手非最佳着（= 非最佳着法）；
- `non_best`：实际取到的着法 != 本轮 `root_scores[0]`（搜索最佳着）；
- `rank2`：非最佳着恰好是名次第 2 的候选；
- 两个比例 = 命中数 / `total_moves`。

验收区间（docs/AI_TIERS.md §15）：次优层占比 8%–20%；非最佳着法占比 ≤ 20%。

用法：
    python scripts/measure_beginner_sampling.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.ai import CONFIGS, ChessAI, Difficulty  # noqa: E402
from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color  # noqa: E402

# ---- 头部参数（改这里即可复现不同批次）----
SEED = 20261118
GAMES = 20
MAX_PLIES = 120
LEVEL = Difficulty.BEGINNER
# ---------------------------------------------


def main() -> int:
    cfg = CONFIGS[LEVEL]
    params = {
        "seed": SEED,
        "games": GAMES,
        "max_plies": MAX_PLIES,
        "level": LEVEL.value,
        "config": {
            "depth": cfg.depth,
            "time_limit": cfg.time_limit,
            "randomness": cfg.randomness,
            "quiescence_depth": cfg.quiescence_depth,
            "candidate_count": cfg.candidate_count,
            "branch_limit": cfg.branch_limit,
            "root_limit": cfg.root_limit,
            "sample_margin": cfg.sample_margin,
        },
    }
    print("params=" + json.dumps(params, ensure_ascii=False), flush=True)

    total_moves = 0
    layer_triggered = 0
    non_best = 0
    rank2 = 0

    for game_index in range(GAMES):
        game = Game("web")
        red = ChessAI(LEVEL, seed=SEED + game_index * 2)
        black = ChessAI(LEVEL, seed=SEED + game_index * 2 + 1)

        for _ in range(MAX_PLIES):
            if game.state.finished:
                break
            engine = red if game.state.turn is Color.RED else black
            move = engine.choose_move(game)
            if move is None:
                break
            total_moves += 1

            if engine.root_scores:
                best_move = engine.root_scores[0][1]
                if move.key() != best_move.key():
                    non_best += 1
                    layer_triggered += 1
                    if len(engine.root_scores) > 1 and move.key() == engine.root_scores[1][1].key():
                        rank2 += 1

            game.move(move)

    def ratio(n: int) -> float:
        return round(n / total_moves, 4) if total_moves else 0.0

    report = {
        **params,
        "total_moves": total_moves,
        "layer_triggered": layer_triggered,
        "non_best": non_best,
        "rank2": rank2,
        "triggered_ratio": ratio(layer_triggered),
        "non_best_ratio": ratio(non_best),
        "rank2_ratio": ratio(rank2),
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
