from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wasm_decision_is_recorded() -> None:
    decision = ROOT / "docs" / "WASM_DECISION.md"
    assert decision.exists(), "WASM 结论必须落档，不能只存在于对话里"
    text = decision.read_text(encoding="utf-8")
    assert "不采纳" in text
    assert "重新评估的触发条件" in text


def test_no_pyodide_dependency_is_introduced() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert "pyodide" not in package.get("dependencies", {})
    for requirement in (ROOT / "requirements").glob("*.txt"):
        assert "pyodide" not in requirement.read_text(encoding="utf-8").lower()
