"""移除集合指纹门禁：语义一动，基线必变。

## 为什么需要它

`RULE_VERSION` 靠人记得 `+1`。三连吃子那一轮就是活例子：三项收紧（多格位移不结算 /
恰好三子 / 不吃王）**每一条都在改移除集合**，而既有 88 条跨引擎护栏**一条都没红** ——
因为 `perft` 数的是**着法条数**，`verify-rules.mjs` 也只比 `legal` + `check`：
"这一着吃掉哪些子"完全不在任何护栏里。网页版缺整条兵三连能潜伏到今天，正是这个盲区。

这里换一种钉法：把「合法着法 / 谁能吃到谁 / 每一步吃掉哪些子」三类摘要打进基线，
语义一变必红，且红灯直接给出处置步骤。

## 三条硬口径

1. **不进 `slow`**：进了 `-m "not slow"` 就等于不存在（提交不再即红）。
2. **不 assert 墙钟**：共享 CI 上必然 flaky，而 flaky 的门禁最后一定被人挪进 slow。
   改用与机器无关的计算量代理 —— `sum(perft1)`（基线里本来就有，天然是"这台机器要处理
   多少着法"的度量）。`PERFT_BUDGET` 首跑实测 2964（2026-11-12），取 2 倍余量；**只许下调**。
3. **只跑 Python**：指纹回答"比上一版变了吗"（绝对基线），跨端回答"两边一致吗"（parity）。
   混在一个测试里，红了不知道该修哪边。跨端交给 `test_cross_engine.py`。

## 红灯要指名下一步动作

三条失败路径（版本 / 缺例 / 摘要漂移）各自给出**该做什么**，而不是只说"不匹配"。
但**没有测试去 grep 这段文案** —— 那会把文案锁死成 API，改一句话就得改测试。
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_removal_fingerprint.py"
BASELINE = ROOT / "tests" / "fixtures" / "removal_fingerprint.json"

# 计算量代理上限（不是墙钟）。首跑实测 2964 着法 / 78 例，取 2 倍余量。
# 有人塞 perft(2) 进来会乘上约 30 倍，立刻红。
PERFT_BUDGET = 6000
MAX_CASES = 200

REGEN = "python scripts/gen_removal_fingerprint.py --write"


def _module():
    spec = importlib.util.spec_from_file_location("removal_fingerprint_for_tests", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_fingerprint_is_cheap_enough_to_stay_in_the_main_gate() -> None:
    """算不完的指纹门禁会被赶进 `-m slow`，那就等于没有 —— 用算量而不是墙钟来守。"""
    started = time.perf_counter()
    payload = _module().fingerprint()
    elapsed = time.perf_counter() - started

    cases = payload["cases"]
    moves = sum(case["perft1"] for case in cases.values())
    # 墙钟只打印，供人看趋势；不断言（共享 CI 上必然 flaky）。
    print(f"[removal-fingerprint] {len(cases)} cases / {moves} moves / {elapsed:.2f}s")

    assert len(cases) <= MAX_CASES, f"指纹用例 {len(cases)} 例超过 {MAX_CASES} 上限"
    assert moves <= PERFT_BUDGET, (
        f"指纹要处理 {moves} 条着法，超过 {PERFT_BUDGET} 预算 —— "
        "覆盖加太多或误加了 perft(2)，先减范围再加回来"
    )
    assert cases, "指纹为空集 —— 门禁什么都不钉"


def test_baseline_actually_covers_the_capture_kinds() -> None:
    """基线必须真的咬到三连吃子，而不只是直接吃子。

    这条不是洁癖：第一版生成器在整盘均匀撒子，200 例的「可吃格」摘要**全是空串** ——
    门禁照样绿，但三连语义怎么改它都不动，等于没钉。覆盖度必须显式断言，
    否则"绿"只证明了两边都算出了同一个零。
    """
    cases = _baseline()["cases"]
    assert any("three_line" in case["capturable"] for case in cases.values()), (
        "基线里没有任何 three_line 记录 —— 三连吃子的语义没被钉住，"
        "请检查 tests/_removal_cases.py 的构造（线内补位子不能用兵，会把线带歪）"
    )
    assert any("direct" in case["capturable"] for case in cases.values()), "基线里没有 direct 记录"


def test_removal_fingerprint_matches_the_baseline() -> None:
    """版本 → 缺例 → 摘要漂移，三条路径分别报，各自指名下一步动作。"""
    expected = _baseline()
    actual = _module().fingerprint()

    assert actual["ruleVersion"] == expected["ruleVersion"], (
        f"[version] 规则语义版本不一致：基线 ruleVersion={expected['ruleVersion']}，"
        f"当前 RULE_VERSION={actual['ruleVersion']}。\n"
        "  → 已 bump 版本：重生成基线并提交（基线里的 ruleVersion 要跟着变）。\n"
        "  → 未 bump 版本：说明本次改动动了移除语义，必须 bump RULE_VERSION "
        "并同步 offline.js 的 rs 字面量。"
    )
    assert actual["generatorVersion"] == expected["generatorVersion"], (
        f"[generator] 构造规则版本不一致：基线 {expected['generatorVersion']}，"
        f"当前 {actual['generatorVersion']}。\n"
        "  → 你改了 tests/_removal_cases.py 的局面构造（加族 / 改坐标），"
        f"请在该模块注释里说明改了什么并重生成基线：{REGEN}"
    )

    missing = sorted(set(actual["cases"]) - set(expected["cases"]))
    extra = sorted(set(expected["cases"]) - set(actual["cases"]))
    assert not missing and not extra, (
        f"[missing] 基线缺 {len(missing)} 例、多 {len(extra)} 例："
        f"{', '.join(missing[:6]) or '-'} / {', '.join(extra[:6]) or '-'}。\n"
        "  → 你改了覆盖范围（加族 / 加维度）。重生成基线，"
        "并在 GENERATOR_VERSION 注释里写明新增了哪一维。"
    )

    drifted = []
    for case_id, case in actual["cases"].items():
        was = expected["cases"][case_id]
        changed = [key for key in ("perft1", "capturable", "removals") if was[key] != case[key]]
        if changed:
            details = "; ".join(f"{key}: was={was[key]!r} now={case[key]!r}" for key in changed)
            drifted.append(f"{case_id} → {details}")
    assert not drifted, (
        f"[delta] {len(drifted)}/{len(actual['cases'])} 例的移除集合变了：\n  "
        + "\n  ".join(drifted[:8])
        + "\n  → 若这是有意的规则变更：bump RULE_VERSION + 同步 offline.js 的 rs + "
        f"重生成基线 + 写发布说明，四件缺一不可（{REGEN}）。\n"
        "  → 若不是：rules.py / offline.js 有回归，不要改基线。"
    )
