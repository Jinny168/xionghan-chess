"""训练进度纯函数的**三端口径对拍**（批次 A / P1-3 + P1-4 硬门禁）。

Python `core/training_progress.py` 是权威实现；webapp 的 `webapp/js/ui/training_progress.js`
是镜像。本测试把同一组输入同时喂给两者，逐项比对：章节顺序、星级映射、章节解锁、
连对题池排序、软提示阈值、章节汇总。任一端漂移立即红。

web 旧树不在此探针内（它的训练逻辑内联在 app.js，由 test_web_tree_training.py 做结构守卫）。
缺 node 时按 `tests/_node_guard.py` 硬失败，不许静默 green。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from _node_guard import NODE, module_skip_mark, require_node

from xionghan_chess.core import training_progress as tp

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "training_progress_probe.mjs"
WEBAPP_MODULE = ROOT / "webapp" / "js" / "ui" / "training_progress.js"

if (mark := module_skip_mark()) is not None:
    pytestmark = mark


PUZZLES = [
    {"id": "drill-1", "chapter": "", "tags": ["drill"]},
    {"id": "a1", "chapter": "揭竿", "tags": ["mate3"]},
    {"id": "a2", "chapter": "揭竿", "tags": ["mate3"]},
    {"id": "b1", "chapter": "破釜", "tags": ["defense"]},
    {"id": "b2", "chapter": "破釜", "tags": ["feature:archer"]},
    {"id": "c1", "chapter": "逐鹿", "tags": ["mate5"]},
    {"id": "c2", "chapter": "逐鹿", "tags": ["equilibrium"]},
    {"id": "d1", "chapter": "垓下", "tags": ["mate7"]},
    {"id": "d2", "chapter": "垓下", "tags": ["counter"]},
    {"id": "e1", "chapter": "定鼎", "tags": ["mate7"]},
    {"id": "e2", "chapter": "定鼎", "tags": ["feature:guard"]},
]

STAR_CASES = [
    {},
    {"a1": 3, "a2": 2},
    {"a1": 3, "a2": 3, "b1": 1, "b2": 2},
    {"a1": 3, "a2": 3, "b1": 3, "b2": 3, "c1": 1, "c2": 1},
    {p["id"]: 3 for p in PUZZLES if p["chapter"]},
]


def _js_results() -> dict:
    require_node()
    proc = subprocess.run(
        [NODE, str(PROBE), str(WEBAPP_MODULE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(proc.stdout)


def test_chapter_order_matches_core() -> None:
    assert list(tp.CHAPTER_ORDER) == ["揭竿", "破釜", "逐鹿", "垓下", "定鼎"]
    assert _js_results()["chapterOrder"] == list(tp.CHAPTER_ORDER)


def test_python_pure_functions_match_js() -> None:
    js = _js_results()

    # chapterIndex
    py_idx = [tp.chapter_index(c) for c in ["", "揭竿", "破釜", "逐鹿", "垓下", "定鼎", "不存在"]]
    assert js["chapterIndex"] == py_idx

    # starsFor
    py_stars = []
    for m in [0, 1, 2, 3, 4, 9]:
        py_stars.append([m, tp.stars_for(m, 0), tp.stars_for(0, m), tp.stars_for(m, m)])
    assert js["stars"] == py_stars

    # softHintDue
    assert js["softHint"] == [tp.soft_hint_due(n) for n in [0, 4, 5, 6, 20]]

    # unlockedChapters
    py_unlocked = [tp.unlocked_chapters(s, PUZZLES) for s in STAR_CASES]
    assert js["unlocked"] == py_unlocked

    # poolFor
    py_pool = [
        [p["id"] for p in tp.pool_for(s, tp.unlocked_chapters(s, PUZZLES), "a1" if i % 2 else None, PUZZLES)]
        for i, s in enumerate(STAR_CASES)
    ]
    assert js["pool"] == py_pool

    # chapterSummary
    py_summary = [tp.chapter_summary(s, tp.unlocked_chapters(s, PUZZLES), PUZZLES) for s in STAR_CASES]
    assert js["summary"] == py_summary


def test_stars_formula_guard() -> None:
    """星级公式锁定：0→3、1-2→2、≥3→1；错着与提示等价计入。"""
    assert tp.stars_for(0, 0) == 3
    assert tp.stars_for(1, 0) == 2
    assert tp.stars_for(0, 2) == 2
    assert tp.stars_for(1, 1) == 2
    assert tp.stars_for(2, 0) == 2
    assert tp.stars_for(3, 0) == 1
    assert tp.stars_for(0, 3) == 1
    assert tp.stars_for(2, 2) == 1


def test_unlock_chain_and_no_star_threshold() -> None:
    """首章默认开；解出即开下一章（stars>=1），不要求 3 星；链式不跳级。"""
    # 空进度只开揭竿
    assert tp.unlocked_chapters({}, PUZZLES) == ["揭竿"]
    # 揭竿两题都只用 1 星解出 → 破釜开（不卡 3 星）
    stars = {"a1": 1, "a2": 1}
    assert tp.unlocked_chapters(stars, PUZZLES) == ["揭竿", "破釜"]
    # 破釜未解 → 逐鹿不开（链式）
    assert "逐鹿" not in tp.unlocked_chapters(stars, PUZZLES)
    # 全部解出 → 五章全开
    all_stars = {p["id"]: 1 for p in PUZZLES if p["chapter"]}
    assert tp.unlocked_chapters(all_stars, PUZZLES) == list(tp.CHAPTER_ORDER)


def test_pool_excludes_drill_and_daily() -> None:
    stars = {p["id"]: 3 for p in PUZZLES if p["chapter"]}
    opened = list(tp.CHAPTER_ORDER)
    pool = tp.pool_for(stars, opened, "b1", PUZZLES)
    ids = [p["id"] for p in pool]
    assert "drill-1" not in ids, "drill 不进连对题池"
    assert "b1" not in ids, "当日每日题不进连对题池"
    assert all(p["chapter"] for p in pool)


def test_pool_priority_unplayed_first() -> None:
    """优先级：未做过 → 星级<3 → 已满星；同级按章节顺序。"""
    stars = {"a1": 3, "b1": 1}  # a1 满星、b1 一星，其余未做
    opened = list(tp.CHAPTER_ORDER)
    pool = [p["id"] for p in tp.pool_for(stars, opened, None, PUZZLES)]
    # 未做过的 a2/b2/c1/... 应排在有星级的 a1/b1 之前
    assert pool.index("a2") < pool.index("a1")
    assert pool.index("b2") < pool.index("b1")
