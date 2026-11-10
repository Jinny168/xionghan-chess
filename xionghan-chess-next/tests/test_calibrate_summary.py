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


def test_product_wall_is_recorded_not_enforced() -> None:
    """产品 cap 下 wall 必然绑定：只记录 wall 占比，不因此判 pass=False。"""
    rows = _rows(22, 0, 10)
    for row in rows:
        row["a_bound_reasons"] = {"wall": 1, "nodes": 0, "cancel": 0}
        row["b_bound_reasons"] = {"wall": 1, "nodes": 0, "cancel": 0}
    report = summarize(rows, "beginner", "medium", 64, 32, tiers_name="product")
    assert report["gates"]["wallClean"] is False
    assert report["gates"]["wallCleanEnforced"] is False
    assert report["wallPercent"] == 100.0
    assert "wall-bound" in report["wallBoundNote"]
    assert report["pass"] is True, "product 的 wall 不应把可引用数据判死"


def test_target_wall_remains_a_hard_gate() -> None:
    rows = _rows(22, 0, 10)
    for row in rows:
        row["a_bound_reasons"] = {"wall": 1, "nodes": 0, "cancel": 0}
        row["b_bound_reasons"] = {"wall": 1, "nodes": 0, "cancel": 0}
    report = summarize(rows, "beginner", "medium", 64, 32, tiers_name="target")
    assert report["gates"]["wallClean"] is False
    assert report["gates"]["wallCleanEnforced"] is True
    assert report["pass"] is False, "target 表的 wallClean 仍是硬门"


def test_load_search_config_accepts_json_and_file(tmp_path) -> None:
    import json

    from calibrate_levels import _load_search_config

    payload = {
        "depth": 2,
        "time_limit": 2.0,
        "randomness": 0.55,
        "quiescence_depth": 1,
        "candidate_count": 4,
        "branch_limit": 3,
        "root_limit": 5,
        "sample_margin": 150,
        "max_nodes": None,
    }
    direct = _load_search_config(json.dumps(payload), "--config-a")
    assert (direct.depth, direct.time_limit, direct.sample_margin) == (2, 2.0, 150)

    path = tmp_path / "c1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    from_file = _load_search_config(f"@{path}", "--config-a")
    assert from_file == direct


def test_load_search_config_rejects_wrong_shape() -> None:
    import pytest
    from calibrate_levels import _load_search_config

    with pytest.raises(SystemExit):
        _load_search_config('{"depth": 2}', "--config-a")
    with pytest.raises(SystemExit):
        _load_search_config('{"depth": 2, "bogus": 1}', "--config-a")


def test_load_search_config_defaults_max_nodes_to_none() -> None:
    from calibrate_levels import _load_search_config

    raw = (
        '{"depth":2,"time_limit":2.0,"randomness":0.55,"quiescence_depth":1,'
        '"candidate_count":4,"branch_limit":3,"root_limit":5,"sample_margin":150}'
    )
    config = _load_search_config(raw, "--config-a")
    assert config.max_nodes is None


def _rows_with_flags(count: int, flags: list[bool]) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        row = _row("red" if index % 2 == 0 else "black")
        row["a_zero_depth_flags"] = flags[:1] if index == 0 else [False]
        row["b_zero_depth_flags"] = [False]
        row["a_moves"] = 1
        row["b_moves"] = 1
        row["a_zero_depth_max_consecutive"] = 0
        row["b_zero_depth_max_consecutive"] = 0
        rows.append(row)
    return rows


def test_k2_zero_rate_and_sample_gate_are_reported() -> None:
    report = summarize(_rows_with_flags(300, [False]), "beginner", "medium", 64, 300)
    assert report["zeroDepthK2Evaluated"] is True
    assert report["gates"]["zeroDepthRateAtMost1Percent"] is True
    assert "0/300" in report["zeroDepthK2"]
    assert "上界" in report["zeroDepthK2"]


def test_k2_consecutive_and_per_game_gates_go_red() -> None:
    rows = _rows_with_flags(300, [False])
    rows[0]["a_zero_depth_flags"] = [True, True]
    rows[0]["a_moves"] = 2
    rows[0]["a_zero_depth_max_consecutive"] = 2
    report = summarize(rows, "beginner", "medium", 64, 300)
    assert report["gates"]["zeroDepthNoConsecutive"] is False
    assert report["gates"]["zeroDepthAtMostOnePerGame"] is False
    assert "zeroDepthNoConsecutive" in report["failedGates"]
