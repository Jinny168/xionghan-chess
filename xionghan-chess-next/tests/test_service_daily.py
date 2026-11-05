"""网页端每日一题的接口与接线守卫。

分工是刻意的：**选题在服务端算**（`core/daily.py`，与桌面同源），
前端只负责记「今天做没做」。如果哪天有人图省事在前端再实现一套星期配方，
两端的"每日"就会在某个日期上分叉 —— 这几条断言就是拦这个的。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from xionghan_chess.core import daily
from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.service.app import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_daily_matches_core_selection() -> None:
    response = client.get("/api/daily")
    assert response.status_code == 200
    data = response.json()
    today = date.today()
    assert data["day"] == today.isoformat()
    expected = daily.pick_daily(load_puzzles(), today)
    assert data["puzzle"]["id"] == expected.id
    # 前端要能直接开题：解法与局面都得带上
    assert data["puzzle"]["solution"] and data["puzzle"]["document"]


def test_daily_accepts_an_explicit_day() -> None:
    day = date(2026, 11, 2)          # 周一 → beginner
    data = client.get("/api/daily", params={"day": day.isoformat()}).json()
    assert data["day"] == day.isoformat()
    assert data["puzzle"]["difficulty"] == daily.level_for(day) == "beginner"


def test_daily_rejects_a_malformed_day() -> None:
    assert client.get("/api/daily", params={"day": "abc"}).status_code == 400


def test_web_uses_the_api_and_local_storage_key() -> None:
    """接线守卫：入口按钮、接口调用、存储键三样缺一不可。"""
    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    assert "/api/daily" in js, "前端没有走 /api/daily —— 是不是又自己算了一套？"
    assert daily.DAILY_KEY in js, f"前端没有使用统一的存储键 {daily.DAILY_KEY}"
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'id="dailyPuzzleButton"' in html, "训练弹窗里缺少每日入口按钮"
