"""开局书（`benchmarks/openings/calibration_book.json`）的守卫。

标定的可复现性全押在这份文件上：它一旦悄悄变了（换生成器版本、换 profile、
被编辑器改掉换行），所有历史胜率都失去可比性，而**胜率本身不会报错**。

本文件钉四件事：
1. 结构：64 条 = seed 700–731 × plies 6/10，组合唯一、指纹唯一；
2. 生成器确定性：同参两次 `generate_text` 逐字节相同（无时间戳、无环境信息）；
3. 契约：`build_game` 真能按条目重建局面（`benchmark_match(position_builder=...)` 用它）；
4. **慢**：64 条 `fp` 全部可重建一致（约 30s，`-m slow` 跑；改了 `bench_roots`
   或规则引擎必须跑这条）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gen_opening_book import (  # noqa: E402
    DEFAULT_OUT,
    DEFAULT_PLIES,
    DEFAULT_PROFILE,
    DEFAULT_SEEDS,
    build_entries,
    build_game,
    generate_text,
    load_book,
)

EXPECTED_COUNT = len(DEFAULT_SEEDS) * len(DEFAULT_PLIES)  # 32 × 2 = 64


def _payload() -> dict[str, object]:
    return json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))


def test_book_structure_and_diversity() -> None:
    payload = _payload()
    assert payload["count"] == EXPECTED_COUNT == 64
    assert payload["profile"] == DEFAULT_PROFILE
    assert payload["seeds"] == [min(DEFAULT_SEEDS), max(DEFAULT_SEEDS)] == [700, 731]
    assert payload["plies"] == list(DEFAULT_PLIES) == [6, 10]

    entries = payload["openings"]
    assert len(entries) == 64
    assert all(item["profile"] == "desktop_complete" for item in entries)
    combinations = {(item["seed"], item["plies"]) for item in entries}
    assert len(combinations) == 64, "seed × plies 组合必须唯一"
    fingerprints = {item["fp"] for item in entries}
    assert len(fingerprints) == 64, "64 条开局必须互不相同（指纹口径）"
    assert all(isinstance(item["fp"], str) and item["fp"] for item in entries)
    # pieces/legal 是辅助显示（相同不代表同一局面），但必须存在且合理。
    assert all(item["pieces"] > 0 and item["legal"] > 0 for item in entries)


def test_generate_text_is_byte_deterministic() -> None:
    """同参两次生成逐字节相同：没有时间戳/机器信息混进产物。"""
    first = generate_text(profile=DEFAULT_PROFILE, seeds=(700, 701), plies_list=(2,))
    second = generate_text(profile=DEFAULT_PROFILE, seeds=(700, 701), plies_list=(2,))
    assert first == second
    assert "\r" not in first, "写盘固定 LF（配合 .gitattributes 的 -text）"


def test_loaded_book_entries_are_openings_with_fingerprints() -> None:
    book = load_book()
    assert len(book) == 64
    assert all(entry.fp for entry in book)
    assert book[0].profile == DEFAULT_PROFILE


def test_build_game_rebuilds_the_played_plies() -> None:
    """`build_game(profile, seed, plies)` 是 benchmark 侧注入的生成器：手数/子数/着数必须对得上。"""
    item = _payload()["openings"][0]
    game = build_game(item["profile"], item["seed"], item["plies"])
    assert len(game.state.history) == item["plies"]
    assert len(game.state.pieces) == item["pieces"]
    assert len(game.rules.legal_moves(game.state)) == item["legal"]


@pytest.mark.slow
def test_every_stored_fingerprint_rebuilds_identically() -> None:
    """64 条 `fp` 全部可重建一致 —— 改了生成器/规则后跑这条（约 30s）。"""
    stored = [(item["seed"], item["plies"], item["fp"]) for item in _payload()["openings"]]
    rebuilt = {(item["seed"], item["plies"]): item["fp"]
               for item in build_entries(DEFAULT_PROFILE, DEFAULT_SEEDS, DEFAULT_PLIES)}
    mismatched = [(seed, plies) for seed, plies, fp in stored
                  if rebuilt.get((seed, plies)) != fp]
    assert not mismatched, f"{len(mismatched)} 条开局指纹无法重建：{mismatched[:5]}"


@pytest.mark.slow
def test_check_mode_matches_the_committed_file() -> None:
    """`--check` 的口径：磁盘文件与重建结果逐字节一致。"""
    from gen_opening_book import main

    assert main(["--check"]) == 0
