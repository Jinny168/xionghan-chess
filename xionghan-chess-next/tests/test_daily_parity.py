"""每日一题跨端选题对拍：JS (webapp/js/ui/daily.js) 必须与 Python (core/daily.py) 逐日一致。

这是"每日对所有人是同一道题"承诺的硬门禁。两端题库已由 build_web_puzzles.py
统一为 core 35 条；本测试再钉死选题算法等价 —— 任一端改算法而另一端没跟，
同一天选出不同题，这里立刻红。

覆盖：一年 365 天（跨整周轮换）+ 基准日前的回拨日期 + bucket/dayIndex 逐项。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "webapp" / "tests" / "daily-probe.mjs"

sys.path.insert(0, str(ROOT / "src"))
from xionghan_chess.core.daily import bucket_of, day_index, level_for, pick_daily  # noqa: E402
from xionghan_chess.core.puzzles import load_puzzles  # noqa: E402


def _js_rows(start: str, days: int) -> list[dict]:
    proc = subprocess.run(
        ["node", str(PROBE), start, str(days)],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
    )
    return json.loads(proc.stdout)


def test_js_daily_selection_matches_python_for_a_full_year() -> None:
    """365 天逐日比对 level/id/dayIndex/bucket，全等才算跨端同源。"""
    puzzles = load_puzzles()
    start = date(2026, 1, 5)  # BASE_MONDAY
    rows = _js_rows(start.isoformat(), 365)
    assert len(rows) == 365

    mismatches: list[str] = []
    for i, row in enumerate(rows):
        day = start + timedelta(days=i)
        py_level = level_for(day)
        py_puzzle = pick_daily(puzzles, day)
        py_id = py_puzzle.id if py_puzzle else None
        if row["level"] != py_level:
            mismatches.append(f"{day} level js={row['level']} py={py_level}")
            continue
        if row["id"] != py_id:
            mismatches.append(f"{day} id js={row['id']} py={py_id}")
            continue
        for level, key in (("beginner", "dayIndexBeginner"), ("advanced", "dayIndexAdvanced"), ("master", "dayIndexMaster")):
            if row[key] != day_index(day, level):
                mismatches.append(f"{day} dayIndex[{level}] js={row[key]} py={day_index(day, level)}")
        for level, key in (("beginner", "bucketBeginner"), ("advanced", "bucketAdvanced"), ("master", "bucketMaster")):
            py_bucket = [p.id for p in bucket_of(puzzles, level)]
            if row[key] != py_bucket:
                mismatches.append(f"{day} bucket[{level}] 分叉")

    assert not mismatches, "跨端选题不一致（前 10 条）：\n" + "\n".join(mismatches[:10])


def test_js_handles_dates_before_base_like_python() -> None:
    """基准日前的日期：core 按基准日算（指针不出现负数），JS 必须一致。"""
    puzzles = load_puzzles()
    start = date(2025, 12, 29)
    rows = _js_rows(start.isoformat(), 7)  # 基准日前 7 天到前 1 天
    for i, row in enumerate(rows):
        day = start + timedelta(days=i)
        py_puzzle = pick_daily(puzzles, day)
        assert row["id"] == (py_puzzle.id if py_puzzle else None), f"{day} 回拨日期选题不一致"
        assert row["dayIndexBeginner"] == day_index(day, "beginner"), f"{day} 回拨 dayIndex 不一致"
