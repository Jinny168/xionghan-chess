"""每日一题：选题规则与连续天数（纯逻辑，两端共用）。

三条设计约束（见 `docs/IMPROVEMENT_PLAN.md`）：
1. **零联网、零采集**：题目只由**本地日期**决定，不读统计、不上报。
2. **难度按星期固定轮换**，不做自适应 —— "每日"要对所有人是同一道题，
   才谈得上"每天来一次"这个约定；自适应会让两个朋友同一天看到不同的题。
3. **桶内指针是纯函数**：不存"我做到第几题"，只由日期推出来。
   存指针会在换题库版本时错位，而由日期推是幂等的 —— 换题库最多换一道题，不会跳着走。

状态只记一件事：今天做没做、连续几天。桌面写 `settings.json` 的 `daily` 一个对象，
网页写 localStorage 单键 `xh-daily`，字段名两端必须一致。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Iterable

from .puzzles import Puzzle

# 基准日必须是**周一**，否则"按星期轮换"的对齐会随起始日漂。
BASE_MONDAY = date(2026, 1, 5)

# 周一到周日：新手 / 进阶 / 新手 / 进阶 / 新手 / 大师 / 大师
# 新手占三天是为了让"每天都来"的人不至于连续两天撞难题；周末两道大师题给周期性的期待。
WEEKDAY_LEVELS: tuple[str, ...] = (
    "beginner", "advanced", "beginner", "advanced", "beginner", "master", "master",
)

# 每周各难度出现几次 —— 由 WEEKDAY_LEVELS 数出来，不重复维护
PER_WEEK = {level: WEEKDAY_LEVELS.count(level) for level in set(WEEKDAY_LEVELS)}

# 难度桶空了时的回落顺序：大师题最稀缺，先退回进阶，再退回新手。
FALLBACK = {"master": ("advanced", "beginner"), "advanced": ("beginner",), "beginner": ()}

DAILY_KEY = "xh-daily"


@dataclass(frozen=True, slots=True)
class DailyRecord:
    """一天一条记录（单键覆盖，不按天堆键 —— 那会无限增长且两端清理策略不一致）。"""

    day: str = ""          # "YYYY-MM-DD"，本条记录对应的本地日期
    id: str = ""           # 当日题 id（题库换版后用来判断"今天还是不是那道题"）
    done: bool = False     # 当日是否已解出
    streak: int = 0        # 当前连续天数
    best: int = 0          # 历史最长连续

    def to_dict(self) -> dict:
        return {"day": self.day, "id": self.id, "done": self.done,
                "streak": self.streak, "best": self.best}

    @classmethod
    def from_dict(cls, data: object) -> "DailyRecord":
        """坏数据一律当空记录：宁可重置一次连续，也不要在本地炸掉整个设置文件。"""
        if not isinstance(data, dict):
            return cls()
        def _int(key: str) -> int:
            value = data.get(key, 0)
            return value if isinstance(value, int) and value >= 0 else 0
        return cls(
            day=str(data.get("day") or ""),
            id=str(data.get("id") or ""),
            done=bool(data.get("done")),
            streak=_int("streak"),
            best=_int("best"),
        )


def level_for(day: date) -> str:
    """当天该出哪一档题（周一=0）。"""
    return WEEKDAY_LEVELS[day.weekday()]


def _days_before_base(day: date) -> int:
    return (day - BASE_MONDAY).days


def day_index(day: date, level: str) -> int:
    """从基准周一到当天，落在该难度的第几天（含当天，1 起）。

    用整周乘法而不是逐天循环：跨几年也只是常数次运算。
    早于基准日的日期一律按基准日算（返回 1）—— 系统时间被拨到过去时不该出现负数指针。
    """
    delta = _days_before_base(day)
    if delta < 0:
        delta = 0
    full_weeks, remainder = divmod(delta, 7)
    within_week = sum(1 for i in range(remainder + 1) if WEEKDAY_LEVELS[i] == level)
    return full_weeks * PER_WEEK.get(level, 0) + within_week


def bucket_of(puzzles: Iterable[Puzzle], level: str) -> list[Puzzle]:
    """按 id 字典序排 —— 指针靠字典序，发布后**不许改名**。"""
    return sorted((p for p in puzzles if p.difficulty == level), key=lambda p: p.id)


def pick_daily(puzzles: Iterable[Puzzle], day: date) -> Puzzle | None:
    """当天的那道题。桶空时按 FALLBACK 降级，全空则返回 None。"""
    pool = list(puzzles)
    level = level_for(day)
    for candidate in (level, *FALLBACK.get(level, ())):
        bucket = bucket_of(pool, candidate)
        if not bucket:
            continue
        # 同一天必须永远算出同一题：全靠这两个输入（日期、题库 id 排序）
        index = (day_index(day, candidate) - 1) % len(bucket)
        return bucket[index]
    return None


def yesterday_of(day: date) -> date:
    return day - timedelta(days=1)


def start_today(record: DailyRecord, day: date, puzzle: Puzzle | None) -> DailyRecord:
    """打开每日题时调用：惰性归零，但**不提前把 day 推到今天**。

    这一点很关键：`day` 记的是"最后一次有结果的日期"。如果在打开时就改写成今天，
    "昨天做完了"这个事实就没了，今天解出只能算 `streak = 1` —— 连续天数永远涨不上去。
    所以这里只刷新 streak 与缺失的 id，`day/id/done` 留到真正解出时由 `solve_today` 改写。
    """
    if puzzle is None:
        return record
    today = day.isoformat()
    # 系统时间被回拨：不惩罚、不提示、不重置，原样返回
    if record.day and today < record.day:
        return record
    return replace(record, id=record.id or puzzle.id, streak=_lazy_streak(record, day))


def _lazy_streak(record: DailyRecord, day: date) -> int:
    """读取时惰性归零：昨天没做完就断了，不必写定时任务。"""
    if not record.day:
        return 0
    try:
        last = date.fromisoformat(record.day)
    except ValueError:
        return 0
    gap = (day - last).days
    if gap > 1:
        return 0                      # 断了两天以上
    if gap == 1 and not record.done:
        return 0                      # 昨天开了没做
    return record.streak


def solve_today(record: DailyRecord, day: date, puzzle: Puzzle) -> DailyRecord:
    """解出时调用。同一天重解不涨，隔天做完才 +1。"""
    today = day.isoformat()
    if record.day == today and record.done:
        return record
    streak = 1
    if record.day:
        try:
            last = date.fromisoformat(record.day)
        except ValueError:
            last = None
        if last is not None and (day - last).days == 1 and record.done:
            streak = record.streak + 1
    return DailyRecord(day=today, id=puzzle.id, done=True,
                       streak=streak, best=max(streak, record.best))
