"""用户题库导入单测（问题 P1-K）。

`import_puzzles` 原本是空壳：选完文件只弹一句提示，什么都没发生。这里锁住
「真的写进用户题库、下次还能读出来、坏文件不会写坏存储」这三件事。

不依赖 PySide6：导入逻辑在 `desktop/puzzle_store.py`，只碰文件与 core 的解析。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xionghan_chess.core.puzzles import load_puzzles, move_to_dict
from xionghan_chess.desktop import config, puzzle_store


@pytest.fixture()
def store(tmp_path: Path) -> Path:
    """把用户数据目录挪到临时目录，避免碰真实的 %APPDATA%。"""
    return tmp_path / "puzzles.json"


def _entry(pid: str = "imported-1", difficulty: str = "beginner") -> dict:
    """以一条真实内置题为模板造一条合法题目（题面直接用它的 document）。"""
    base = load_puzzles()[0]
    return {
        "id": pid,
        "title": f"导入题 {pid}",
        "difficulty": difficulty,
        "description": "用于测试的导入题目",
        "document": base.document,
        "solution": [move_to_dict(base.solution[0])],
        "hints": ["提示一"],
        "tags": ["导入"],
    }


def _write(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return path


def test_install_adds_puzzle_and_persists(tmp_path: Path, store: Path) -> None:
    source = _write(tmp_path / "incoming.json", [_entry()])
    result = puzzle_store.install_puzzles(source, path=store)
    assert (result.added, result.skipped, result.total) == (1, 0, 1)
    assert store.is_file()

    loaded, warning = puzzle_store.load_user_puzzles(store)
    assert warning == ""
    assert [p.id for p in loaded] == ["imported-1"]


def test_installed_puzzle_is_playable(store: Path) -> None:
    """导入的题必须能被判定器认作「解法首着正确」，否则导入等于没导入。"""
    from xionghan_chess.desktop.training import VERDICT_CORRECT, VERDICT_SOLVED, PuzzleSession

    puzzle_store.install_puzzles(_write(Path(store).parent / "a.json", [_entry()]), path=store)
    loaded, _ = puzzle_store.load_user_puzzles(store)
    assert loaded
    session = PuzzleSession(loaded[0])
    assert session.submit(loaded[0].solution[0]) in (VERDICT_CORRECT, VERDICT_SOLVED)


def test_duplicate_of_builtin_id_is_skipped(store: Path) -> None:
    """随包题目的 id 不能被外部文件顶掉。"""
    builtin_id = load_puzzles()[0].id
    result = puzzle_store.install_puzzles(_write(store.parent / "b.json", [_entry(builtin_id)]), path=store)
    assert (result.added, result.skipped) == (0, 1)
    assert not store.exists(), "全部跳过时不该创建存储文件"


def test_reimporting_same_file_is_idempotent(tmp_path: Path, store: Path) -> None:
    source = _write(tmp_path / "incoming.json", [_entry()])
    puzzle_store.install_puzzles(source, path=store)
    second = puzzle_store.install_puzzles(source, path=store)
    assert (second.added, second.skipped, second.total) == (0, 1, 1)
    loaded, _ = puzzle_store.load_user_puzzles(store)
    assert len(loaded) == 1


def test_merges_with_existing_user_puzzles(tmp_path: Path, store: Path) -> None:
    puzzle_store.install_puzzles(_write(tmp_path / "one.json", [_entry("u-1")]), path=store)
    puzzle_store.install_puzzles(_write(tmp_path / "two.json", [_entry("u-2")]), path=store)
    loaded, _ = puzzle_store.load_user_puzzles(store)
    assert {p.id for p in loaded} == {"u-1", "u-2"}


@pytest.mark.parametrize("payload", ["not a list", {}, [{"id": "x"}]])
def test_invalid_source_raises_and_leaves_store_untouched(
        payload: object, tmp_path: Path, store: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        puzzle_store.install_puzzles(source, path=store)
    assert not store.exists(), "非法文件不能写坏存储"


def test_empty_list_is_rejected(tmp_path: Path, store: Path) -> None:
    source = _write(tmp_path / "empty.json", [])
    with pytest.raises(ValueError):
        puzzle_store.install_puzzles(source, path=store)


def test_corrupt_user_store_does_not_break_training_window(store: Path) -> None:
    """自定义题库坏了只应「被忽略 + 提示」，不能让训练窗口打不开。"""
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text("{ this is not json", encoding="utf-8")
    merged, warning = puzzle_store.available_puzzles(store)
    assert len(merged) == len(load_puzzles())
    assert "自定义题库读取失败" in warning


def test_available_puzzles_puts_builtin_first(store: Path) -> None:
    puzzle_store.install_puzzles(_write(store.parent / "c.json", [_entry()]), path=store)
    merged, _ = puzzle_store.available_puzzles(store)
    assert merged[0].id == load_puzzles()[0].id
    assert merged[-1].id == "imported-1"


def test_puzzles_file_lives_in_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """用户题库必须落在 data_dir 下，跟 settings/games 在一起。"""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert config.puzzles_file() == config.data_dir() / "puzzles.json"


def test_training_dialog_lists_imported_puzzle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """端到端：导入后，训练对话框的列表里真的能看到这道题。

    只测 `install_puzzles` 写文件是不够的 —— 如果对话框还读旧数据源，
    玩家依旧看不到导入的题（P1-K 的原始症状是「点了没反应」，这里防的是
    「存进去了但界面不认」）。
    """
    pytest.importorskip("PySide6", reason="TrainingDialog 依赖 PySide6")
    from PySide6.QtWidgets import QApplication

    from xionghan_chess.desktop.ui.dialogs import TrainingDialog

    monkeypatch.setenv("APPDATA", str(tmp_path))        # 用户数据目录挪到临时目录
    target = config.puzzles_file()
    puzzle_store.install_puzzles(_write(tmp_path / "incoming.json", [_entry()]), path=target)

    QApplication.instance() or QApplication([])
    dialog = TrainingDialog(None)
    try:
        dialog.level.setCurrentIndex(0)                 # beginner（导入题用的就是这档）
        ids = {puzzle.id for puzzle in dialog.puzzles}
        assert "imported-1" in ids
    finally:
        dialog.deleteLater()
