"""文档与版本号的"单一来源"守卫。

两条都来自踩过的坑：
1. **版本号两处真源**：`pyproject` 写 1.7.0、发布 1.7.5，谁也没发现；
2. **改错副本**：`docs/PIECE_RULES.md` 与 `resources/docs/PIECE_RULES.md` 逐字节相同，
   但只有后者进包 —— 改 docs/ 那份对用户完全无效。
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "src" / "xionghan_chess" / "desktop" / "resources" / "docs"


def test_version_single_source() -> None:
    """`pyproject` 不写死版本，改为从 `xionghan_chess.__version__` 读；两者必须一致。"""
    import xionghan_chess

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in data["project"], "pyproject 又写死了 version，版本号会再次分叉"
    assert data["project"]["dynamic"] == ["version"]
    attr = data["tool"]["setuptools"]["dynamic"]["version"]["attr"]
    assert attr == "xionghan_chess.__version__"
    assert xionghan_chess.__version__.count(".") == 2, xionghan_chess.__version__


def test_piece_rules_copies_are_identical() -> None:
    """`docs/` 与 `resources/docs/` 的副本必须逐字节一致。"""
    pairs = [("PIECE_RULES.md", ROOT / "docs" / "PIECE_RULES.md", RESOURCES / "PIECE_RULES.md"),
             ("ABOUT.md", ROOT / "docs" / "ABOUT.md", RESOURCES / "ABOUT.md"),
             ("HELP.md", ROOT / "docs" / "HELP.md", RESOURCES / "HELP.md")]
    checked = 0
    for name, public, bundled in pairs:
        if not public.is_file() or not bundled.is_file():
            continue
        checked += 1
        a = hashlib.sha256(public.read_bytes()).hexdigest()
        b = hashlib.sha256(bundled.read_bytes()).hexdigest()
        assert a == b, (
            f"{name} 两份不一致（{a[:12]} vs {b[:12]}）。"
            "注意：改 docs/ 那份对用户无效，请同步 resources/docs/ 那份（进包的是它）")
    assert checked >= 1, "一份双份文档都没检查到，路径是不是变了？"
