"""报告小数的舍入护栏：`_round` 必须是纯 `round`，且 tie 行为是 half-to-even。

## 为什么要单独测"舍入"

`winRate + strongScore == 1` 这条守恒关系，依赖两边用**同一个** `round(_, 4)`。
生成端一旦有一处被改成 half-up，或有人"顺手加个 1e-9 修浮点误差"，数值会变、
而**几乎所有测试仍然绿** —— 因为本轮锚点 `13.5/64 = 0.2109375` 与 `50.5/64 = 0.7890625`
**都不是 tie**（第 5 位分别是 3 和 6），走不到 tie 分支。舍入模式的覆盖缺口是 **100%**，
本文件是唯一保护。

## 两个必须写进代码的坑（改之前先读）

1. **oracle 必须 `Decimal(v)`（float 的精确值），不能 `Decimal(str(v))`。**
   `str` 口径把输入域换成十进制，会造出**生产中不存在的 tie**：`nd=2, den=200` 时
   str 口径给 50 个"tie"，float 口径只给 2 个（`0.125 / 0.625`）。`0.015` 就是典型：
   它在十进制里是 tie，但 float 里略小于 0.015，`round()` 根本不走 tie 分支。
   而且这个坑**换判别器救不回来**，只有换 oracle 才修好。
2. **判别器必须让两种舍入模式作用于同一个 exact 值**：
   `exact.quantize(q) != exact.quantize(q, rounding=ROUND_HALF_UP)`。
   若写成 `round(v, n) != float(exact.quantize(q, ROUND_HALF_UP))`，测到的是
   float 与 decimal 的**表示差异**，不是舍入模式差异 —— 会"报覆盖但没覆盖"。

## tie 只在第 4 位为偶数时才区分

`0.96875` 是 tie 但第 4 位是 7（奇），half-even 与 half-up 都给 `0.9688`，**无区分力**。
`0.005` 更不是 tie（float 里略大于 0.005，两模式都上进）。所以用例只能从
`float_exact_ties()` 里取，不能手挑"看起来像 tie"的十进制数。
"""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "benchmarks" / "calibration_runs"
STEM = "2026-11-11-bm-final-n64"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from calibrate_levels import _round, summarize  # noqa: E402


def float_exact_ties(ndigits: int) -> list[float]:
    """`ndigits` 位小数下**能被 float 精确表示**、且两舍入模式给出不同结果的 tie。

    完备性：tie 要求 `v = (2m+1) / (2·10^nd)` 且 float 可精确表示 ⇒ `5^nd | (2m+1)`
    ⇒ `v = j / 2^(nd+1)`，j 为奇数；反向亦成立（末位必为 5）。所以枚举奇数 j
    就穷尽了"float 可表示的 tie"，遗漏为零。

    没有 `den` 参数是有意的：任何"该填哪个分母"的参数都是"可能填错"的位置，
    而 `den` 从 `report["games"]` 推会让 n=100 的报告红 —— 那是正确结果，却看起来像测试坏了。
    """
    out: list[float] = []
    q = Decimal(1).scaleb(-ndigits)
    for j in range(1, 2 ** (ndigits + 1), 2):
        value = j / 2 ** (ndigits + 1)
        exact = Decimal(value)  # ← 必须 Decimal(v)，不能 Decimal(str(v))
        if exact.quantize(q) != exact.quantize(q, rounding=ROUND_HALF_UP):
            out.append(value)
    return out


def test_tie_enumerator_is_not_degenerate() -> None:
    """生成器自身要够用：4 位 8 个、2 位 2 个、3 位 4 个（将来换精度可直接复用）。"""
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
    """被测是 `_round`（不是内置 `round`）——写内置就是"参考 vs 参考"，绿了也没碰实现。"""
    ties = float_exact_ties(ndigits)
    assert len(ties) == expected_count, "枚举退化了：tie 集合变少说明生成器写错"
    quantum = Decimal(1).scaleb(-ndigits)
    for value in ties:
        exact = Decimal(value)
        # ① 实现 vs 独立 oracle（Decimal 的 half-even）
        assert _round(value, ndigits) == float(exact.quantize(quantum)), f"{value} @ {ndigits} 位"
        # ② 本用例确实有区分力：half-up 必须给出不同结果，否则它在测空气
        assert exact.quantize(quantum, rounding=ROUND_HALF_UP) != exact.quantize(quantum), (
            f"{value} @ {ndigits} 位 对舍入模式不敏感，不能承担覆盖"
        )


def test_non_discriminating_ties_are_documented_not_used() -> None:
    """这两条**不承担覆盖**，只记录"为什么它们不进上面的循环"。

    `0.96875` 是 tie 但第 4 位为奇数 → 两模式同值；`0.005` 在 float 里不是 tie。
    """
    assert _round(0.96875, 4) == 0.9688
    assert _round(0.005, 2) == 0.01  # float 略大于 0.005，两模式都上进 —— 不是 tie


def _artifacts_present() -> bool:
    """`calibration_runs/` 是本地运行输出，仓库不跟踪 —— 缺产物时跳过相关用例，不红。"""
    return (RUNS / f"{STEM}.report.json").is_file() and (RUNS / f"{STEM}.jsonl").is_file()


needs_artifacts = pytest.mark.skipif(not _artifacts_present(), reason="缺少本地标定产物（运行输出不进仓库）")


def _report() -> dict:
    path = RUNS / f"{STEM}.report.json"
    assert path.is_file(), f"缺仓库外的本地产物 {path.name}"
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


@needs_artifacts
def test_report_rounding_values_are_pinned() -> None:
    """金测试：从**报告文件**读（顺带覆盖写盘层），钉住所有舍入字段。

    没有这条，"`_round` 是纯 round、没塞 epsilon" 就只是一句声明 —— 给 helper 加
    `+1e-9` 修"浮点误差"这类改动会静默通过。
    """
    report = _report()
    assert report["winRate"] == Decimal("0.2109")
    assert report["strongScore"] == Decimal("0.7891")
    assert report["strongLow"] == Decimal("0.6742")
    # 注意量纲：`wallPercent` 是**百分数、2 位小数**，与其余 4 位小数的比例字段不同。
    assert report["wallPercent"] == Decimal("0.16")
    assert report["wilson95"] == [Decimal("0.1289"), Decimal("0.3258")]
    assert report["zeroDepthRate"] == {"a": Decimal("0.0"), "b": Decimal("0.0")}


@needs_artifacts
def test_win_rate_is_the_score_ratio_not_the_win_ratio() -> None:
    """`winRate` 存的是**得分率**（`score / games`，和棋计 0.5），不是 `wins / games`。

    守恒关系 `winRate + strongScore == 1` 用 `Decimal` 读**已存储**值做加法，全程不涉及舍入；
    顺带钉住语义：将来谁把名字"修正"成 `wins / games`，这个和立刻不等于 1。

    可识别性的固有限制：`draws == 0` 时两种定义同值，这条断言抓不到改名 ——
    所以生成端那段"`winRate` = 得分率，历史名，勿按字面理解"的注释是必需的，不能删。
    """
    report = _report()
    assert report["winRate"] + report["strongScore"] == Decimal("1")
    # 本轮 draws=1，所以两种定义确实不同值：得分率 0.2109、胜率 13/64=0.203125
    assert report["draws"] > 0, "这条断言的可识别性依赖 draws > 0"
    assert report["winRate"] != Decimal(str(round(report["wins"] / report["games"], 4)))


@needs_artifacts
def test_writer_emits_the_same_rounded_values_and_the_new_ratio() -> None:
    """重跑汇总函数（不跑棋）必须复现同样的舍入值，且产出 `adjudicatedRatio`。

    历史报告没有 `adjudicatedRatio`（本字段后加），所以它只能从写出端验证。
    这条同时证明 `_round` 在所有字段上都被用到了 —— 漏掉一处，值就会与磁盘报告不一致。
    """
    jsonl = RUNS / f"{STEM}.jsonl"
    assert jsonl.is_file(), f"缺本地产物 {jsonl.name}"
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    fresh = summarize(rows, "beginner", "medium", 64, 64)
    stored = _report()

    for key in ("winRate", "strongScore", "strongLow", "wallPercent"):
        assert fresh[key] == pytest.approx(float(stored[key]), abs=1e-9), key
    assert fresh["adjudicatedRatio"] == pytest.approx(0.125, abs=1e-9)
