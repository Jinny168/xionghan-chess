"""连对挑战会话逻辑单测（批次 A / P1-4）。

一错即止：错一次终止、跳过不算错、池走完前不重复、连对数只增。
计分态屏蔽文字提示由 app 层 puzzle_scored 守卫负责（见 test_p1_guard.py）。
"""

from __future__ import annotations

from xionghan_chess.desktop import training


def _puzzle(pid: str) -> object:
    # StreakSession 只用 puzzle.id 做去重，不读其它字段
    return type("P", (), {"id": pid})()


def test_pool_advances_without_repeat() -> None:
    pool = [_puzzle(f"p{i}") for i in range(5)]
    session = training.StreakSession(pool)
    order = []
    for _ in range(5):
        p = session.next_puzzle()
        assert p is not None
        order.append(p.id)
    assert len(order) == len(set(order)) == 5, "一轮池走完前不重复"
    assert session.next_puzzle() is None, "池走完返回 None"


def test_correct_increments_count() -> None:
    session = training.StreakSession([_puzzle("p0")])
    assert session.count == 0
    session.on_correct()
    session.on_correct()
    assert session.count == 2


def test_one_mistake_ends_run_and_count_frozen() -> None:
    """一错即止：错前的连对数保留为本轮成绩，错误本身不加不减。"""
    session = training.StreakSession([_puzzle(f"p{i}") for i in range(5)])
    session.on_correct()
    session.on_correct()
    before = session.count
    session.on_wrong()
    assert session.count == before, "答错后本轮成绩冻结在终止前的连对数"


def test_skip_does_not_count_as_mistake() -> None:
    """跳过：结束本轮但不算错，连对数不变。"""
    session = training.StreakSession([_puzzle(f"p{i}") for i in range(5)])
    session.on_correct()
    before = session.count
    session.on_skip()
    assert session.count == before


def test_skip_threshold_default_60s() -> None:
    assert training.StreakSession([]).skip_threshold_s == 60


def test_streak_end_constants_exist() -> None:
    assert training.STREAK_END_WRONG == "wrong"
    assert training.STREAK_END_SKIP == "skip"
    assert training.STREAK_END_EXHAUSTED == "exhausted"
