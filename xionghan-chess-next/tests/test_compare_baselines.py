"""标定基线比较脚本的自检（`comparable` / `conclusion` 两段判据）。

## 五条自检，每条专测一道门

    ① final-n64 vs 自身        → comparable=True,  IDENTICAL      ← 专测"②③ 不会恒假"
    ② c1-n10  vs 自身          → comparable=False, IDENTITY_MISSING
    ③ c1-n10  vs final-n64     → comparable=False, IDENTITY_MISSING（① 先于 ②）
    ④ 合成身份：仅 aiConfigDigest 不同 → IDENTITY_CONFIG    ← 测"配置真被比了"
    ⑤ 合成扰动                 → comparable=True,  DIFFERENCE，区间不含 0

**① 最关键**：它是唯一能证明"判据在应该通过的样本上真的通过"的办法。
判据很容易退化成"永远说不"，而永远说不的门禁比没有门禁更糟 —— 所有人都会绕过它。

## ④ 为什么用合成身份而不是真文件

原规格写的是「`bm-final-n64` vs `bm-root18-final-n64` → IDENTITY_CONFIG」。实测**做不到**：
root18 那份没有可比性元数据（无 `fpDigest` / `aiConfigDigest` / `gatesEvaluated`），
所以判据在 ① 就返回 `IDENTITY_MISSING` —— 这本身是对的：**没有元数据就无法断言"配置不同"**。
要测「`aiConfigDigest` 是否真的接线」，只能用两份**都有**身份、仅配置不同的样本。

（随之而来的结论：root18 在补 sidecar 之前不能当可比基线用。已单独报告，不在本文件断言。）

## ⑤ 的合成扰动：钉 RNG 无关的量，断蒙特卡洛量的方向

- **确定性量**（可精确断言）：`blocksPaired == 32`、点估计 `== k/blocksPaired == 0.3125`、
  选块规则（按块 id 升序取前 k 个 A=0 块）、可用 A=0 块数 ≥ k。
- **稳健性质**（只断方向）：下界 `>= 0.15`、上界 `> 点估计`。

**不要断言精确端点**：端点由蒙特卡洛决定，任何种子/RNG 实现变更都会让它红，
而红的原因与"③ 是否退化"无关 —— 只会训练人去改数字。

## 这个用例什么时候该红（半年后有人看到红，请先读这里）

| 红因 | 处置 |
|---|---|
| bootstrap 实现变了（percentile→BCa、次数、种子处理） | 正常红，更新端点/方向断言，**不许放宽** |
| 构造规则变了（不是 `s→1-s`、不是只挑 A=0 块） | 正常红，连期望值一起改；**不许改成"随便挑块"** —— 只有 A=0 块翻转后每块恰好 +1 |
| 数据侧变了（jsonl / `master_color` 布局 / 块划分） | **异常红**，先查为什么被动过，别改断言 |
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "benchmarks" / "calibration_runs"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from compare_baselines import Baseline, _identity_check, block_scores, compare, paired_conclusion  # noqa: E402

FINAL = "2026-11-11-bm-final-n64"
C1_N10 = "2026-11-10-bm-c1-n10"

# 数据侧锚点：一红就说明 jsonl 或块划分被动过，而不是统计量变了。
EXPECTED_SCORE_DISTRIBUTION = {0.0: 20, 0.5: 10, 0.75: 1, 1.0: 1}
# A=0 块（0-based 块号，升序）。k=10 时按升序取前 10 个。
EXPECTED_ZERO_BLOCKS = [2, 3, 5, 6, 7, 9, 10, 14, 15, 16, 17, 19, 21, 23, 26, 27, 28, 29, 30, 31]


def _artifacts_present() -> bool:
    """两份基线的产物都在时才有意义（`calibration_runs/` 是本地运行输出，不进仓库）。"""
    required = [
        *[RUNS / f"{stem}.{suffix}" for stem in (FINAL, C1_N10) for suffix in ("jsonl", "report.json")],
    ]
    return all(path.is_file() for path in required)


pytestmark = pytest.mark.skipif(not _artifacts_present(), reason="缺少本地标定产物（运行输出不进仓库）")


def _final() -> Baseline:
    return Baseline(FINAL)


def test_self_comparison_is_comparable_and_identical() -> None:
    """① 同一份报告 vs 自身：必须"可比、且无差异"。

    这条专测"② 与 ③ 不会恒假"。若它红，说明 ② 或 ③ 里又写进了在这份真实数据上
    不可判定的条件 —— 而不是说明数据有问题。
    """
    result = compare(FINAL, FINAL)
    assert result["comparable"] is True, f"自比较竟然不可比：{result.get('notes')}"
    assert result["conclusion"]["conclusion"] == "IDENTICAL"
    assert result["conclusion"]["pointEstimate"] == 0.0
    assert result["conclusion"]["ci95"] == [0.0, 0.0]


def test_baseline_without_metadata_is_identity_missing() -> None:
    """② c1-n10 自身比较：缺可比性元数据 → `IDENTITY_MISSING`。

    注意它**不是** `DEFORMED`：缺身份时连"是否变形"都不该判 —— 拿两份不同母体
    去比测量质量没有意义，报 `DEFORMED` 会把排查引到错误方向。
    """
    result = compare(C1_N10, C1_N10)
    assert result["comparable"] is False
    assert result["reason"] == "IDENTITY_MISSING"


def test_identity_is_checked_before_deformation() -> None:
    """③ c1-n10 vs final：先命中 `IDENTITY_MISSING`，**不能**是 `DEFORMED`。

    c1-n10 同时 `wallPercent=70.96%`（真变形），但如果先报 DEFORMED，说明判定顺序错了。
    """
    result = compare(C1_N10, FINAL)
    assert result["comparable"] is False
    assert result["reason"] == "IDENTITY_MISSING", "① 必须排在 ② 前面"


class _FakeBaseline:
    """只带身份字段的最小桩，用来单测"配置是否真被比了"。"""

    def __init__(self, identity: dict) -> None:
        self.report = None
        self.meta = None
        self.stem = "synthetic"
        self._identity = identity

    def identity(self, key: str):
        return self._identity.get(key)

    @property
    def from_backfill(self) -> bool:
        return False


def test_identity_config_mismatch_is_detected() -> None:
    """④ 仅 `aiConfigDigest` 不同 → `IDENTITY_CONFIG`。

    原规格想用 `final-n64` vs `root18` 测这一条，但 root18 没有元数据（会在 ① 返回
    `IDENTITY_MISSING`）。所以这里用合成身份测"接线"，而不是把 root18 的数据补出来 ——
    补出来的只是猜测，猜出来的身份比缺身份更糟。
    """
    base = {"fpDigest": "x", "aiConfigDigest": {"a": "1", "b": "2"}, "judgementVersion": "v2"}
    other = {**base, "aiConfigDigest": {"a": "1", "b": "3"}}
    assert _identity_check(_FakeBaseline(base), _FakeBaseline(other)) == "IDENTITY_CONFIG"
    # 其余不变时应当通过身份检查
    assert _identity_check(_FakeBaseline(base), _FakeBaseline(dict(base))) is None


def test_synthetic_perturbation_gives_a_non_degenerate_conclusion() -> None:
    """⑤ 合成扰动必须给出 `DIFFERENCE` 且区间不含 0 —— 证明 ③ 不是恒 IDENTICAL。

    **只证明 ③ 能给出非退化结论，不得作为 v3 强度变化的证据引用。**
    """
    scores = block_scores(_final().rows)

    # ---- 构造前提（消失时要明确报"前提没了"，而不是莫名其妙的索引错）----
    assert len(scores) == 32, "配对块数变了（整块剔除被接进 ③？）"
    distribution = Counter(scores)
    assert dict(distribution) == EXPECTED_SCORE_DISTRIBUTION, "数据侧锚点变了：查 jsonl 或块划分"
    zero_blocks = [index for index, score in enumerate(scores) if score == 0.0]
    assert zero_blocks == EXPECTED_ZERO_BLOCKS, "A=0 块集合变了"
    k = 10
    assert len(zero_blocks) >= k, f"可用 A=0 块只有 {len(zero_blocks)} 个，不够 k={k}"

    # ---- 构造：按块 id 升序取前 k 个 A=0 块，逐块 s → 1-s ----
    # 只有 A=0 的块翻转后**每块恰好 +1**，所以点估计恒等于 k/blocksPaired，与 RNG 无关。
    picked = sorted(zero_blocks)[:k]
    perturbed = list(scores)
    for index in picked:
        perturbed[index] = 1.0 - perturbed[index]

    result = paired_conclusion(perturbed, scores)
    # ---- 确定性量：可精确断言 ----
    assert result["blocksPaired"] == 32
    assert result["pointEstimate"] == pytest.approx(k / 32, abs=1e-9), "点估计必须等于 k/blocksPaired"
    # ---- 稳健性质：只断方向，不断端点 ----
    assert result["ci95"][0] >= 0.15, f"下界 {result['ci95'][0]} 太低，③ 对真实差异不敏感"
    assert result["ci95"][1] > result["pointEstimate"]
    assert result["conclusion"] == "DIFFERENCE"
