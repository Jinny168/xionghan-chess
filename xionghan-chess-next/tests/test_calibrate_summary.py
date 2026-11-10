"""标定汇总口径：和棋半分、门槛、enoughGames、checkpoint 命名。

这些数字直接决定"某档能不能交付"，但汇总函数本身不跑棋，所以可以纯构造 rows
逐条钉住：
- 和棋按半分：16 胜 12 和 4 负 = 22/32 = 0.6875（不是 16/32=0.5）；
- 门槛：n=32 → 22、n=64 → 40；
- `enoughGames` 必须进 `pass`：只跑 2 局不能因为胜率高就通过；
- checkpoint 文件名带双方档位，同一天跑多对不互相覆盖。
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from calibrate_levels import default_checkpoint, summarize  # noqa: E402


def _row(winner: str | None) -> dict[str, object]:
    return {
        "winner": winner,
        "master_color": "red",
        "adjudicated": False,
        "a_moves": 1,
        "b_moves": 1,
        "a_bound_reasons": {"wall": 0, "nodes": 0, "cancel": 0},
        "b_bound_reasons": {"wall": 0, "nodes": 0, "cancel": 0},
        "a_zero_depth_reasons": {"wall": 0, "nodes": 0, "cancel": 0},
        "b_zero_depth_reasons": {"wall": 0, "nodes": 0, "cancel": 0},
        "a_clean_move_times": [0.3],
        "b_clean_move_times": [4.0],
    }


def _rows(wins: int, draws: int, losses: int) -> list[dict[str, object]]:
    return [_row("red")] * wins + [_row(None)] * draws + [_row("black")] * losses


def test_draws_count_as_half_a_point() -> None:
    report = summarize(_rows(16, 12, 4), "beginner", "medium", 64, 32)
    assert report["score"] == 22.0
    assert report["winRate"] == 0.6875
    assert report["winRatePass"] is True
    assert report["thresholdWins"] == 22

    stronger = summarize(_rows(20, 8, 4), "beginner", "medium", 64, 32)
    assert stronger["score"] == 24.0
    assert stronger["winRate"] == 0.75
    assert stronger["pass"] is True


def test_draws_do_not_hide_a_failing_win_rate() -> None:
    """16 胜 0 和 16 负 = 0.5：不能因为"没输太多"就过。"""
    report = summarize(_rows(16, 0, 16), "beginner", "medium", 64, 32)
    assert report["winRate"] == 0.5
    assert report["winRatePass"] is False
    assert report["pass"] is False


def test_enough_games_is_part_of_pass() -> None:
    report = summarize(_rows(2, 0, 0), "beginner", "medium", 64, 32)
    assert report["winRate"] == 1.0
    assert report["gates"]["enoughGames"] is False
    assert report["pass"] is False, "2 局全胜不能当验收"


def test_checkpoint_name_carries_both_levels() -> None:
    path = default_checkpoint("medium", "hard")
    assert "medium-vs-hard" in path.name
    assert path.name.endswith(".jsonl")
