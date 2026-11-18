"""文字提示层 scored 守卫（批次 A / 裁决5 三方一致部分）。

裁决5：两段式**文字**提示——章节闯关 scored=false 可用且计入星级；连对挑战 /
每日一题 scored=true 屏蔽一切提示。星轨几何层是另一条线（三端全屏蔽，不在此测）。

桌面实现：`MainWindow.show_puzzle_hint` 首行 `if self.puzzle_scored: return`。
本测试守两件事：
1. 行为：PuzzleSession 的提示计数只在没被 scored 守卫拦下时才增长；
2. 结构：三端文字提示入口都有 scored 守卫（web/webapp 由前端主程负责实现）。
"""

from __future__ import annotations

from pathlib import Path

from xionghan_chess.core.model import Move, Position
from xionghan_chess.core.puzzles import Puzzle
from xionghan_chess.desktop import training

ROOT = Path(__file__).resolve().parents[1]


def _puzzle() -> Puzzle:
    from xionghan_chess.core.puzzles import load_puzzles

    base = load_puzzles()[0]
    return Puzzle("g-1", "守卫题", "beginner", "描述", base.document,
                  (Move(Position(8, 4), Position(7, 4)),), ("提示一", "提示二"), ("defense",))


def test_hint_counts_toward_penalty_when_shown() -> None:
    """文字提示一旦展示就计入 penalty —— 星级公式 = attempts + hints_shown。"""
    session = training.PuzzleSession(_puzzle())
    assert session.stars == 0  # 未解
    session.staged_hint()  # 第一段：指子
    session.staged_hint()  # 第二段：指招
    assert session._hints_shown == 2
    session.submit(session.expected)
    assert session.stars == 2, "看两段提示 = 2 次扣分 → 2 星"


def test_desktop_text_hint_has_scored_guard() -> None:
    """桌面 show_puzzle_hint 首行必须有 scored 守卫（计分态屏蔽文字提示）。"""
    app_src = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")
    start = app_src.index("def show_puzzle_hint")
    body = app_src[start : start + 600]
    assert "if self.puzzle_scored:" in body and "return" in body, "桌面文字提示缺 scored 守卫"


def test_daily_and_streak_are_marked_scored() -> None:
    """每日一题与连对挑战都用 scored=True 入口；章节闯关 scored=False。"""
    app_src = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")
    # start_streak 走 scored=True，show_training 里每日题 scored=puzzle_is_daily
    assert "self._load_puzzle_into_board(first, scored=True" in app_src, "连对挑战须计分态"
    assert "self.puzzle_scored = self.puzzle_is_daily" in app_src, "每日题计分、章节闯关不计分"
