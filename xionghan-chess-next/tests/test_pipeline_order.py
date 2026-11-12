"""manifest 链完整性：Step1 → Step2 → Step3 → Step4 的顺序要能 fail，不能静默空跑。

链条：
  profiles.manifest.json  (Step1，含 ruleVersion/optionsDigest/profilesHash/rulesHash)
      ↓ 前置断言
  fixtures/rules.json     (Step2，头部 manifest 与 Step1 逐项一致，且带 removals)
      ↓ 同步
  5 类产物                (Step3，HTML 内嵌块 / online/core / .edgeone 与唯一源一致)
      ↓ 护栏
  verify-rules.mjs        (Step4，stale-fixtures + removals 逐着法比对)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES_JS = ROOT / "webapp" / "js" / "core" / "profiles.js"
RULES_JS = ROOT / "webapp" / "js" / "core" / "rules.js"
MANIFEST = ROOT / "webapp" / "js" / "core" / "profiles.manifest.json"
FIXTURE = ROOT / "webapp" / "tests" / "fixtures" / "rules.json"
VERIFIER = ROOT / "webapp" / "tests" / "verify-rules.mjs"

from xionghan_chess.core.profiles import RULE_VERSION, RuleOptions  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_step1_manifest_is_self_consistent() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["generatedBy"] == "scripts/gen_web_profiles.py"
    assert m["ruleVersion"] == RULE_VERSION == 3
    assert m["profilesHash"] == _sha(PROFILES_JS)
    assert m["rulesHash"] == _sha(RULES_JS)
    canonical = hashlib.sha256(
        json.dumps(sorted(asdict(RuleOptions())), separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert m["optionsDigest"] == canonical


def test_step2_fixture_header_mirrors_step1_manifest() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    f = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for key in ("ruleVersion", "optionsDigest", "profilesHash", "rulesHash"):
        assert f[key] == m[key], f"fixtures manifest.{key} 与 Step1 分叉"
    assert f["optionsKeys"] == sorted(asdict(RuleOptions()))
    assert f["generatedBy"] == "scripts/gen_rule_fixtures.py"


def test_step2_source_digest_closes_the_s3_s4_order() -> None:
    """T18：fixtures 的 sourceDigest 必须等于按 S1–S6 顺序从磁盘重算的值。

    若 bundle（S3/S4）跑在 fixtures（S5）之后，online/public/index.html 的字节
    不在摘要里 → 本断言红，且 verify-rules.mjs 会 fail('build-order')。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("grf_order", ROOT / "scripts" / "gen_rule_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    f = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert f["sourceDigest"] == module.source_digest()
    assert len(f["sourceDigestFiles"]) == 5
    assert "online/public/index.html" in f["sourceDigestFiles"]


def test_t14_t15_verifiers_exist_and_are_wired() -> None:
    """T14/T15：两个新增 verifier 存在，且 CI test job 真的会跑它们。"""
    t14 = ROOT / "webapp" / "tests" / "verify-position-key.mjs"
    t15 = ROOT / "webapp" / "tests" / "verify-bundle.mjs"
    vm_lib = ROOT / "webapp" / "tests" / "lib" / "bundle-vm.mjs"
    for path in (t14, t15, vm_lib):
        assert path.exists(), f"缺 {path}"
    assert "Q-PK-01" in t14.read_text(encoding="utf-8")
    assert "bundle-stale" in t15.read_text(encoding="utf-8")
    ci = (ROOT.parent / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "node webapp/tests/verify-position-key.mjs" in ci
    assert "node webapp/tests/verify-bundle.mjs" in ci
    assert "S1" in ci and "S6" in ci, "CI slow job 缺 S1–S6 顺序日志"


def test_step3_sentinels_close_the_chain() -> None:
    """Step3 产物里必须带 Step1/Step2 才有的新哨兵，防止线上仍跑旧引擎。"""
    edgeone_rules = ROOT / "webapp" / ".edgeone" / "assets" / "js" / "core" / "rules.js"
    online_rules = ROOT / "online" / "core" / "rules.js"
    for path in (edgeone_rules, online_rules):
        raw = path.read_text(encoding="utf-8")
        for token in ("threeLineCaptures", "p3l", "||opt:", "||pool:", "rs${RULE_VERSION}-"):
            assert token in raw, f"{path} 缺哨兵 {token}（Step3 没同步？）"
        assert "pawn_full_movement_at_base" not in raw


def test_step4_verifier_is_wired_to_removals_and_selftest() -> None:
    """verify-rules.mjs 必须真的有 removals 比对与 --selftest，不能是空壳。"""
    raw = VERIFIER.read_text(encoding="utf-8")
    assert "boardRemovals" in raw
    assert "stale-fixtures" in raw
    assert "--selftest" in raw or "SELFTEST" in raw
    assert "removalsCompared" in raw, "没有比对条数统计，无法判空绿"
    assert "removals-selftest" in raw
    # T17：防空跑三断言 + 顺序错必 fail 样本 + build-order
    for token in ("fixtures-empty", "removals-empty", "variant-missing",
                  "build-order", "sourceDigest", "顺序样本①", "顺序样本②", "顺序样本③"):
        assert token in raw, f"verify-rules.mjs 缺 {token}"


def test_t19_r3_display_layer_is_explicitly_not_applicable() -> None:
    """T19 = R3 展示层「不适用（不执行、不判定）」（严过关 M28）。

    R3 已在 5f25642 落地，且 webapp/online 结构上没有该渲染路径。
    这是**显式排除**，不是缺口；本轮不补、不执行、不判定。
    """
    # 断言本轮没有把 R3 相关的展示/文案项带进改动范围：
    # locales/*:420 的 pawn_long、app.js:84/:87 图谱描述、GAME_MODES.md:82 脚注
    app_js = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
    # 图谱描述仍是原文案（本轮不动）
    assert "到底线四向移动" in app_js, "展示文案被误改（T19 要求不动）"
    rules_js = (ROOT / "webapp" / "js" / "core" / "rules.js").read_text(encoding="utf-8")
    assert "pawn_full_movement_at_base" not in rules_js, "1.9.x 死开关不该回到规则内核"


def test_verifier_selftest_reports_nonzero_comparisons() -> None:
    """实跑 --selftest：必须报 N/N 通过，且 removals 实际比对条数 > 0（防假绿）。"""
    result = subprocess.run(
        ["node", str(VERIFIER), "--selftest"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert "[removals-selftest]" in out
    assert "条数: 0" not in out, "removals 实际比对条数为 0 —— 空绿，门禁无效"


def test_rule_version_is_not_bumped() -> None:
    """RULE_VERSION 保持 3、POSITION_KEY_VERSION 保持 4（本轮不 bump）。"""
    from xionghan_chess.core.rules import POSITION_KEY_VERSION

    assert RULE_VERSION == 3
    assert POSITION_KEY_VERSION == 4
