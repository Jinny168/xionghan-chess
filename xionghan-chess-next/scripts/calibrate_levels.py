"""档位标定 / 验收（**只注入实例 config，不改 `CONFIGS`**）。

## 判据

**强档方向**（v2，报告 `judgementVersion == "v2"`）：`strong = max(point, 1-point)`、
`strong_low = max(low, 1-high)`，判 `strong ≥0.60 且 strong_low ≥0.50`
（n=32 → 22；n=64 → 40）。
`thresholdSide: "strong"` 只标注门槛的**语义作用域**，数值与 v1 完全相同；
不得解释成"强档最低得分"（A=弱档时会被误读成 A 只拿 24 分）。
A 方常排弱档（见下方用法），拿 A 的 `winRate` 直接判会恒 false。
`winRatePass` / `pass` 只表示"档位可分"，**不等于落进设计带**；设计带另用
`bandPass = 0.65 ≤ strong ≤ 0.75` 单独记录，验收结论必须读 `bandPass`。
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
import hashlib
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
    Opening,
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
    # `max_nodes` 有默认值 None；扫候选时省略它等价于"不启用节点预算"。
    data.setdefault("max_nodes", None)
    allowed = set(SearchConfig.__dataclass_fields__)
    unknown = sorted(set(data) - allowed)
    missing = sorted(allowed - set(data))
    if unknown or missing:
        raise SystemExit(f"{label} 字段不匹配 SearchConfig：unknown={unknown} missing={missing}")
    return SearchConfig(**data)


def _round(x: float, ndigits: int) -> float:
    """报告里所有小数的**唯一**舍入出口。**必须是纯 `round`，不许先加 epsilon 再舍。**

    为什么单独抽出来：`winRate + strongScore == 1` 这条守恒关系依赖两边用**同一个**
    `round(_, 4)`；散在 8 处各写一遍，迟早有一处被改成 half-up 或加个 1e-9 修"浮点误差"，
    而那种改动在**所有测试都绿的情况下悄悄改数值**。抽出来后由
    `tests/test_report_rounding.py` 直接打这个函数（含 tie 用例），改动就瞒不住。

    Python 的 `round` 是 half-to-even（银行家舍入）：`round(0.03125, 4) == 0.0312`。
    """
    return round(x, ndigits)


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


def _max_true_run(flags: list[bool]) -> int:
    best = run = 0
    for flag in flags:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def _zero_flags(rows: list[dict[str, object]], side: str) -> list[bool]:
    return [bool(flag) for row in rows for flag in (row.get(f"{side}_zero_depth_flags") or [])]


BAND_LOW = 0.65
BAND_HIGH = 0.75


def band_pass(score_rate: float) -> bool:
    """K4 设计带：强档得分率**点估计**须落在 [0.65, 0.75] 闭区间。

    口径固定为点估计，不是 Wilson 区间：n=64 时 CI 全宽约 19.69pt > 设计带 10pt，
    「整个 CI 落在带内」恒 false；p≈0.70 时全宽降到 10pt 以下需 n≈400 量级。
    `summarize` 必须复用本函数，不得在别处复制 0.65 / 0.75 字面量。
    """
    return BAND_LOW <= score_rate <= BAND_HIGH


# 判「两次标定能不能比」的判据是
# `(ruleVersion, bookFormat, book.fpDigest, aiConfigDigest, games, seeds)` 全同。
# 其中两个 digest 的区别很关键：
#   `book.fpDigest`  —— **自维护**：`fp` 里带 `rs{N}-` 前缀，母体一变它就变；
#   `ruleVersion`    —— **手维护**：会撒谎（本轮就撒过：语义已是 v3、版本号还是 2）。
# 所以"母体不同"要靠 fpDigest 先判，ruleVersion 只是给人看的标签。
# `aiConfigDigest` 分档存、对**实际生效**的配置求哈希（`--config-*` / `--cap-*` /
# `--max-nodes-*` 解析之后），不是对 `CONFIGS` 表 —— 否则两次不同 cap 的运行会得到
# 同一个 digest，而报告里的 `levels` 只有档位名，看不出任何差别。
ADJUDICATED_RATIO_POLICY = 0.2  # **policy**（会被数据推翻），与下面的测量值分开记

# **设计契约门**：它失败说明"这一档没达到交付标准"，与"测量本身可不可信"是两件事。
# `failedGates` 把两者混在同一个数组里（`winRatePass` 排第一），于是判据若自己写
# `set(failedGates) - {"winRatePass"}` 就等于又维护一份白名单 —— 将来加 `bandPass` 就复发。
# 所以在**写出端**定义一次，报告里直接给子集 `failedMeasurementGates`，消费方只读不推。
CONTRACT_GATES = frozenset({"winRatePass"})


def _config_digest(level: str, config: SearchConfig) -> str:
    payload = json.dumps([level, asdict(config)], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _book_digest(book: list[Opening]) -> str:
    entries = sorted(book, key=lambda entry: (entry.profile, entry.seed, entry.plies))
    text = "\n".join(f"{e.profile}#{e.seed}@{e.plies}:{e.fp}" for e in entries)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


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
    # ---- 截断判定（adjudicated）必须与真和棋分开算 ----
    # 现状问题：`draws = games - wins - losses`，而 `winner is None` 里混了两种东西 ——
    # 真和棋，以及"被 ply_cap 截断、没下完"的局。于是"和棋率"不可解释，
    # 且 `score` 把截断判定也计进了半分。
    # 通则：**同名字段语义不可变，改口径一律新增字段**（否则历史报告会静默变成另一个含义）。
    adjudicated_games = sum(1 for row in rows if row.get("adjudicated"))
    # 截断且无胜负：这部分才是从 `draws` 里分出来的"没下完"
    draws_no_result = sum(1 for row in rows if row.get("winner") is None and row.get("adjudicated"))
    games_excl = games - adjudicated_games
    score_excl = sum(
        1.0
        for row in rows
        if not row.get("adjudicated") and row.get("winner") == row.get("master_color")
    ) + 0.5 * sum(
        1.0 for row in rows if not row.get("adjudicated") and row.get("winner") is None
    )
    low, high = wilson_interval(score, games)
    a_bound = _aggregate_reasons(rows, "a")
    b_bound = _aggregate_reasons(rows, "b")
    a_zero = _zero_reasons(rows, "a")
    b_zero = _zero_reasons(rows, "b")
    a_moves = sum(int(row.get("a_moves", 0)) for row in rows)
    b_moves = sum(int(row.get("b_moves", 0)) for row in rows)
    a_flags = _zero_flags(rows, "a")
    b_flags = _zero_flags(rows, "b")
    a_zero_count = sum(a_flags) if a_flags else sum(a_zero.values())
    b_zero_count = sum(b_flags) if b_flags else sum(b_zero.values())
    a_zero_rate = a_zero_count / a_moves if a_moves else 0.0
    b_zero_rate = b_zero_count / b_moves if b_moves else 0.0
    a_max_consecutive = max(
        max((int(row.get("a_zero_depth_max_consecutive", 0)) for row in rows), default=0),
        _max_true_run(a_flags),
    )
    b_max_consecutive = max(
        max((int(row.get("b_zero_depth_max_consecutive", 0)) for row in rows), default=0),
        _max_true_run(b_flags),
    )
    a_games_gt1 = sum(1 for row in rows if sum(bool(flag) for flag in (row.get("a_zero_depth_flags") or [])) > 1)
    b_games_gt1 = sum(1 for row in rows if sum(bool(flag) for flag in (row.get("b_zero_depth_flags") or [])) > 1)
    k2_evaluated = a_moves >= 300 and b_moves >= 300
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
    wall_percent = _round(100.0 * wall_moves / total_moves, 2) if total_moves else 0.0  # 2 位，与其余字段不同
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
    gates["zeroDepthEvaluated"] = k2_evaluated
    gates["zeroDepthRateAtMost1Percent"] = (a_zero_rate <= 0.01 and b_zero_rate <= 0.01) if k2_evaluated else True
    gates["zeroDepthNoConsecutive"] = (a_max_consecutive <= 1 and b_max_consecutive <= 1) if k2_evaluated else True
    gates["zeroDepthAtMostOnePerGame"] = (a_games_gt1 == 0 and b_games_gt1 == 0) if k2_evaluated else True
    a_upper = min(1.0, 3 / a_moves) if a_zero_count == 0 and a_moves else wilson_interval(a_zero_count, a_moves)[1]
    b_upper = min(1.0, 3 / b_moves) if b_zero_count == 0 and b_moves else wilson_interval(b_zero_count, b_moves)[1]
    k2_note = (
        f"A {a_zero_count}/{a_moves}，点估计 {a_zero_rate:.1%}，95% 上界 {a_upper:.1%}；"
        f"B {b_zero_count}/{b_moves}，点估计 {b_zero_rate:.1%}，95% 上界 {b_upper:.1%}；"
        f"连续 A={a_max_consecutive} B={b_max_consecutive}；单局>1 A={a_games_gt1} B={b_games_gt1}"
        + ("" if k2_evaluated else "（样本 <300 手，K2 未评估）")
    )
    wall_note = (
        f"本结果为产品 cap 下的 wall-bound 数据，wall 占比 {wall_percent:.2f}%"
        if not wall_enforced
        else f"target 表：wallClean 为硬门（wall 占比 {wall_percent:.2f}%）"
    )
    # v2：按"强档方向"判定。A 常排弱档（见 docstring 用法），拿 A 的 point 直接判会恒 false。
    # Wilson 对称：wilson_lower(1-p) == 1 - wilson_upper(p)，故两侧通用写法是 max(low, 1-high)。
    strong_side = "a" if point >= 0.5 else "b"
    strong_score = max(point, 1.0 - point)
    strong_low = max(low, 1.0 - high)
    win_rate_pass = strong_score >= 0.60 and strong_low >= 0.50
    gate_flags = {**gates, "winRatePass": win_rate_pass}
    pass_value = (
        win_rate_pass
        and gates["enoughGames"]
        and (gates["wallClean"] or not wall_enforced)
        and gates["noZeroDepth"]
        and gates["nodesRatioAtMost2Percent"]
        and gates["zeroDepthRateAtMost1Percent"]
        and gates["zeroDepthNoConsecutive"]
        and gates["zeroDepthAtMostOnePerGame"]
    )
    failed_gates = [
        name
        for name in (
            "winRatePass",
            "enoughGames",
            "wallClean",
            "noZeroDepth",
            "nodesRatioAtMost2Percent",
            "zeroDepthRateAtMost1Percent",
            "zeroDepthNoConsecutive",
            "zeroDepthAtMostOnePerGame",
        )
        if gate_flags[name] is False and (name != "wallClean" or wall_enforced)
    ]
    # 测量门子集：`failedGates` 里去掉**设计契约**那几项。判据只读这个字段，
    # 不要自己去减 —— 那会变成第二份"哪些是契约门"的白名单。
    failed_measurement_gates = [name for name in failed_gates if name not in CONTRACT_GATES]
    # 这次**实际评估了哪些**测量门。`failedGates == []` 只说明"评估过的都过了"，
    # 不说明"评估了同样多"（实测有 9 键与 5 键两种产物）—— 门集范围不一致时不可比。
    # `wallClean` 在 product 档只记录不判红（`wall_enforced=False`），因此不算"评估过"；
    # 零深度三兄弟在样本不足时不评估。两者都靠各自的既有条件判定，不另设白名单。
    gates_evaluated = ["enoughGames", "noZeroDepth", "nodesRatioAtMost2Percent"]
    if wall_enforced:
        gates_evaluated.append("wallClean")
    if k2_evaluated:
        gates_evaluated += [
            "zeroDepthRateAtMost1Percent",
            "zeroDepthNoConsecutive",
            "zeroDepthAtMostOnePerGame",
        ]

    # K4 设计带是独立判据，口径固定为**点估计**（非 Wilson 区间），且只走 band_pass 纯函数。
    # pass=true 只代表"强档显著强 + 数据可引用"，不代表落进 65–75%。
    band_ok = band_pass(strong_score)
    band_reason = (
        []
        if band_ok
        else [
            f"band: {strong_score:.4f} > {BAND_HIGH:.2f}"
            if strong_score > BAND_HIGH
            else f"band: {strong_score:.4f} < {BAND_LOW:.2f}"
        ]
    )
    # 契约验收是脚本门禁的子集：contractPass 为真时 pass 必为真。
    contract_pass = pass_value and band_ok
    # 契约层失败项与 failedGates 严格分开：后者只收录参与 pass 计算的脚本门禁。
    contract_failed_gates = band_reason
    return {
        "levels": {"a": level_a, "b": level_b},
        "games": games,
        "targetGames": target_n,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "score": score,
        # `winRate` = **得分率**（`score / games`，和棋计 0.5），不是字面的"胜率"。历史名，勿按字面理解。
        # 守恒关系 `winRate + strongScore == 1` 只在 `draws > 0` 时能区分"得分率 vs 胜率"
        # 两种定义（`draws = 0` 时两者同值，任何测试都抓不到改名）——所以语义只能靠这两行守。
        "winRate": _round(point, 4),
        "wilson95": [_round(low, 4), _round(high, 4)],
        "elo": (None if (elo_value := elo_from_win_rate(point)) is None else _round(elo_value, 1) or 0.0),
        "thresholdWins": threshold,
        "thresholdSide": "strong",
        "winRatePass": win_rate_pass,
        "strongSide": strong_side,
        "strongScore": _round(strong_score, 4),
        "strongLow": _round(strong_low, 4),
        "judgementVersion": "v2",
        "moveTimes": {"a": time_stats(a_times), "b": time_stats(b_times)},
        "boundReasons": {"a": a_bound, "b": b_bound},
        "zeroDepthReasons": {"a": a_zero, "b": b_zero},
        "moves": {"a": a_moves, "b": b_moves},
        "wallPercent": wall_percent,
        "wallBoundNote": wall_note,
        "zeroDepthK2": k2_note,
        "zeroDepthK2Evaluated": k2_evaluated,
        "zeroDepthRate": {"a": _round(a_zero_rate, 4), "b": _round(b_zero_rate, 4)},
        "zeroDepthMaxConsecutive": {"a": a_max_consecutive, "b": b_max_consecutive},
        "zeroDepthGamesWithGt1": {"a": a_games_gt1, "b": b_games_gt1},
        "gates": gates,
        "pass": pass_value,
        "failedGates": failed_gates,
        # 新增两字段（`failedGates` 保持原义）：没有它们，判据就得自己维护白名单、
        # 也无法发现"两份报告评估的门集不同"。**永不出 null** —— 不带键=没评估，
        # `[]`/非空=评估了。`键缺失`/`null`/`[]` 三者语义不同，读取端请用 `in` 判断。
        "failedMeasurementGates": failed_measurement_gates,
        "gatesEvaluated": sorted(gates_evaluated),
        "bandPass": band_ok,
        "contractPass": contract_pass,
        "contractFailedGates": contract_failed_gates,
        # 截断判定的口径（测量值 ÷ policy 分开记）：`games == targetGames` 是恒真的假指标，
        # 32 局里 18 局被 ply_cap 截断时它照样全过。
        "adjudicatedGames": adjudicated_games,
        "adjudicatedRatio": _round(adjudicated_games / games, 4) if games else 0.0,
        "adjudicatedRatioPolicy": ADJUDICATED_RATIO_POLICY,
        # 口径声明：`score` 仍是旧义（含截断判定），新增字段给排除口径，不改旧义。
        "scoreIncludesAdjudicated": True,
        "scoreExclAdjudicated": score_excl,
        "gamesExclAdjudicated": games_excl,
        "drawsNoResult": draws_no_result,
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
    # 两侧**实际生效**的配置先解出来：报告要写 `aiConfigDigest`，而"checkpoint 已够、
    # 直接汇总"那条路径原本不构造 config —— 放在分支里会让摘要字段在 resume 时缺失。
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
    if start_game >= args.n:
        print(f"checkpoint 已有 {start_game} 局 ≥ n={args.n}，直接汇总")
    else:
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
    # 母体 + 引擎指纹：让"档位强度变了"能分清是**规则变了**还是**母体/配置变了**。
    # 报告里的 `levels` 只有档位名、`book` 只有 size/used，而 size 与 used 在 v2/v3 下完全相同 ——
    # 不加这两个 digest，旧报告会"看起来可比、实则不可比"。
    # 顶层带**书自己声明的**版本（不是当前常量）：报告要能自证"我按哪版规则、哪个母体跑的"。
    # 老报告没有这两个字段 → 判等脚本按"不可比"处理，不追改。
    declared = json.loads(Path(args.book).read_text(encoding="utf-8"))
    report["ruleVersion"] = declared.get("ruleVersion")
    report["bookFormat"] = declared.get("format")
    report["book"]["fpDigest"] = _book_digest(book)  # type: ignore[index]
    report["aiConfigDigest"] = {
        "a": _config_digest(args.level_a, config_a),
        "b": _config_digest(args.level_b, config_b),
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    output = Path(args.output) if args.output else checkpoint.with_suffix(".report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")

    print(
        f"{args.level_a} vs {args.level_b}  n={report['games']}  "
        f"{report['wins']}-{report['losses']}-{report['draws']}  "
        f"winRate={report['winRate']:.3f}  Wilson={report['wilson95']}  "
        f"threshold={report['thresholdWins']}({report['thresholdSide']})  "
        f"pass={report['pass']}  contractPass={report['contractPass']}"
    )
    print(
        f"strong={report['strongSide']}:{report['strongScore']}  "
        f"bandPass={report['bandPass']}  "
        f"contractFailedGates={report['contractFailedGates']}  "
        "（pass 只表示档位可分，不等于落进 65–75% 设计带）"
    )
    print(f"gates={report['gates']}  bound={report['boundReasons']}")
    print(report["wallBoundNote"])
    print(f"报告：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
