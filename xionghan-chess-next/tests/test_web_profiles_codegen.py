"""网页规则档案 codegen 门禁：`profiles.js` 必须与 Python `core/profiles.py` 同源。

范式照抄 `tests/test_offline_data_codegen.py:12-20`：subprocess 跑 `--check`，
漂移即 exit 1。8 条断言（键集相等 + 逐值相等，而不是「键数都是 32」）在脚本里。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_web_profiles.py"
TARGET = ROOT / "webapp" / "js" / "core" / "profiles.js"
MANIFEST = ROOT / "webapp" / "js" / "core" / "profiles.manifest.json"


def _norm_sha(path: Path) -> str:
    # 与 scripts/gen_web_profiles.py::sha256 同一口径：归一化行尾（CRLF→LF）后再哈希。
    import hashlib

    return hashlib.sha256(
        path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()


def test_web_profiles_is_in_sync_with_python_profiles() -> None:
    """产物逐字节 == 生成结果；DEFAULT_OPTIONS/三个 OPTIONS/别名/依赖表/名称表逐值相等。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_generated_profiles_exposes_the_v3_switches() -> None:
    """护栏不能空跑：JS DEFAULT_OPTIONS 必须真的含 p3l / pawn_charge。

    `mergeOptions` 的 `key in result` 会静默丢弃未知键；若档案没重建，
    fixtures 里的 `p3l: true` 会被丢弃，removals 门禁必然空跑。
    """
    import json
    import re

    source = TARGET.read_text(encoding="utf-8")
    match = re.search(r"^export const DEFAULT_OPTIONS = (.+);$", source, re.MULTILINE)
    assert match, "profiles.js 缺 DEFAULT_OPTIONS"
    default = json.loads(match.group(1))
    assert "pawn_three_line_capture" in default
    assert "pawn_charge" in default
    assert "pawn_full_movement_at_base" not in default, "1.9.x 死开关不该回到规范键集"


def test_profile_manifest_matches_the_live_artifacts() -> None:
    """manifest 的 hash 必须等于当前文件（毫秒级，防止「忘了重生成」）。"""
    import hashlib
    import json

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["ruleVersion"] == 3
    assert manifest["profilesHash"] == _norm_sha(TARGET)
    assert manifest["rulesHash"] == _norm_sha(ROOT / "webapp" / "js" / "core" / "rules.js")


@pytest.mark.slow
def test_full_web_profiles_regeneration_is_byte_identical() -> None:
    """完整重生成（slow job）：先 --write 再 --check，产物不得漂移。"""
    write = subprocess.run(
        [sys.executable, str(SCRIPT), "--write"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert write.returncode == 0, write.stderr
    check = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert check.returncode == 0, check.stderr
