"""bundle 产物门禁：5 类产物同步 + 内嵌哨兵计数 + --check。

`build_webapp_bundle.py --check` 重算 html 后逐字节比对两处 HTML、
校验 online/core/*.js、内嵌 `__mods["js/core/rules.js"]` / profiles.js 文本、
EdgeOne 部署源，并做哨兵计数。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_webapp_bundle.py"
DIST_HTML = ROOT / "webapp" / "dist" / "index.html"
ONLINE_HTML = ROOT / "online" / "public" / "index.html"
EDGEONE = ROOT / "webapp" / ".edgeone" / "assets"


def test_bundle_check_passes() -> None:
    """重算 + 逐字节比对，任一产物漂移即 exit 1（T09）。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_embedded_sentinels_are_present_in_both_html() -> None:
    """T15/Q-ART-01：两份引擎快照都要带新标记，阈值 **≥2**（严过关 M26）。

    `js/core/rules.js` 在 HTML 里真正的 `__mods[...] = (function` 引擎快照只有 2 份
    （1 份主 inline script、1 份 `__WORKER_SRC` 转义串）；只更新一份时 ≥1 会假绿。
    """
    for path in (DIST_HTML, ONLINE_HTML):
        raw = path.read_text(encoding="utf-8")
        assignment = '__mods["js/core/rules.js"] = (function () {'
        # 主 inline 明文 1 份 + __WORKER_SRC 转义串解码后 1 份 = 2
        import json
        import re

        worker_match = re.search(r'var __WORKER_SRC = ("(?:[^"\\]|\\.)*");', raw)
        worker_count = 0
        if worker_match:
            worker_count = json.loads(worker_match.group(1)).count(assignment)
        assert raw.count(assignment) + worker_count == 2, f"{path.name} 引擎快照数 != 2"
        counts = {
            "threeLineCaptures": raw.count("threeLineCaptures"),
            "pawn_three_line_capture": raw.count("pawn_three_line_capture"),
            "p3l": raw.count("p3l"),
            # 主理人裁决：不写死 `rs3-` 字面量（§2.2(c) 防复发优先）。
            # 文本哨兵认 `rs${RULE_VERSION}-`（≥2）；运行时串由 T14 的 Q-PK 全等覆盖。
            # 逐字 `rs3-` 若残留一律来自注释，不能当断言留着（永远为 0 的假断言）。
            "rs${RULE_VERSION}-": raw.count("rs${RULE_VERSION}-"),
            "||opt:": raw.count("||opt:"),
            "||pool:": raw.count("||pool:"),
        }
        for token, count in counts.items():
            assert count >= 2, f"{path.name} 内嵌哨兵 {token} 计数={count} < 2"
        # 规则内核内嵌块里不得残留 1.9.x 死开关（全文 UI 文案不计）
        rules_block_start = raw.find(assignment)
        assert rules_block_start >= 0, f"{path.name} 缺内嵌 rules.js 模块"
        next_module = raw.find("__mods[", rules_block_start + 10)
        rules_block = raw[rules_block_start:next_module if next_module > 0 else None]
        assert "pawn_full_movement_at_base" not in rules_block


def test_edgeone_deployment_source_is_synced() -> None:
    """第五类产物：EdgeOne 引用式加载活体 js/core/*.js，必须与唯一源逐字一致。"""
    pairs = [
        (EDGEONE / "js" / "core" / "profiles.js", ROOT / "webapp" / "js" / "core" / "profiles.js"),
        (EDGEONE / "js" / "core" / "rules.js", ROOT / "webapp" / "js" / "core" / "rules.js"),
        (EDGEONE / "js" / "core" / "movegen.js", ROOT / "webapp" / "js" / "core" / "movegen.js"),
        (EDGEONE / "tests" / "fixtures" / "rules.json", ROOT / "webapp" / "tests" / "fixtures" / "rules.json"),
    ]
    for target, source in pairs:
        assert target.exists(), f"EdgeOne 缺 {target}"
        assert target.read_text(encoding="utf-8").replace("\r\n", "\n") == source.read_text(
            encoding="utf-8"
        ).replace("\r\n", "\n"), f"{target} 与唯一源漂移"


def test_online_core_matches_webapp_core() -> None:
    """online/core/*.js 归一化行尾后与 webapp/js/core/*.js 逐字相同。"""
    for item in (ROOT / "webapp" / "js" / "core").glob("*.js"):
        dst = ROOT / "online" / "core" / item.name
        assert dst.exists(), f"online/core 缺 {item.name}"
        assert dst.read_text(encoding="utf-8").replace("\r\n", "\n") == item.read_text(
            encoding="utf-8"
        ).replace("\r\n", "\n"), f"online/core/{item.name} 漂移"


@pytest.mark.slow
def test_full_bundle_regeneration_is_byte_identical() -> None:
    """完整重生成 + --check（slow job）。"""
    write = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )
    assert write.returncode == 0, write.stderr
    check = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert check.returncode == 0, check.stderr
