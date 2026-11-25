"""35 道真题「为什么」解析的三端接线测试。

文案数据分离：解析只在 `core/data/puzzle_explanations.json`，题库 `puzzles.json` 不动；
桌面 `show_hint()` 与 Webapp 的 `app.puzzle.data.hints` 链路都把解析作为最后一条追加。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "gen_puzzle_explanations.py"
PROBE = ROOT / "tests" / "puzzle_explanation_probe.mjs"

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from xionghan_chess.core import puzzle_explanations as explanations  # noqa: E402
from xionghan_chess.core.puzzles import Puzzle, load_puzzles  # noqa: E402
from xionghan_chess.desktop.ui import dialogs  # noqa: E402

GEN_IDS = tuple(f"gen-{number:02d}" for number in range(1, 36))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_generator_check_is_green() -> None:
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "35 条" in result.stdout


def test_data_is_separate_from_puzzle_database() -> None:
    raw = (ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json").read_text(encoding="utf-8")
    data = explanations.load()
    assert tuple(sorted(data)) == GEN_IDS
    for puzzle_id, item in data.items():
        assert set(item) == {"key_move", "why"}, puzzle_id
        assert item["key_move"] and item["why"], puzzle_id
        assert item["why"] not in raw, "解析文案混进了题库数据"


def test_all_35_real_questions_and_no_drill() -> None:
    puzzles = load_puzzles()
    real = {puzzle.id for puzzle in puzzles if puzzle.chapter}
    drills = {puzzle.id for puzzle in puzzles if not puzzle.chapter}
    assert real == set(GEN_IDS)
    assert len(drills) == 13
    assert all(explanations.hint_for(puzzle_id) for puzzle_id in real)
    assert all(explanations.hint_for(puzzle_id) is None for puzzle_id in drills)
    assert explanations.hint_for("unknown-id") is None


def test_hint_for_has_no_authoritative_prefix_or_score() -> None:
    for puzzle_id in GEN_IDS:
        text = explanations.hint_for(puzzle_id) or ""
        assert not re.match(r"^(正确答案|AI\s*分析|为什么)[:：]", text), puzzle_id
        assert "你应该" not in text, puzzle_id
        assert not re.search(r"\d+\s*分", text), puzzle_id


def _select(dialog: dialogs.TrainingDialog, puzzle_id: str) -> None:
    for index in range(dialog.list.count()):
        item = dialog.list.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == puzzle_id:
            dialog.list.setCurrentItem(item)
            return
    raise AssertionError(f"列表里找不到 {puzzle_id}")


def test_desktop_show_hint_reveals_explanation_after_original_hint(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真行为：答完题后点提示 → 弹窗出现解析原文，且没有指令式措辞或分值。"""
    parent = QWidget()
    parent.config = {}
    dialog = dialogs.TrainingDialog(parent)
    _select(dialog, "gen-01")
    puzzle: Puzzle = dialog.current()
    assert puzzle is not None and puzzle.id == "gen-01"

    captured: list[str] = []
    monkeypatch.setattr(dialogs.QMessageBox, "information", lambda *_args: captured.append(_args[2]))

    dialog.show_hint()
    assert len(captured) == 1
    text = captured[0]
    explanation = explanations.hint_for("gen-01") or ""
    assert text.startswith(puzzle.hints[0]), "指路提示必须先出现"
    assert explanation in text, "解析没跟在指路提示之后"
    assert text.index(puzzle.hints[0]) < text.index(explanation), "解析不是最后一条"
    assert "你应该" not in text
    assert not re.search(r"\d+\s*分", text)
    assert not re.match(r"^(正确答案|AI\s*分析|为什么)[:：]", text)


def test_desktop_drill_hint_has_no_explanation(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = QWidget()
    parent.config = {}
    dialog = dialogs.TrainingDialog(parent)
    drill = next(puzzle for puzzle in dialog.puzzles if not puzzle.chapter)
    _select(dialog, drill.id)
    captured: list[str] = []
    monkeypatch.setattr(dialogs.QMessageBox, "information", lambda *_args: captured.append(_args[2]))
    dialog.show_hint()
    assert captured == [drill.hints[0]], "drill 不该接入解析"


def test_webapp_real_hint_chain() -> None:
    """Node 侧真 import 生产模块并走 app.puzzle.data.hints 揭示链路。"""
    result = subprocess.run(
        ["node", str(PROBE)], cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report == {
        "gen": 35,
        "drill": 13,
        "appended": 1,
        "shownHasWhy": True,
        "forbidden": False,
    }
