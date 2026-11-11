"""比较两份标定基线：`comparable`（能不能比）与 `conclusion`（比完能不能下结论）。

## 为什么是两个输出，不是一个布尔

一份合规、只是"没观察到差异"的测量，如果被合成一个布尔判成"不可比"，人会去改测量 ——
而正确答案是"没观察到差异"。所以：

    comparable : bool    = ① 身份 ∧ ② 未变形
    conclusion : 三态     = ③（仅当 comparable 为真才求值）
        DIFFERENCE    差值 95% 区间不含 0
        INSUFFICIENT  区间含 0，且差值并非恒 0   → 动作：加样本
        IDENTICAL     差值恒 0（区间恒 [0,0]）   → 动作：不该做这个比较

## 判定顺序也是规范的一部分

① 身份 → ② 未变形 → ③ 超噪声。身份不对时**连"是否变形"都不判**：拿两份不同母体
去比测量质量没有意义，报 `DEFORMED` 会把人引向错误的排查方向。

reason code（取先命中者）：`IDENTITY_MISSING` / `IDENTITY_CONFIG` / `IDENTITY_JUDGEMENT` /
`DEFORMED` / `INSUFFICIENT` / `IDENTICAL`。

## ② 引用既有聚合判定，不自己列 gate 键

代码里 `failed_gates` 已经把 product/target 的例外折进去了（`wallClean` 在 product 档
只记录不判红），也混了 `winRatePass`（设计契约，常态会失败）。所以：

- 判"墙钟污染"用 `wallPercent <= 2%`，**不要**用 `gates.wallClean` 布尔 ——
  实测两份可用基线都是 `wallClean=False`（各有一手被墙钟截断），按布尔会把它们全否掉；
- 判"测量门"用报告里的 `failedMeasurementGates`，**不要**做 `- {"winRatePass"}` 减法 ——
  那又是一份靠人维护的白名单。

## 自检（本脚本必须能同时满足，写在这里供后来人核）

    ① bm-final-n64 vs 自身        → comparable=True,  IDENTICAL
    ② c1-n10 vs 自身              → comparable=False, IDENTITY_MISSING（缺可比性字段）
    ③ c1-n10 vs bm-final-n64      → comparable=False, IDENTITY_MISSING（① 先于 ②）
    ④ bm-final-n64 vs root18      → comparable=False, IDENTITY_CONFIG（root_limit 16 vs 18）
    ⑤ 合成扰动                    → comparable=True,  DIFFERENCE（区间不含 0）

**① 是最关键的一条**：它是唯一能证明"判据在应该通过的样本上真的通过"的办法。
判据很容易变成"永远说不"的门禁，而永远说不的门禁比没有门禁更糟 —— 所有人都会绕过它。

用法：
    python scripts/compare_baselines.py <stem-a> <stem-b> [--bootstrap 2000] [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "benchmarks" / "calibration_runs"

# ---- policy（设计判断，会被数据推翻；与测量值分开）----
WALL_PERCENT_POLICY = 2.0
ADJUDICATED_RATIO_POLICY = 0.2
ADJUDICATED_DELTA_POLICY = 0.05
BLOCKS_FULLY_ADJUDICATED_POLICY = 2

DEFAULT_BOOTSTRAP = 2000
DEFAULT_SEED = 20260807


def _load_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


class Baseline:
    """一份基线：报告 + jsonl + （可选）backfill sidecar。

    身份字段优先取 sidecar —— 历史报告没有它们，而 sidecar 是**事后**补的，
    所以结论里必须能看出"哪些字段来自回填"。
    """

    def __init__(self, stem: str) -> None:
        self.stem = stem
        # 显式文件名：`<stem>.report.json` 有判定层，孪生的 `<stem>.v1.report.json` 没有。
        self.report = _load_json(RUNS / f"{stem}.report.json")
        self.meta = _load_json(RUNS / f"{stem}.meta.json")
        jsonl = RUNS / f"{stem}.jsonl"
        self.rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]

    # ---- 身份 ----
    def identity(self, key: str):
        if self.report and key in self.report:
            return self.report[key]
        if self.meta:
            return self.meta["fields"].get(key, self.meta.get(key))
        return None

    @property
    def from_backfill(self) -> bool:
        return bool(self.meta and self.meta.get("backfilled"))


def block_scores(rows: list[dict]) -> list[float]:
    """每 2 局一个开局块（同一开局红黑各一），块内取**该侧**得分均值。

    坑：`master_color` 是 **A 侧**的颜色，不是"master＝强档"。用反了不报错，
    只会得到 `1 - score` 那种看起来同样合理的数。
    """
    out: list[float] = []
    for start in range(0, len(rows), 2):
        pair = rows[start : start + 2]
        out.append(
            sum(
                1.0 if row["winner"] == row["master_color"] else 0.5 if row["winner"] is None else 0.0
                for row in pair
            )
            / len(pair)
        )
    return out


def paired_conclusion(
    a_blocks: list[float], b_blocks: list[float], *, bootstrap: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED
) -> dict:
    """③ 配对 bootstrap。**必须给点估计 + 区间 + blocksPaired**，否则无法断言"区间不含 0"。"""
    assert len(a_blocks) == len(b_blocks), f"块数不等：{len(a_blocks)} vs {len(b_blocks)}"
    diffs = [a - b for a, b in zip(a_blocks, b_blocks)]
    point = statistics.fmean(diffs) if diffs else 0.0
    rng = random.Random(seed)
    means = []
    for _ in range(bootstrap):
        means.append(statistics.fmean(rng.choices(diffs, k=len(diffs))))
    means.sort()
    low = means[int(0.025 * len(means))]
    high = means[int(0.975 * len(means)) - 1]
    if max(diffs) == min(diffs) == 0:
        verdict = "IDENTICAL"
    elif low > 0 or high < 0:
        verdict = "DIFFERENCE"
    else:
        verdict = "INSUFFICIENT"
    return {
        "conclusion": verdict,
        "pointEstimate": round(point, 4),
        "ci95": [round(low, 4), round(high, 4)],
        "blocksPaired": len(diffs),
        "bootstrap": bootstrap,
        "seed": seed,
        "resolution": round(1 / len(diffs), 4) if diffs else None,
    }


def _identity_check(a: Baseline, b: Baseline) -> str | None:
    """① 身份：缺字段 → MISSING；配置不同 → CONFIG；判定层不同 → JUDGEMENT。

    身份只认三项：母体指纹、引擎指纹、判定层版本。
    `gatesEvaluated` **不属于身份** —— 它是"② 未变形"里的门集范围条件（见下）。
    """
    required = ("fpDigest", "aiConfigDigest", "judgementVersion")
    for base in (a, b):
        if any(base.identity(key) in (None, {}) for key in required):
            return "IDENTITY_MISSING"
    if a.identity("aiConfigDigest") != b.identity("aiConfigDigest"):
        return "IDENTITY_CONFIG"
    if a.identity("judgementVersion") != b.identity("judgementVersion"):
        return "IDENTITY_JUDGEMENT"
    return None


def _field(base: Baseline, key: str):
    """报告优先、sidecar 兜底；两边都没有 → None（= 没记录，与"记录为空"区分）。"""
    if base.report and key in base.report:
        return base.report[key]
    if base.meta and key in base.meta.get("fields", {}):
        return base.meta["fields"][key]
    return None


def _deformation_check(a: Baseline, b: Baseline) -> tuple[bool, list[str]]:
    """② 未变形。引用既有聚合判定，不重写成第二份真源。

    返回 `(是否可比, 说明)`。**墙钟污染用 `wallPercent ≤ 2%`，不用 `gates.wallClean` 布尔** ——
    实测两份可用基线都是 `wallClean=False`（各有一手被墙钟截断），按布尔会把它们全否掉；
    product 档本来就只记录、不判红。
    """
    reasons: list[str] = []
    for base in (a, b):
        failed = _field(base, "failedMeasurementGates")
        if failed is None:
            # 没记录 = 无法证明测量门全过（历史报告就是这种情形）。按"不通"处理，
            # 但要把原因写清，否则看起来像"数据坏了"。
            reasons.append(f"{base.stem}: 缺 failedMeasurementGates（无法证明测量门全过）")
        elif failed:
            reasons.append(f"{base.stem}: 测量门失败 {failed}")
        wall = (base.report or {}).get("wallPercent", 0.0)
        if wall > WALL_PERCENT_POLICY:
            reasons.append(f"{base.stem}: wallPercent={wall:.2f}% 超过 {WALL_PERCENT_POLICY}%")
        gates = (base.report or {}).get("gates") or {}
        if gates.get("wallCleanEnforced") and not gates.get("wallClean"):
            reasons.append(f"{base.stem}: target 档要求 wallClean，实际有一次墙钟截断")
        ratio = (base.report or {}).get("adjudicatedRatio", _field(base, "adjudicatedRatio") or 0.0)
        if ratio > ADJUDICATED_RATIO_POLICY:
            reasons.append(f"{base.stem}: adjudicatedRatio={ratio:.3f} 超过 policy {ADJUDICATED_RATIO_POLICY}")
        fully = _field(base, "blocksFullyAdjudicated") or 0
        if fully > BLOCKS_FULLY_ADJUDICATED_POLICY:
            reasons.append(f"{base.stem}: blocksFullyAdjudicated={fully} 超过 policy {BLOCKS_FULLY_ADJUDICATED_POLICY}")

    # 门集范围：两侧都有记录时必须相同；两侧都缺时不作为否决理由（否则任何历史基线都
    # 永远"不可比"，门禁就成了"永远说不"，比没有门禁更糟），但要在说明里留痕。
    a_eval, b_eval = a.identity("gatesEvaluated"), b.identity("gatesEvaluated")
    if a_eval is None and b_eval is None:
        reasons.append("两侧都缺 gatesEvaluated（门集范围不可核）")
    elif a_eval is None or b_eval is None:
        reasons.append("只有一侧记录了 gatesEvaluated（门集范围不一致）")
    elif set(a_eval) != set(b_eval):
        reasons.append(f"门集范围不同：{sorted(a_eval)} vs {sorted(b_eval)}")

    delta = abs(
        ((a.report or {}).get("adjudicatedRatio", _field(a, "adjudicatedRatio") or 0.0))
        - ((b.report or {}).get("adjudicatedRatio", _field(b, "adjudicatedRatio") or 0.0))
    )
    if delta > ADJUDICATED_DELTA_POLICY:
        reasons.append(f"截断比例差 {delta:.3f} 超过 {ADJUDICATED_DELTA_POLICY}")

    # 只有"否决性"的原因才算不可比；`gatesEvaluated` 双缺属于"不可核"，不否决。
    blocking = [reason for reason in reasons if "不可核" not in reason]
    return (not blocking, reasons)


def compare(stem_a: str, stem_b: str, *, bootstrap: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED) -> dict:
    a, b = Baseline(stem_a), Baseline(stem_b)
    reason = _identity_check(a, b)
    if reason:
        return {"comparable": False, "reason": reason, "conclusion": None}
    ok, deformation_notes = _deformation_check(a, b)
    if not ok:
        return {"comparable": False, "reason": "DEFORMED", "conclusion": None, "notes": deformation_notes}

    result = paired_conclusion(block_scores(a.rows), block_scores(b.rows), bootstrap=bootstrap, seed=seed)
    notes = list(deformation_notes)
    if a.from_backfill or b.from_backfill:
        notes.append(
            "基线元数据含事后回填（source: "
            + ", ".join(f"{base.stem}:{base.meta['source']['commit']}" for base in (a, b) if base.from_backfill)
            + "），非运行时自证"
        )
    return {
        "comparable": True,
        "reason": result["conclusion"],
        "conclusion": result,
        "notes": notes,
        "baselines": {"a": stem_a, "b": stem_b},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="比较两份标定基线（comparable / conclusion 两段）")
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    result = compare(args.a, args.b, bootstrap=args.bootstrap, seed=args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["comparable"]:
        conclusion = result["conclusion"]
        # 交付口径：只写得分成差与区间，**不写"更强/更弱"**；分辨力必须印出来。
        print(
            f"\n得分差 {conclusion['pointEstimate']}（区间 {conclusion['ci95']}，"
            f"{conclusion['blocksPaired']} 块配对，分辨力 {conclusion['resolution']}）"
        )
        if conclusion["conclusion"] == "INSUFFICIENT":
            print("可比，但该样本量无法判定强度变化 —— 动作是加样本，不是改测量。")
        elif conclusion["conclusion"] == "IDENTICAL":
            print("两份完全相同 —— 这个比较本身没有意义。")
    for note in result.get("notes", []):
        print(f"\n注意：{note}")
    return 0 if result["comparable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
