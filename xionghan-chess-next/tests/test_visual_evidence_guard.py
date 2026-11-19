"""目检证据图守卫（只读文件，不依赖无头浏览器）。

证据目录 ``benchmarks/visual_evidence/`` 默认不入库；CI 上没有该目录时整组 skip
（skip 原因写明「本地证据不入库，CI 无此目录」）。目录存在时校验：

1. 每张证据图字节数 > 20 KB；
2. 各图 SHA256 两两不同（防止同一张全景图冒充多个验收点，如 M-1 / M-2 重复）；
3. 磁盘上的文件名集合与目检模板 ``docs/visual_manual_check_record.md`` 里索引的
   证据文件名一致（新增证据图必须先在模板登记，守卫自动继承，不写死张数）。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "benchmarks" / "visual_evidence"
TEMPLATE = ROOT / "docs" / "visual_manual_check_record.md"

MIN_BYTES = 20_000
_PNG_RE = re.compile(r"benchmarks/visual_evidence/([A-Za-z0-9_.-]+\.png)")


def _evidence_pngs() -> list[Path]:
    return sorted(p for p in EVIDENCE_DIR.glob("*.png") if p.is_file())


def _indexed_in_template() -> set[str]:
    text = TEMPLATE.read_text(encoding="utf-8")
    return set(_PNG_RE.findall(text))


def _require_evidence_dir() -> list[Path]:
    pngs = _evidence_pngs()
    if not pngs:
        pytest.skip("本地证据不入库，CI 无此目录（benchmarks/visual_evidence/ 缺失或无 PNG）")
    return pngs


def test_evidence_files_are_large_enough() -> None:
    pngs = _require_evidence_dir()
    small = [(p.name, p.stat().st_size) for p in pngs if p.stat().st_size <= MIN_BYTES]
    assert not small, f"证据图字节数 ≤ {MIN_BYTES}：{small}"


def test_evidence_hashes_are_pairwise_distinct() -> None:
    pngs = _require_evidence_dir()
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for p in pngs:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest in seen:
            collisions.append(f"{p.name} 与 {seen[digest]} 哈希相同")
        else:
            seen[digest] = p.name
    assert not collisions, "证据图存在逐字节重复（同一张图冒充多个验收点）：" + "; ".join(collisions)


def test_evidence_filenames_match_template_index() -> None:
    pngs = _require_evidence_dir()
    on_disk = {p.name for p in pngs}
    indexed = _indexed_in_template()
    unindexed = sorted(on_disk - indexed)
    assert not unindexed, f"证据图未在目检模板登记：{unindexed}"
    missing_on_disk = sorted(name for name in indexed if (EVIDENCE_DIR / name).exists() and name not in on_disk)
    assert not missing_on_disk, f"模板已索引但磁盘缺失：{missing_on_disk}"
