"""fixtures 新鲜度门禁：毫秒级读 manifest，防「忘了重生成」。

完整「重生成 + 逐字节比对」55s+ 放 slow（本文件末尾的 slow 用例），
不阻塞 PR；本文件的其余断言只读 manifest/头部，主 pytest 里跑。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_rule_fixtures.py"
FIXTURE = ROOT / "webapp" / "tests" / "fixtures" / "rules.json"
FIXTURE_EDGEONE = ROOT / "webapp" / ".edgeone" / "assets" / "tests" / "fixtures" / "rules.json"
PROFILES_JS = ROOT / "webapp" / "js" / "core" / "profiles.js"
RULES_JS = ROOT / "webapp" / "js" / "core" / "rules.js"
PROFILES_MANIFEST = ROOT / "webapp" / "js" / "core" / "profiles.manifest.json"

from xionghan_chess.core.profiles import RULE_VERSION, RuleOptions  # noqa: E402


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_manifest_matches_live_core() -> None:
    """ruleVersion / profilesHash / rulesHash / optionsKeys 必须与当前源码一致。"""
    data = _fixture()
    assert data["ruleVersion"] == RULE_VERSION == 3
    assert data["profilesHash"] == hashlib.sha256(PROFILES_JS.read_bytes()).hexdigest()
    assert data["rulesHash"] == hashlib.sha256(RULES_JS.read_bytes()).hexdigest()
    assert data["optionsKeys"] == sorted(asdict(RuleOptions()))
    assert data["caseCount"] == len(data["cases"])
    assert data["transitionCount"] == len(data["transitions"])


def test_source_digest_matches_disk_in_fixed_order() -> None:
    """T01'/S1–S6：sourceDigest 按固定顺序拼接 5 个文件 + str(RULE_VERSION)。

    bundle（S3/S4）必须先于 fixtures（S5），否则这里会与磁盘重算值分叉。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("grf_fresh", ROOT / "scripts" / "gen_rule_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = _fixture()
    assert data["sourceDigest"] == module.source_digest(), "sourceDigest 与磁盘重算值不等（S3/S4 没跑？）"
    assert data["sourceDigestFiles"] == module.source_digest_parts()
    assert len(data["sourceDigestFiles"]) == 5


def test_every_case_carries_three_line_moves() -> None:
    """T01'：每 case 带 threeLineMoves；至少 1 个 case 非空（防护栏空跑）。"""
    data = _fixture()
    for case in data["cases"]:
        assert "threeLineMoves" in case, f"{case['id']} 缺 threeLineMoves"
        assert isinstance(case["threeLineMoves"], list)
        assert set(case["threeLineMoves"]) <= set(case["legal"])
    non_empty = [c for c in data["cases"] if c["threeLineMoves"]]
    assert len(non_empty) >= 1, "threeLineCases=0 → 护栏空跑"


def test_exact3_variant_pair_is_present() -> None:
    """T01'/M31：两条确定性开关变体（同一局面只翻 p3l）必须存在且期望逐字正确。"""
    data = _fixture()
    by_id = {c["id"]: c for c in data["cases"]}
    on = by_id.get("opt:tl:exact3")
    off = by_id.get("opt:tl:exact3:off")
    assert on is not None, "缺 opt:tl:exact3"
    assert off is not None, "缺 opt:tl:exact3:off"
    assert on["options"]["pawn_three_line_capture"] is True
    assert off["options"]["pawn_three_line_capture"] is False
    # 同一局面 = 去 id 后逐子相同（id 按 case_id 命名，本就跨 case 不同，且不参与判定）
    shape = lambda c: sorted(  # noqa: E731
        (p["type"], p["color"], p["row"], p["col"]) for p in c["state"]["pieces"]
    )
    assert shape(on) == shape(off), "两条变体必须是同一局面（忽略 id）"
    assert on["state"]["turn"] == off["state"]["turn"]
    assert on["state"]["captured"] == off["state"]["captured"]
    assert on["removals"][on["probe"]] == [["advisor", "black", 6, 5]]
    assert off["removals"][off["probe"]] == []
    assert on["threeLineMoves"] == [on["probe"]]
    assert off["threeLineMoves"] == []


def test_every_case_has_a_removals_map_keyed_by_legal() -> None:
    """removals 键缺失 / 键集合 != set(legal) 是阻断条件（T01）。"""
    data = _fixture()
    for case in data["cases"]:
        assert "removals" in case, f"{case['id']} 缺 removals"
        assert set(case["removals"]) == set(case["legal"]), (
            f"{case['id']} removals 键集合 != set(legal)"
        )
        for key, value in case["removals"].items():
            assert isinstance(value, list), f"{case['id']}@{key} 应为数组（空吃子用 []，不是 null）"
            for quad in value:
                assert len(quad) == 4 and isinstance(quad[2], int) and isinstance(quad[3], int), (
                    f"{case['id']}@{key} 四元组形状错误: {quad}"
                )


def test_case_options_cover_the_v3_switches() -> None:
    """case 的 options 必须含 pawn_three_line_capture/pawn_charge（不是空跑的旧 32 键）。"""
    data = _fixture()
    canonical = set(asdict(RuleOptions()))
    for case in data["cases"]:
        assert set(case["options"]) == canonical, f"{case['id']} options 键集不是 v3 规范集"
        assert "pawn_three_line_capture" in case["options"]
        assert "pawn_charge" in case["options"]


def test_three_line_deterministic_cases_are_present_with_qa_expectations() -> None:
    """13 条 rem:tl:* 定向局面必须在 fixtures 里，且期望值逐字是 QA 复算值。

    特别钉住 W-06a 口径：`rem:tl:disp-5`（5 格行军）期望必须是 `[]`；
    写成 `[[advisor,black,5,4]]` 说明有人把 R1 误撤。
    """
    data = _fixture()
    tl = {case["id"]: case for case in data["cases"] if case["id"].startswith("rem:tl:")}
    assert len(tl) == 13, f"rem:tl 定向 case 数 {len(tl)} != 13"
    expected = {
        "rem:tl:axis-h": [["advisor", "black", 6, 5]],
        "rem:tl:axis-v": [["advisor", "black", 4, 3]],
        "rem:tl:axis-d1": [["advisor", "black", 8, 5]],
        "rem:tl:axis-d2": [["advisor", "black", 8, 1]],
        "rem:tl:multiline": [["advisor", "black", 5, 4]],
        "rem:tl:outer-near": [],
        "rem:tl:outer-far": [],
        "rem:tl:outer-both": [],
        "rem:tl:disp-2": [],
        "rem:tl:disp-5": [],  # W-06a：R1 已落地，禁止沿用 {(5,4)}
        "rem:tl:king-in-window": [],
        "rem:tl:king-replaced-rook": [["rook", "black", 2, 4]],
        "rem:tl:far-line": [],
    }
    for case_id, want in expected.items():
        case = tl[case_id]
        assert case["removals"][case["probe"]] == want, (
            f"{case_id}@{case['probe']}: 期望 {want}，实际 {case['removals'][case['probe']]}"
        )
    # A≠B 走法关键样本：开关 on/off 时 legal/check 相同，唯 removals 不同
    on = tl["rem:tl:axis-h"]
    assert on["removals"][on["probe"]], "axis-h 必须是非空（护栏能验出「只改移除集合」）"
    assert tl["rem:tl:king-in-window"]["removals"][tl["rem:tl:king-in-window"]["probe"]] == []
    assert tl["rem:tl:king-replaced-rook"]["removals"][tl["rem:tl:king-replaced-rook"]["probe"]]


def test_two_fixture_copies_are_byte_identical() -> None:
    """双份输出逐字节相同（webapp/tests 与 .edgeone/assets/tests）。"""
    assert FIXTURE_EDGEONE.exists(), "EdgeOne 部署源缺 fixtures 副本"
    assert FIXTURE.read_bytes() == FIXTURE_EDGEONE.read_bytes()


def test_manifest_chain_precedes_fixtures() -> None:
    """Step1 manifest 的 hash/digest 必须与 fixtures 头部一致（顺序链）。"""
    data = _fixture()
    manifest = json.loads(PROFILES_MANIFEST.read_text(encoding="utf-8"))
    assert data["profilesHash"] == manifest["profilesHash"]
    assert data["rulesHash"] == manifest["rulesHash"]
    assert data["ruleVersion"] == manifest["ruleVersion"]
    assert data["optionsDigest"] == manifest["optionsDigest"]


@pytest.mark.slow
def test_full_fixture_regeneration_is_byte_identical() -> None:
    """完整重生成 + 逐字节比对（55s+，slow job，不阻塞 PR）。"""
    write = subprocess.run(
        [sys.executable, str(SCRIPT), "--write"],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert write.returncode == 0, write.stderr or write.stdout
    check = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert check.returncode == 0, check.stderr or check.stdout
