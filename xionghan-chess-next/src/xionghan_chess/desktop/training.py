"""训练模式的正解判定（阶段2 S2-7 配套）。

## 为什么需要这个模块

`TrainingDialog` 原本只把题面载入成一个**普通对局**：`start_selected()` 做
`game_from_document(puzzle.document)` 就 `accept()`，之后玩家走任意一步都不会
得到任何反馈 —— `Puzzle.solution` 在桌面端从来没被读过，只有 `hints[0]` 被
「提示」按钮用到。题库内容再真，没有判定也只是一张摆好的棋盘。

## 设计取舍

- **不依赖 PySide6**：判对错是纯状态机，放这里就能用普通单测覆盖（与 `net.py`、
  `update.py` 同一分工）。界面只负责把结论翻译成人话。
- **答错不「扣分」，只累计尝试次数**：这是训练不是考试。次数用来决定第几次
  该给更强的提示（`next_hint`），而不是惩罚。
- **只比对起止格，不比对升变**：题目解法里从不写 `promotion`，而玩家走兵到底线时
  会被升变对话框插入一个 `promotion` 字段。若按整对象比较，正解会被判错。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from xionghan_chess.core.model import Move
from xionghan_chess.core.puzzles import Puzzle

VERDICT_CORRECT = "correct"
VERDICT_SOLVED = "solved"
VERDICT_WRONG = "wrong"


@dataclass(slots=True)
class PuzzleSession:
    """一次题目练习的进度。`cursor` 指向「下一步该走哪一手」。"""

    puzzle: Puzzle
    cursor: int = 0
    attempts: int = 0
    _hints_shown: int = field(default=0, repr=False)

    @property
    def total(self) -> int:
        return len(self.puzzle.solution)

    @property
    def solved(self) -> bool:
        return self.cursor >= self.total

    @property
    def expected(self) -> Move | None:
        """当前应走的那一手；已解出返回 None。"""
        return None if self.solved else self.puzzle.solution[self.cursor]

    def matches(self, move: Move) -> bool:
        target = self.expected
        if target is None:
            return False
        return ((move.source.row, move.source.col, move.target.row, move.target.col)
                == (target.source.row, target.source.col, target.target.row, target.target.col))

    def submit(self, move: Move) -> str:
        """判定一手棋。返回 `correct` / `solved` / `wrong`（都是字符串常量）。"""
        if self.solved:
            return VERDICT_SOLVED
        if not self.matches(move):
            self.attempts += 1
            return VERDICT_WRONG
        self.cursor += 1
        return VERDICT_SOLVED if self.solved else VERDICT_CORRECT

    def next_hint(self) -> str:
        """按尝试次数逐级放宽提示：第 1 次错给第 1 条，第 2 次给第 2 条……

        提示用完就停在最后一条 —— 反复给同一句，比每次冒出新的「提示」更诚实。
        """
        hints = self.puzzle.hints
        if not hints:
            return ""
        index = min(max(self.attempts - 1, 0), len(hints) - 1)
        self._hints_shown = max(self._hints_shown, index + 1)
        return hints[index]

    def reset(self) -> None:
        self.cursor = 0
        self.attempts = 0


def session_for(puzzle: Puzzle | None) -> PuzzleSession | None:
    """给 `None` 就返回 `None` —— 调用方据此判断「当前不是训练模式」。"""
    return None if puzzle is None else PuzzleSession(puzzle)
