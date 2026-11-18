"""桌面训练进度存储单测（批次 A / P1-3 + P1-4）。

纯逻辑，不依赖 Qt / 磁盘：只用内存 dict 验证 training 分区的归一、星级最高值、
解锁写回、连对只增不减、零采集（training 键不在云同步 allowlist）。
"""

from __future__ import annotations

from xionghan_chess.desktop import training_store as store

PUZZLES = [
    {"id": "drill-1", "chapter": "", "tags": ["drill"]},
    {"id": "a1", "chapter": "揭竿", "tags": ["mate3"]},
    {"id": "a2", "chapter": "揭竿", "tags": ["mate3"]},
    {"id": "b1", "chapter": "破釜", "tags": ["defense"]},
    {"id": "b2", "chapter": "破釜", "tags": ["feature:archer"]},
    {"id": "c1", "chapter": "逐鹿", "tags": ["mate5"]},
]


def test_normalize_fills_defaults_and_drops_garbage() -> None:
    state = store.normalize(
        {"stars": {"a1": 3, "bad": 9, "zero": 0, "str": "x"}, "unlocked": ["逐鹿", "???"], "streak": {"best": -5}}
    )
    assert state["stars"] == {"a1": 3}, "只保留 1-3 星"
    assert state["unlocked"] == ["揭竿"], "跳级状态（有逐鹿无破釜）截成合法前缀"
    assert state["streak"]["best"] == 0, "负数归零"
    assert state["storm"]["best"] == 0, "预留区恒为 0"


def test_read_missing_returns_default() -> None:
    assert store.read({}) == store.DEFAULT_TRAINING


def test_record_stars_keeps_historical_max() -> None:
    config: dict = {}
    store.record_stars(config, "a1", 3)
    store.record_stars(config, "a1", 1)  # 重做拿低星
    assert store.read(config)["stars"]["a1"] == 3, "重做不覆盖历史最高星"
    store.record_stars(config, "a1", 0)  # 未解不写入
    assert store.read(config)["stars"]["a1"] == 3


def test_refresh_unlocks_chain() -> None:
    config: dict = {}
    assert store.refresh_unlocks(config, PUZZLES) == ["揭竿"]
    store.record_stars(config, "a1", 1)
    store.record_stars(config, "a2", 1)
    assert store.refresh_unlocks(config, PUZZLES) == ["揭竿", "破釜"]
    store.record_stars(config, "b1", 3)
    store.record_stars(config, "b2", 3)
    assert store.refresh_unlocks(config, PUZZLES) == ["揭竿", "破釜", "逐鹿"]


def test_record_streak_best_only_increases() -> None:
    config: dict = {}
    assert store.record_streak_best(config, 5) == 5
    assert store.record_streak_best(config, 3) == 5, "低分不降 best"
    assert store.record_streak_best(config, 8) == 8
    assert "daily" not in config, "连对成绩绝不写每日键"


def test_puzzle_pool_excludes_drill_and_daily() -> None:
    config: dict = {}
    store.record_stars(config, "a1", 3)
    store.record_stars(config, "a2", 3)
    store.refresh_unlocks(config, PUZZLES)
    pool = [p["id"] for p in store.puzzle_pool(config, "b1", PUZZLES)]
    assert "drill-1" not in pool
    assert "b1" not in pool  # 当日题
    assert "c1" not in pool  # 未解锁章节
    assert "a1" in pool and "a2" in pool


def test_summary_shape() -> None:
    config: dict = {}
    rows = store.summary(config, PUZZLES)
    assert [r["chapter"] for r in rows] == ["揭竿", "破釜", "逐鹿", "垓下", "定鼎"]
    assert rows[0]["unlocked"] is True
    assert rows[1]["unlocked"] is False
    assert rows[0]["total"] == 2 and rows[0]["max"] == 6


def test_training_key_absent_from_cloud_allowlist() -> None:
    """零采集：训练键不得出现在桌面云同步的 mapping 里。"""
    import ast
    from pathlib import Path

    app_src = (Path(__file__).resolve().parents[1] / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(app_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"mapping", "cloud_to_desktop"}:
                    literal = ast.literal_eval(node.value)
                    values = list(literal.values()) if isinstance(literal, dict) else []
                    assert "training" not in values, f"{target.id} 含 training，会泄漏进度到云端"
