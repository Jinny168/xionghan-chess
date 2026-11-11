"""报告小数的舍入护栏：`_round` 必须是纯 `round`，且 tie 行为是 half-to-even。

## 为什么要单独测"舍入"

`winRate + strongScore == 1` 这条守恒关系依赖两边用**同一个** `round(_, 4)`。
生成端一旦有一处被改成 half-up，或有人"顺手加个 1e-9 修浮点误差"，数值会变、
而**几乎所有测试仍然绿** —— 因为本轮锚点 `13.5/64 = 0.2109375` 与 `50.5/64 = 0.7890625`
**都不是 tie**（第 5 位分别是 3 和 6），走不到 tie 分支。舍入模式的覆盖缺口是 **100%**。

## 三层各守一件事（别让任何一层变成"永远绿"）

1. **tie 单测**：`_round` vs `Decimal.quantize` 的 half-even，输入由 `float_exact_ties()` 生成。
   不依赖任何本地文件 → CI 一定跑。
2. **单入口（AST 级）**：`calibrate_levels.py` 里裸 `round(` 只允许出现在 `_round` 内部。
   防"新加字段时顺手写 `round(x, 4)`"——那是真会发生的事。
3. **守恒不变量 + 写出端**：跑 `tests/fixtures/mini_calibration.jsonl`（8 局，随仓库走）
   复现 `summarize()`，断言 `winRate + strongScore == 1` 与各字段的舍入值。
   **不能用 `.report.json` / `.jsonl` 真产物** —— 它们不进仓库，CI 里会静默 skip，
   于是这条核心不变量在 CI 里根本不跑（本项目已经踩过一次"静默 skip"的坑）。

## 两个必须写进代码的坑

1. **oracle 必须 `_exact(v)` = `Decimal(v)`（float 精确值），不能 `Decimal(str(v))`。**
   `str` 口径把输入域换成十进制，会造出**生产中不存在的 tie**。这个错本轮**真实发生过**
   （写生成器的人自己写的），而且在生产参数下**完全静默**：`den=64` 时两种口径都给 8 个、
   `den=8` 都给 2 个，只有非真实的 `den=200` 才分叉（50 vs 2）。
   所以只能靠直接断言 `_exact` 的语义来守，行为断言抓不到。
2. **判别器必须让两种舍入模式作用于同一个 exact 值**。
   写成 `round(v, n) != float(exact.quantize(q, HALF_UP))` 会把 float 与 decimal 的
   **表示误差**记成"舍入模式差异"（`0.015` 即此类）。
"""

from __future__ import annotations

import ast
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUNS = ROOT / "benchmarks" / "calibration_runs"
FIXTURE = ROOT / "tests" / "fixtures" / "mini_calibration.jsonl"
STEM = "2026-11-11-bm-final-n64"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from calibrate_levels import _round, summarize  # noqa: E402


def _exact(value: float) -> Decimal:
    """`float` 的**精确**十进制值。

    **禁止改成 `Decimal(str(value))`**：那会把输入域换成"十进制读法"，造出生产中不存在的
    tie（`0.015` 在 float 里略小于精确值，`round()` 根本不走 tie 分支）。本轮这个错真实
    发生过，而且生产参数下完全静默 —— 见模块 docstring。
    """
    return Decimal(value)


def float_exact_ties(ndigits: int) -> list[float]:
    """`ndigits` 位小数下**能被 float 精确表示**、且两种舍入模式给出不同结果的 tie。

    完备性：tie 要求 `v = (2m+1)/(2·10^nd)` 且 float 可精确表示 ⇒ `5^nd | (2m+1)`
    ⇒ 记 `2m+1 = j·5^nd`（j 奇）⇒ `v = j / 2^(nd+1)`。反向：`j/2^(nd+1) = j·5^(nd+1)/10^(nd+1)`，
    j 奇 ⇒ 末位必为 5 ⇒ 恰是 nd 位 tie。故枚举奇 j 即"全部且仅有的 float 可精确 tie"。

    **不要改成按分母枚举**：真实 `games ∈ {10,20,25,40,50,64,100,128}` 下两种写法结论相同
    （不可达），但一旦有人引入非真实分母（如 `den=200`），会造出 50 个假 tie（真实只有 2 个）。
    """
    quantum = Decimal(1).scaleb(-ndigits)
    out: list[float] = []
    for j in range(1, 2 ** (ndigits + 1), 2):
        value = j / 2 ** (ndigits + 1)  # 天生二进制精确
        exact = _exact(value)
        if exact.quantize(quantum) != exact.quantize(quantum, rounding=ROUND_HALF_UP):
            out.append(value)
    return out


# ---------------------------------------------------------------------------
# ① oracle 语义（唯一能抓住 `str(v)` 回归的地方）
# ---------------------------------------------------------------------------
def test_exact_oracle_uses_float_semantics() -> None:
    """`0.005` 是唯一抓手：float 里它略大于精确值，而十进制读法会把它当精确 0.005。"""
    assert _exact(0.005) != Decimal("0.005"), "改成 Decimal(str(v)) 了？那会造出生产中不存在的 tie"
    assert _exact(0.03125) == Decimal("0.03125"), "二进制可精确表示的值必须相等"


def test_tie_enumeration_is_not_degenerate() -> None:
    """枚举边界 / 奇偶过滤写错时红；顺带证明换精度可复用。"""
    assert float_exact_ties(4) == [
        0.03125,
        0.15625,
        0.28125,
        0.40625,
        0.53125,
        0.65625,
        0.78125,
        0.90625,
    ]
    assert float_exact_ties(2) == [0.125, 0.625]
    assert len(float_exact_ties(3)) == 4


@pytest.mark.parametrize(("ndigits", "expected_count"), [(4, 8), (2, 2)])
def test_round_is_half_to_even_on_every_representable_tie(ndigits: int, expected_count: int) -> None:
    """被测是 `_round`，不是内置 `round` —— 写成内置就是"参考 vs 参考"，绿了也没碰实现。"""
    ties = float_exact_ties(ndigits)
    assert len(ties) == expected_count, "枚举退化了"
    quantum = Decimal(1).scaleb(-ndigits)
    for value in ties:
        exact = _exact(value)
        # ① 实现 vs 独立 oracle（Decimal 的 half-even）
        assert _round(value, ndigits) == float(exact.quantize(quantum)), f"{value} @ {ndigits} 位"
        # ② 本用例确实有区分力：half-up 必须给出不同结果，否则它在测空气
        assert exact.quantize(quantum, rounding=ROUND_HALF_UP) != exact.quantize(quantum), (
            f"{value} @ {ndigits} 位 对舍入模式不敏感"
        )


def test_non_discriminating_ties_are_documented_not_used() -> None:
    """这两条**不承担覆盖**，只记录"为什么它们不进上面的循环"。

    `0.96875` 是 tie 但第 4 位为奇数 → 两模式同值；`0.005` 在 float 里根本不是 tie。
    """
    assert _round(0.96875, 4) == 0.9688
    assert _round(0.005, 2) == 0.01


# ---------------------------------------------------------------------------
# ② 舍入单入口（AST 级：`round(` 是 `_round(` 的子串，文本匹配必然误报）
# ---------------------------------------------------------------------------
def test_all_rounding_goes_through_the_helper() -> None:
    """裸 `round()` 只允许出现在 `_round` 函数体内。

    防的是"新加一个比例字段时顺手写 `round(x, 4)`"——那一处会绕过 tie 护栏，
    而且不会有任何行为测试变红（只有它的取值恰好落在 tie 上才看得出来）。
    """
    source = (SCRIPTS / "calibrate_levels.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    helper = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_round"
    )
    body_start = helper.lineno
    body_end = max(getattr(node, "lineno", body_start) for node in ast.walk(helper))

    calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round"
    ]
    outside = [line for line in calls if not body_start <= line <= body_end]
    assert not outside, f"存在裸 round() 调用（行 {outside}）：所有舍入必须走 _round(x, ndigits)"
    assert len(calls) == 1, f"`_round` 内部应当恰好一次 round()，实际 {len(calls)} 处"


# ---------------------------------------------------------------------------
# ③ 守恒不变量 + 写出端（跑随仓库走的 mini fixture → CI 一定执行）
# ---------------------------------------------------------------------------
def _mini_rows() -> list[dict]:
    assert FIXTURE.is_file(), f"缺 fixture：{FIXTURE}"
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def _mini_report() -> dict:
    return summarize(_mini_rows(), "beginner", "medium", 64, 8)


# 容差 1e-4 的依据（实测枚举，不是推演）：
#   在 2..800 的全部偶数局数里，`k/(2g)` 会撞上"十进制是 4 位 tie、但 float 不精确"的
#   取值，两个补数各自舍入后和偏离 1 —— 且**偏离集恰好是 80 的所有倍数**
#   （[80,160,240,320,400,480,560,640,720,800]），偏差为 **±0.0001 双边**。
#   生产候选 {10,20,25,40,50,64,100,128} 全部精确相等，但 `--n 80` 一条命令就能踩到。
#   容差只放过这 1 个 ulp：语义改名（得分率 0.3125 vs 胜率 0.25，差 0.0625）远大于它。
CONSERVATION_TOLERANCE = Decimal("0.0001")


def test_win_rate_plus_strong_score_is_within_one_unit() -> None:
    """守恒关系在**写出端产物**上也成立（容差 1 个 4 位单位，见上）。

    这条用 fixture 跑，所以 **CI 里真的会执行** —— 之前的版本依赖 `.report.json`
    （不进仓库），在干净 clone 上会静默 skip，等于这条核心不变量没被守。
    """
    report = _mini_report()
    delta = Decimal(str(report["winRate"])) + Decimal(str(report["strongScore"])) - Decimal("1")
    assert abs(delta) <= CONSERVATION_TOLERANCE, delta


def test_ratio_conservation_on_all_reachable_scores() -> None:
    """纯函数性质：不依赖任何产物，任何环境都会跑。

    扫生产候选局数下的**全部可达得分**（`k/(2g)`，k 从 0 到 2g 覆盖每半分局），
    两个补数的舍入结果之和必须落在 1 的 1 个 ulp 内。
    """
    for games in (10, 20, 25, 40, 50, 64, 100, 128):
        for k in range(0, 2 * games + 1):
            score = k / 2
            total = _round(score / games, 4) + _round((games - score) / games, 4)
            assert abs(total - 1) <= 1e-4, (games, k, total)


def test_conservation_deviation_is_confined_to_multiples_of_80() -> None:
    """特征断言：偏离的局数**恰好是 80 的倍数**。

    这条把"容差该多大"从口头依据变成机器判据：若它红了，说明 `--n` 的取值域或舍入实现
    变了 —— 那时才该重新决定容差（而不是直接调大数字）。
    范围写进断言，红的时候能一眼看出是"范围变了"还是"回归了"。
    用 `_round` 而不是内置 `round`：后者测的是平台，不是报告路径。
    """
    deviating = {games for games in range(2, 801, 2) if _deviates(games)}
    assert deviating == set(range(80, 801, 80)), deviating
    # 钉住已知偏离的具体量与方向（双边都实测出现过，所以必须取绝对值）
    assert abs(_round(0.5 / 80, 4) + _round(79.5 / 80, 4) - 1) == pytest.approx(1e-4)
    assert abs(_round(0.5 / 64, 4) + _round(63.5 / 64, 4) - 1) == 0  # 生产候选：精确相等


def _deviates(games: int) -> bool:
    return any(
        _round((k / 2) / games, 4) + _round((games - k / 2) / games, 4) != 1.0
        for k in range(0, 2 * games + 1)
    )


def test_win_rate_is_the_score_ratio_not_the_win_ratio() -> None:
    """`winRate` 存的是**得分率**（`score / games`，和棋计 0.5），不是 `wins / games`。

    可识别性依赖 `draws > 0`（`draws = 0` 时两种定义同值，任何断言都抓不到改名）——
    fixture 特意挑了一局和棋，所以这里能真的区分：得分率 `0.3125` vs 胜率 `0.25`。
    生成端那段"历史名、勿按字面理解"的注释因此是必需的，不能删。
    """
    report = _mini_report()
    assert report["draws"] > 0, "fixture 必须含和棋，否则这条断言没有区分力"
    assert report["winRate"] == 0.3125
    assert report["winRate"] != _round(report["wins"] / report["games"], 4)  # 胜率是 0.25


def test_mini_fixture_writer_rounds_every_ratio_field() -> None:
    """写出端各比例字段的舍入值（顺带覆盖 2 位的 `wallPercent`，它与其他字段精度不同）。"""
    report = _mini_report()
    assert report["winRate"] == 0.3125
    assert report["strongScore"] == 0.6875
    assert report["adjudicatedRatio"] == 0.125  # 1/8，无舍入歧义，但证明该字段被写出
    assert report["wallPercent"] == pytest.approx(0.47, abs=1e-9)  # 2 位


# ---------------------------------------------------------------------------
# ④ 历史报告金测试（本地产物，CI 上跳过 —— 它的守卫职责已由 ③ 的 fixture 承接）
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not (RUNS / f"{STEM}.report.json").is_file(), reason="缺少本地标定产物（calibration_runs/ 不进仓库）"
)
def test_historical_report_rounding_values_are_pinned() -> None:
    """钉住那一份历史报告的实际取值，防"helper 被塞进 epsilon"这类静默改数值。

    注意量纲：`wallPercent` 是**百分数、2 位小数**，其余比例字段是 4 位。
    """
    report = json.loads((RUNS / f"{STEM}.report.json").read_text(encoding="utf-8"), parse_float=Decimal)
    assert report["winRate"] == Decimal("0.2109")
    assert report["strongScore"] == Decimal("0.7891")
    assert report["strongLow"] == Decimal("0.6742")
    assert report["wallPercent"] == Decimal("0.16")
    assert report["wilson95"] == [Decimal("0.1289"), Decimal("0.3258")]
    assert report["zeroDepthRate"] == {"a": Decimal("0.0"), "b": Decimal("0.0")}
