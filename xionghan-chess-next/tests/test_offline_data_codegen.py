from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_offline_data.py"
OFFLINE = ROOT / "android" / "Resources" / "assets" / "offline" / "offline.js"


def test_offline_data_is_in_sync_with_python_profiles() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_offline_probe_anchors_are_preserved() -> None:
    source = OFFLINE.read_text(encoding="utf-8")
    assert "const TYPES=" in source
    assert "const canvas=" in source
    assert source.index("const TYPES=") < source.index("const canvas=")
    assert "const PROFILE_DATA=" in source
