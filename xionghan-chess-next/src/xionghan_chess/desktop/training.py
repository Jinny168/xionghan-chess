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
from xionghan_chess.core.puzzles import Puzzle, piece_type_at

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
    # 两段式提示的进度：0 未提示 / 1 已指子 / 2 已指招。换到下一手要归零。
    _hint_stage: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        # 解法是**交替序列**：偶数下标归玩家、奇数下标是对手应着。
        # 偶数长度会停在"对手刚走完"，玩家无从落子 —— 这是数据错误，构造时就该炸。
        if len(self.puzzle.solution) % 2 == 0:
            # 开发者向的断言，不是界面文案，所以不走 dl()：写死中文会被
            # `tests/test_desktop_texts.py` 判成"未翻译的界面字面量"。
            raise ValueError(
                "solution length must be odd (even indices are the player's moves, "
                "odd ones are forced replies): "
                f"{len(self.puzzle.solution)} plies would end on the opponent's move")

    @property
    def total(self) -> int:
        return len(self.puzzle.solution)

    @property
    def player_total(self) -> int:
        """面向玩家的「手数」= 解方要走的步数。

        `total` 是内部 ply（含对手应着），3 ply 的题是 2 手、4 ply 是 2 手。
        UI 一律用这个数，别拿 `total` 直接显示 —— 否则 5 ply 会写成「5 步」，多算对手两着。
        """
        return (self.total + 1) // 2

    @property
    def player_index(self) -> int:
        """下一手是解方的第几手（从 1 起）。已解出时等于 `player_total`。"""
        return min(self.cursor // 2 + 1, self.player_total)

    @property
    def solved(self) -> bool:
        return self.cursor >= self.total

    @property
    def auto_reply(self) -> Move | None:
        """轮到对手时（奇数下标）应自动落的那一手；其余情况返回 None。

        多步题的强度来自「对手最优抵抗」，所以 `solution` 是**交替序列**：
        偶数下标是玩家要走的，奇数下标是对手的被迫应着。玩家不该看到、也不该走奇数下标。
        """
        if self.solved or self.cursor % 2 == 0:
            return None
        return self.puzzle.solution[self.cursor]

    def advance_auto(self) -> None:
        """替对手落完 `auto_reply` 之后推进游标。"""
        if self.auto_reply is not None:
            self.cursor += 1

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
        if self.cursor % 2 == 1:
            # 奇数下标是对手应着，由 `auto_reply` 自动落；玩家在这一步提交一定是错的
            self.attempts += 1
            return VERDICT_WRONG
        if not self.matches(move):
            self.attempts += 1
            return VERDICT_WRONG
        self.cursor += 1
        self._hint_stage = 0
        return VERDICT_SOLVED if self.solved else VERDICT_CORRECT

    def staged_hint(self) -> tuple[str, str] | None:
        """两段式提示：先"用哪枚子"，再"怎么走"。返回 `(kind, text)`。

        `kind` 为 `"piece"` 时 `text` 是子力类型（UI 负责翻成中文名）；
        为 `"move"` 时是题面里那句走法提示。

        为什么要分两段：直接给整句等于替玩家想完；只说"用这枚子"能把他按到正确的
        那几行上去，仍要自己找落点。两段都看才扣两次分（星级里算两次）。
        """
        if self.solved:
            return None
        move = self.expected
        if move is None:
            return None
        self._hints_shown += 1
        if self._hint_stage == 0:
            self._hint_stage = 1
            return "piece", (piece_type_at(self.puzzle, move.source) or "")
        self._hint_stage = 2
        hand = self.cursor // 2
        text = self.puzzle.hints[hand] if hand < len(self.puzzle.hints) else ""
        return "move", text

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

    @property
    def stars(self) -> int:
        """1–3 星；未解出返回 0。

        只罚"错着"和"提示"两件事：这道题的解法是**唯一强制线**，不存在"更短的走法"，
        所以星级不该奖励速度或运气，只反映"你有多少是自己想出来的"。
        错一次 + 看一次提示各算一次扣分：0 次满分、1–2 次两星、再多一星。
        """
        if not self.solved:
            return 0
        penalty = self.attempts + self._hints_shown
        if penalty == 0:
            return 3
        return 2 if penalty <= 2 else 1

    def reset(self) -> None:
        self.cursor = 0
        self.attempts = 0


def session_for(puzzle: Puzzle | None) -> PuzzleSession | None:
    """给 `None` 就返回 `None` —— 调用方据此判断「当前不是训练模式」。"""
    return None if puzzle is None else PuzzleSession(puzzle)
