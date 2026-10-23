"""用户题库的导入与合并（问题 P1-K）。

## 背景

`TrainingDialog.import_puzzles()` 此前是个**空壳**：选完文件只弹一句
「外部题库文件已选择；服务端题库接口可将其合并为共享题库」，什么都没发生
—— 界面上摆着一个点了没用的按钮。

## 设计

- 随包题库（`core/data/puzzles.json`）**只读**，导入的题目落到
  `%APPDATA%\\XionghanChess\\puzzles.json`（见 `config.puzzles_file()`）。
- 合法性交给 `core.puzzles.load_puzzles()` 判定：它已经会拒绝「不是列表」、
  「缺字段」、「id 重复」这些情况，不在这里再写一套校验规则。
- id 冲突**跳过而不是覆盖**：随包题目是发布内容，不能被一个同名 id 悄悄换掉；
  用户自己重复导入同一份文件也只是「跳过」的提示，不会写坏存储。
- 本模块不依赖 PySide6，导入逻辑因此可以用临时目录直接单测。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from xionghan_chess.core.puzzles import Puzzle, load_puzzles, move_to_dict

from .config import puzzles_file


@dataclass(frozen=True, slots=True)
class InstallResult:
    added: int
    skipped: int
    total: int

    @property
    def summary(self) -> str:
        if self.added == 0:
            return f"没有新增题目（{self.skipped} 条 id 已存在）。"
        suffix = f"，{self.skipped} 条已存在跳过" if self.skipped else ""
        return f"已导入 {self.added} 条题目{suffix}。当前自定义题库共 {self.total} 条。"


def _entry(puzzle: Puzzle) -> dict[str, object]:
    """把 `Puzzle` 还原成可被 `load_puzzles` 重新读入的条目（含内联 document）。"""
    return {
        "id": puzzle.id,
        "title": puzzle.title,
        "difficulty": puzzle.difficulty,
        "description": puzzle.description,
        "document": puzzle.document,
        "solution": [move_to_dict(move) for move in puzzle.solution],
        "hints": list(puzzle.hints),
        "tags": list(puzzle.tags),
    }


def load_user_puzzles(path: Path | None = None) -> tuple[list[Puzzle], str]:
    """读用户题库。文件不存在返回空列表；文件坏了返回空列表 + 一句说明。

    不抛异常是刻意的：一个坏掉的导入文件不该让整个训练窗口打不开。
    """
    target = path or puzzles_file()
    if not target.is_file():
        return [], ""
    try:
        return load_puzzles(target), ""
    except Exception as exc:  # noqa: BLE001 —— 任何解析失败都只影响自定义题库
        return [], f"自定义题库读取失败（已忽略）：{exc}"


def available_puzzles(path: Path | None = None) -> tuple[list[Puzzle], str]:
    """随包 + 自定义，按 id 去重（随包优先）。返回 (题目列表, 警告)。"""
    builtin = load_puzzles()
    user, warning = load_user_puzzles(path)
    seen = {puzzle.id for puzzle in builtin}
    merged = list(builtin)
    for puzzle in user:
        if puzzle.id in seen:
            continue
        merged.append(puzzle)
        seen.add(puzzle.id)
    return merged, warning


def install_puzzles(source: Path, path: Path | None = None) -> InstallResult:
    """把外部 JSON 题库并入用户题库。

    `load_puzzles(source)` 会先做完整校验，非法文件在这里就抛 `ValueError`/
    `KeyError`，由界面转成一句可读的提示 —— 不会出现「导入一半写坏存储」。
    """
    target = path or puzzles_file()
    incoming = load_puzzles(source)          # 非法题库在此抛错
    if not incoming:
        raise ValueError("题库文件里没有任何题目")

    builtin_ids = {puzzle.id for puzzle in load_puzzles()}
    current, _ = load_user_puzzles(target)
    known = builtin_ids | {puzzle.id for puzzle in current}

    added: list[Puzzle] = []
    skipped = 0
    for puzzle in incoming:
        if puzzle.id in known:
            skipped += 1
            continue
        added.append(puzzle)
        known.add(puzzle.id)

    if added:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = [_entry(puzzle) for puzzle in [*current, *added]]
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
    return InstallResult(added=len(added), skipped=skipped, total=len(current) + len(added))
