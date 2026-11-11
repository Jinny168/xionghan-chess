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

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from calibrate_levels import (  # noqa: E402
    BAND_HIGH,
    BAND_LOW,
    band_pass,
    default_checkpoint,
    summarize,
)

# 边界测试专用浮点容差；带宽只由 BAND_LOW / BAND_HIGH 定义，待测输入从二者派生。
EPS = 1e-4


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


# --- v2 强档方向判定 / K4 设计带守卫 ---------------------------------------


@pytest.mark.parametrize(
    ("score_rate", "expected"),
    [
        (BAND_LOW - EPS, False),
        (BAND_LOW, True),
        ((BAND_LOW + BAND_HIGH) / 2, True),
        (BAND_HIGH, True),
        (BAND_HIGH + EPS, False),
        (0.7891, False),  # 本轮实测强档得分率（测量值，允许原样出现）
    ],
)
def test_band_pass_point_estimate_bounds(score_rate: float, expected: bool) -> None:
    """带宽闭区间只由 BAND_LOW / BAND_HIGH 定义；待测输入从常量派生，不硬编码带宽。"""
    assert band_pass(score_rate) is expected


def test_summarize_reuses_band_pass_pure_function() -> None:
    """判定层只能调用 band_pass，不得另写一份 0.65 / 0.75 比较。"""
    for wins, draws, losses, n in ((13, 1, 50, 64), (70, 0, 30, 100), (3, 0, 7, 10)):
        report = summarize(_rows(wins, draws, losses), "beginner", "medium", 64, n)
        assert report["bandPass"] is band_pass(report["strongScore"])


def test_contract_pass_truth_table() -> None:
    """contractPass = pass and bandPass 四格；为真时 pass 必为真（单调，不得洗绿）。"""
    cases = {
        "F/T": (summarize(_rows(3, 0, 7), "beginner", "medium", 64, 10), False, True, False),
        "T/T": (summarize(_rows(70, 0, 30), "beginner", "medium", 64, 100), True, True, True),
        "T/F": (summarize(_rows(13, 1, 50), "beginner", "medium", 64, 64), True, False, False),
        "F/F": (summarize(_rows(16, 0, 16), "beginner", "medium", 64, 32), False, False, False),
    }
    for label, (report, expected_pass, expected_band, expected_contract) in cases.items():
        assert report["pass"] is expected_pass, label
        assert report["bandPass"] is expected_band, label
        assert report["contractPass"] is expected_contract, label
        assert not (report["contractPass"] and not report["pass"]), label


def test_strong_side_and_low_are_symmetric() -> None:
    """A 强取 low、A 弱取 1-high，两侧通用公式为 max(low, 1-high)。"""
    a_strong = summarize(_rows(16, 12, 4), "beginner", "medium", 64, 32)
    a_weak = summarize(_rows(4, 12, 16), "beginner", "medium", 64, 32)
    assert a_strong["strongSide"] == "a"
    assert a_strong["strongLow"] == pytest.approx(a_strong["wilson95"][0], abs=EPS)
    assert a_weak["strongSide"] == "b"
    assert a_weak["strongLow"] == pytest.approx(1 - a_weak["wilson95"][1], abs=EPS)
    assert a_strong["strongScore"] == 0.6875
    assert a_weak["strongScore"] == 0.6875


@pytest.mark.parametrize(
    ("rows", "target_n", "win_rate", "wilson", "elo", "threshold"),
    [
        (_rows(16, 12, 4), 32, 0.6875, [0.5143, 0.8205], 137.0, 22),
        (_rows(20, 8, 4), 32, 0.75, [0.5789, 0.8675], 190.8, 22),
        (_rows(16, 0, 16), 32, 0.5, [0.3363, 0.6637], 0.0, 22),
        (_rows(2, 0, 0), 32, 1.0, [0.3424, 1.0], None, None),
    ],
)
def test_measurement_layer_unchanged(
    rows: list[dict[str, object]],
    target_n: int,
    win_rate: float,
    wilson: list[float],
    elo: float | None,
    threshold: int | None,
) -> None:
    """v2 只改判定层：原始测量字段逐夹具不变，不受强档方向改判影响。"""
    report = summarize(rows, "beginner", "medium", 64, target_n)
    assert report["winRate"] == win_rate
    assert report["wilson95"] == wilson
    assert report["elo"] == elo
    assert report["thresholdWins"] == threshold


def test_v2_report_schema_is_self_explanatory() -> None:
    """本轮终验：脚本门禁通过但 K4 契约未达成，报告必须自己说得清。"""
    report = summarize(_rows(13, 1, 50), "beginner", "medium", 64, 64)
    for key in (
        "strongSide",
        "strongScore",
        "strongLow",
        "judgementVersion",
        "bandPass",
        "contractPass",
        "contractFailedGates",
        "thresholdSide",
    ):
        assert key in report
    assert report["judgementVersion"] == "v2"
    assert report["thresholdSide"] == "strong"
    assert report["strongSide"] == "b"
    assert report["strongScore"] == 0.7891
    assert report["strongLow"] == pytest.approx(1 - report["wilson95"][1], abs=EPS)
    assert report["failedGates"] == []
    assert report["contractFailedGates"] == [f"band: 0.7891 > {BAND_HIGH:.2f}"]
    assert report["contractPass"] is False


# ---------------------------------------------------------------------------
# 截断判定（adjudicated）必须与真和棋分开
#
# 现状：`draws = games - wins - losses`，而 `winner is None` 里混了两种东西 ——
# 真和棋，以及"被 ply_cap 截断、没下完"的局。于是「和棋率」不可解释，
# 而 `games == targetGames` 是个恒真的假指标（32 局 18 局截断时它照样全过）。
#
# 通则：**同名字段语义不可变，改口径一律新增字段** —— 旧报告不能静默变成另一个含义。
# ---------------------------------------------------------------------------
def _adjudicated_row(winner: str | None) -> dict[str, object]:
    row = _row(winner)
    row["adjudicated"] = True
    return row


def test_adjudicated_games_are_counted_separately_from_draws() -> None:
    # 12 胜 + 3 负 + 2 真和 + 3 截断无胜负 = 20 局
    rows = [_row("red")] * 12 + [_row("black")] * 3 + [_row(None)] * 2 + [_adjudicated_row(None)] * 3
    report = summarize(rows, "beginner", "medium", 64, 20)

    assert report["games"] == 20
    assert report["wins"] == 12
    assert report["losses"] == 3
    # `draws` 保持旧义：winner is None 的全部（含截断无胜负）
    assert report["draws"] == 5
    assert report["drawsNoResult"] == 3
    assert report["adjudicatedGames"] == 3
    assert report["adjudicatedRatio"] == pytest.approx(3 / 20, abs=EPS)
    # 旧 `score` 语义不变（含截断判定的半分），另给排除口径
    assert report["score"] == 12 + 0.5 * 5
    assert report["scoreIncludesAdjudicated"] is True
    assert report["scoreExclAdjudicated"] == 12 + 0.5 * 2
    assert report["gamesExclAdjudicated"] == 17


def test_adjudicated_ratio_policy_is_labelled_as_policy() -> None:
    """阈值是**设计判断**（会被数据推翻），测量值不可协商 —— 两者必须分开记。"""
    report = summarize(_rows(16, 12, 4), "beginner", "medium", 64, 32)
    assert report["adjudicatedRatioPolicy"] == 0.2
    assert report["adjudicatedGames"] == 0


# ---------------------------------------------------------------------------
# 两个可比性指纹：必须真的**能分辨**，否则等于没写
# ---------------------------------------------------------------------------
def test_book_digest_changes_when_a_single_opening_fingerprint_changes() -> None:
    """母体是自维护的：任何一条 `fp` 变了（含 `rs` 前缀），digest 必须变。

    这条防的是"字段写了但永不变化"——那样判等脚本会永远判"可比"，
    比没有字段更糟（它会给出错误的信心）。
    """
    from calibrate_levels import _book_digest

    from xionghan_chess.core.benchmark import Opening

    base = [
        Opening(profile="desktop_complete", seed=700, plies=6, fp="a|opt:rs3-p3l1"),
        Opening(profile="desktop_complete", seed=700, plies=10, fp="b|opt:rs3-p3l1"),
    ]
    same = list(base)
    assert _book_digest(base) == _book_digest(same)

    nudged = list(base)
    nudged[1] = Opening(profile="desktop_complete", seed=700, plies=10, fp="b|opt:rs4-p3l1")
    assert _book_digest(base) != _book_digest(nudged), "换了规则版本前缀，母体指纹必须变"


def test_ai_config_digest_tracks_the_effective_config_not_just_the_level_name() -> None:
    """两个 digest 分档存、对**实际生效**的配置求哈希。

    报告里的 `levels` 只有档位名（`{"a": "beginner", "b": "medium"}`），而
    `--config-*` / `--cap-*` / `--max-nodes-*` 优先于 `CONFIGS` 表 —— 两次配置差很远的
    运行会得到**完全相同**的 `levels`。没有这个 digest，"档位强度变了真还是母体变了"
    永远吵不清。
    """
    from dataclasses import replace

    from calibrate_levels import _config_digest

    from xionghan_chess.core.ai import SearchConfig

    # `SearchConfig` 没有全默认构造：显式给一份，字段值本身不重要，只要可复现。
    config = SearchConfig(
        depth=1,
        time_limit=1.0,
        randomness=0,
        quiescence_depth=0,
        candidate_count=8,
        branch_limit=8,
        root_limit=8,
    )
    assert _config_digest("beginner", config) == _config_digest("beginner", config)

    # 同一个档位名、不同的实际配置 → 必须分开
    assert _config_digest("beginner", config) != _config_digest(
        "beginner", replace(config, depth=config.depth + 1)
    )
    # 不同档位名、相同配置 → 也要分开（报告里档位名是给人看的标签）
    assert _config_digest("beginner", config) != _config_digest("medium", config)
