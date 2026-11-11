"""移除集合指纹门禁：语义一动，基线必变。

## 为什么需要它

`RULE_VERSION` 靠人记得 `+1`。三连吃子那轮改动就是活例子：三项收紧（多格位移不结算 /
恰好三子 / 不吃王）**每一条都在改移除集合**，却没有任何既有测试会因此变红 ——
因为既有测试只断言"某些局面下的具体结果"，覆盖不到的每一种组合都是沉默漂移。

这里换一种钉法：把「合法着法 / 谁能吃到谁 / 每一步吃掉哪些子」三类摘要打进基线
（`tests/fixtures/removal_fingerprint.json`，由 `scripts/gen_removal_fingerprint.py`
用固定种子确定性生成）。**语义一变，摘要必变**，门禁红，文案直接给出处置步骤。

它是**唯一**会因为"语义变了但没人声明"而红的地方，所以：
- 不许标 `slow`（它会和 `-m "not slow"` 的主门禁一起跑，否则等于不存在）；
- 必须快（基线 200 例 ≈ 0.5s，硬上限 2.0s），慢到被人想跳过就失去意义。
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_removal_fingerprint.py"
BASELINE = ROOT / "tests" / "fixtures" / "removal_fingerprint.json"
OFFLINE = ROOT / "android" / "Resources" / "assets" / "offline" / "offline.js"
MAX_SECONDS = 2.0
MAX_CASES = 200
DIGESTS = ("perft1", "legalDigest", "capturableDigest", "capturedByMoveDigest")

RED_LIGHT = (
    "移除集合指纹变了 —— 有走法语义被改动。处置顺序：\n"
    "  1) 确认这是**有意**的规则改动；不是 → 修代码，别动基线。\n"
    "  2) 是 → 把 core/profiles.py 的 RULE_VERSION +1"
    "（同时改 offline.js::positionKey 里的 'rs{N}-' 字面量，两处必须一起改）；\n"
    "  3) 然后重生成基线：python scripts/gen_removal_fingerprint.py\n"
    "  4) 把「RULE_VERSION 升位 + 新基线」放进**同一个 commit**，别拆开。"
)


def _module():
    spec = importlib.util.spec_from_file_location("removal_fingerprint_for_tests", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_baseline_is_regenerable_within_the_time_budget() -> None:
    """指纹必须能在 2.0s 内算完 —— 否则门禁会被 `-m slow` 赶出去，等于没有。"""
    module = _module()
    started = time.perf_counter()
    payload = module.fingerprint()
    elapsed = time.perf_counter() - started

    assert elapsed <= MAX_SECONDS, f"指纹生成耗时 {elapsed:.2f}s 超过 {MAX_SECONDS}s 上限，先减案例数"
    assert payload["caseCount"] <= MAX_CASES, f"案例数 {payload['caseCount']} 超过 {MAX_CASES}"
    assert payload["cases"], "指纹为空集 —— 门禁什么都不钉"


def test_baseline_actually_covers_the_capture_kinds() -> None:
    """基线必须真的咬到三连吃子与直接吃子。

    这条不是洁癖：第一版生成器在整盘撒子，200 例里"可吃格"摘要**全是空串哈希** ——
    门禁照样绿，但三连吃子的语义怎么改它都不会动，等于没钉。覆盖度必须显式断言，
    否则"绿"只证明了两边都算出了同一个零。
    """
    kinds: set[str] = set()
    for case in _baseline()["cases"]:
        kinds.update(case["kinds"])
    assert {"direct", "three_line"} <= kinds, (
        f"基线只覆盖了 {sorted(kinds) or '空'} —— 三连吃子/直接吃子的语义都没被钉住，"
        "请调 scripts/gen_removal_fingerprint.py 的局面生成（聚簇布局/兵的比例）"
    )


def test_removal_fingerprint_matches_the_baseline() -> None:
    """语义未变时逐例一致；变了就报出**是哪几例、哪一类摘要**变了。"""
    expected = _baseline()
    actual = _module().fingerprint()

    assert actual["ruleVersion"] == expected["ruleVersion"], RED_LIGHT
    assert actual["seed"] == expected["seed"], f"生成器种子变了（{expected['seed']} → {actual['seed']}），基线必须重生成"

    if actual == expected:
        return

    by_id = {case["id"]: case for case in expected["cases"]}
    drifted: list[str] = []
    for case in actual["cases"]:
        was = by_id.get(case["id"])
        if was is None:
            drifted.append(f"{case['id']}: 基线里没有这一例（生成器变了？）")
            continue
        changed = [key for key in DIGESTS if was.get(key) != case.get(key)]
        if changed:
            detail = ", ".join(f"{key} {was.get(key)}→{case.get(key)}" for key in changed)
            drifted.append(f"{case['id']}: {detail}")
    missing = sorted(set(by_id) - {case["id"] for case in actual["cases"]})
    if missing:
        drifted.append(f"基线里多出 {len(missing)} 例（生成器变了？如 {missing[0]}）")

    assert not drifted, (
        f"{len(drifted)}/{len(actual['cases'])} 例漂移：\n  " + "\n  ".join(drifted[:12]) + f"\n\n{RED_LIGHT}"
    )


@pytest.mark.parametrize("key", ["pawn_three_line_capture", "pawn_charge"])
def test_toggle_flip_changes_the_fingerprint(key: str) -> None:
    """开关必须在指纹里留痕 —— 否则"改了开关默认值"同样能静默漂移。

    做法：把**整批**用例的该开关统一翻面后重算，摘要必须变（单看某一例不行：
    随机摆的局面里，很多局面本来就与这个开关无关，翻了也不该变）。这条同时证明了
    `options` 真的进了 `RulesEngine` —— 历史上踩过"payload 丢 options，
    比对的全是档案默认值"这种假绿。
    """
    module = _module()
    baseline = _baseline()
    assert {case["options"][key] for case in baseline["cases"]} == {True, False}, (
        f"基线里 {key} 只有一种取值，翻面测试没有意义"
    )

    # 短路：只要**有任何一例**因翻面而变，就证明开关进了算法。
    # 不预先挑某一例 —— 随机局面里很多例本来就与这个开关无关，翻了也不该变。
    for case in module.build_cases():
        flipped = {**case, "options": {**case["options"], key: not case["options"][key]}}
        if module.case_digests(case) != module.case_digests(flipped):
            return
    pytest.fail(f"翻转 {key} 后全部 200 例摘要都没变 —— 该开关没有进算法，或没有进指纹")


def test_offline_position_key_literal_matches_rule_version() -> None:
    """`offline.js` 的 `'rs{N}-'` 必须等于 `RULE_VERSION`（JS 与 Python 无法共享常量）。

    这条是升位时最容易漏的一处：Python 改了、JS 没改，两端算出的重复局面键不同，
    同一盘棋在安卓与桌面上的"三次重复"判得不一样 —— 且不会有任何测试喊。
    """
    from xionghan_chess.core.profiles import RULE_VERSION

    source = OFFLINE.read_text(encoding="utf-8")
    key_literal = f"'rs{RULE_VERSION}-'"
    assert key_literal in source, (
        f"offline.js::positionKey 里找不到 {key_literal}；"
        f"当前 RULE_VERSION={RULE_VERSION}，JS 侧字面量没跟上（改一处必须改另一处）"
    )
    # 旧的版本前缀不许残留：只留注释里的历史说明也不行，容易看错。
    for stale in range(1, RULE_VERSION):
        assert f"'rs{stale}-'" not in source, f"offline.js 里还留着旧字面量 'rs{stale}-'"
