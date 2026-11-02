"""每日一题：选题稳定、难度轮换、连续天数语义。

这几条都容易"看起来对但实际会漂"，所以逐条钉死：
- 同一天必须永远算出同一题（否则玩家刷新一次就换题）；
- 难度按星期固定轮换（周一出新手、周末出大师）；
- 桶内不重复，直到轮完一遍（复现周期 = 桶容量 ÷ 每周次数）；
- 连续天数：隔天做完才 +1，同一天重解不涨，断一天归零，系统时间回拨不惩罚。
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from xionghan_chess.core import daily
from xionghan_chess.core.puzzles import Puzzle, load_puzzles


def _fake(pid: str, level: str) -> Puzzle:
    """只要 id / difficulty 的假题 —— 选题不碰棋局，不需要真 document。"""
    return Puzzle(pid, pid, level, "", {}, (), (), ())


def _pool() -> list[Puzzle]:
    return ([_fake(f"b{i:02d}", "beginner") for i in range(1, 6)]
            + [_fake(f"a{i:02d}", "advanced") for i in range(1, 6)]
            + [_fake(f"m{i:02d}", "master") for i in range(1, 4)])


def test_same_day_always_picks_the_same_puzzle() -> None:
    pool = _pool()
    day = date(2026, 11, 2)
    picks = {daily.pick_daily(pool, day).id for _ in range(20)}
    assert len(picks) == 1, f"同一天算出了多道题：{picks}"


def test_weekday_rotation_is_fixed() -> None:
    """周一到周日：新/进/新/进/新/大/大。"""
    monday = date(2026, 11, 2)          # 2026-11-02 是周一
    levels = [daily.level_for(monday + timedelta(days=i)) for i in range(7)]
    assert levels == ["beginner", "advanced", "beginner", "advanced",
                      "beginner", "master", "master"]


def test_bucket_does_not_repeat_until_exhausted() -> None:
    """同一难度的桶在轮完一遍之前不重复（这是「复现周期」的分子）。"""
    pool = _pool()
    # 取该难度出现的所有日期，看前 len(bucket) 次是否互不相同
    seen: list[str] = []
    day = date(2026, 11, 2)
    while len(seen) < 15:
        picked = daily.pick_daily(pool, day)
        if picked.difficulty == "beginner":
            seen.append(picked.id)
        day += timedelta(days=1)
    assert len(set(seen[:5])) == 5, f"新手桶 5 条却在 {seen[:5]} 里提前重复"


def test_master_bucket_falls_back_when_empty() -> None:
    """大师题不够时按 master → advanced → beginner 降级，不能当天无题。"""
    pool = [_fake("b01", "beginner"), _fake("a01", "advanced")]
    saturday = date(2026, 11, 7)
    assert daily.level_for(saturday) == "master"
    picked = daily.pick_daily(pool, saturday)
    assert picked is not None and picked.difficulty == "advanced"


def test_real_library_covers_every_weekday() -> None:
    """随包题库要保证一周七天都能出题（不然某天打开是空的）。"""
    pool = load_puzzles()
    day = date(2026, 11, 2)
    for offset in range(7):
        assert daily.pick_daily(pool, day + timedelta(days=offset)) is not None


def test_day_index_survives_dates_before_base() -> None:
    """系统时间被拨到基准日之前时，指针不许变成负数。"""
    assert daily.day_index(date(2025, 1, 1), "beginner") == 1


# --- 连续天数 -------------------------------------------------------------

def test_first_solve_starts_the_streak() -> None:
    day = date(2026, 11, 2)
    record = daily.solve_today(daily.DailyRecord(), day, _fake("b01", "beginner"))
    assert record.done and record.streak == 1 and record.best == 1
    assert record.day == "2026-11-02"


def test_consecutive_days_add_one() -> None:
    first = date(2026, 11, 2)
    record = daily.solve_today(daily.DailyRecord(), first, _fake("b01", "beginner"))
    record = daily.solve_today(record, first + timedelta(days=1), _fake("a01", "advanced"))
    assert record.streak == 2 and record.best == 2


def test_solving_twice_in_one_day_does_not_add() -> None:
    day = date(2026, 11, 2)
    puzzle = _fake("b01", "beginner")
    record = daily.solve_today(daily.DailyRecord(), day, puzzle)
    again = daily.solve_today(record, day, puzzle)
    assert again.streak == 1


def test_gap_of_one_day_resets_on_read() -> None:
    """昨天开了没做完 → 今天读出来就该是 0（惰性归零，不跑定时任务）。"""
    yesterday = date(2026, 11, 1)
    today = yesterday + timedelta(days=1)
    record = daily.DailyRecord(day=yesterday.isoformat(), id="b01", done=False, streak=4, best=6)
    started = daily.start_today(record, today, _fake("b02", "beginner"))
    assert started.streak == 0
    assert started.best == 6, "累计最长不该被重置"


def test_clock_rollback_is_not_punished() -> None:
    """系统时间回拨：不惩罚、不提示、不重置。"""
    future = date(2026, 11, 10)
    record = daily.DailyRecord(day=future.isoformat(), id="b01", done=True, streak=3, best=3)
    started = daily.start_today(record, date(2026, 11, 1), _fake("b02", "beginner"))
    assert started == record


def test_start_today_keeps_streak_when_yesterday_was_solved() -> None:
    """昨天做完了、今天打开：连续天数保留，等今天解出再 +1。"""
    yesterday = date(2026, 11, 1)
    record = daily.DailyRecord(day=yesterday.isoformat(), id="b01", done=True, streak=2, best=2)
    started = daily.start_today(record, yesterday + timedelta(days=1), _fake("a01", "advanced"))
    assert started.streak == 2
    solved = daily.solve_today(started, yesterday + timedelta(days=1), _fake("a01", "advanced"))
    assert solved.streak == 3


def test_record_roundtrips_through_dict_and_survives_garbage() -> None:
    record = daily.DailyRecord(day="2026-11-02", id="b01", done=True, streak=3, best=5)
    assert daily.DailyRecord.from_dict(record.to_dict()) == record
    for garbage in (None, {}, {"streak": "x"}, {"streak": -2}, 42):
        assert daily.DailyRecord.from_dict(garbage) == daily.DailyRecord()
