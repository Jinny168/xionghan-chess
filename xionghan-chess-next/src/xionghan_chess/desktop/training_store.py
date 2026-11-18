"""桌面训练进度存储（批次 A / P1-3 + P1-4）。

## 存哪里

`config["training"]` 一个分区（settings.json 物理文件），内部分区：
- `stars`: {puzzle_id: 历史最高星 1-3}（重做取最高星，不取最后一次）
- `unlocked`: [章节名]（顺序解锁，首章默认开）
- `streak.best`: 连对挑战历史最大连对题数（只增不减）
- `storm.best`: 预留区（限时冲刺已砍，逻辑/UI 不建，仅为将来兼容占位）

## 零采集

本模块只读写本地 `config` 字典（由调用方 save_config 落盘）。`training` 键
**不在**云同步的 allowlist（`app.py` 的 cloud_to_desktop / 偏好映射）里，
既不上传也不下载；每日一题的坚持天数仍在 `config["daily"]`（xh-daily），
成绩绝不混进每日键。字段名与 webapp/web 旧树的 `xh-training` 逐字一致。

## 单一口径

解锁/星级/题池算法全部委托 `core.training_progress`（权威实现），本模块只负责
"把结果读写到 config 的 training 分区"，不重算算法。
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from xionghan_chess.core.training_progress import (
    CHAPTER_ORDER,
    chapter_summary,
    pool_for,
    unlocked_chapters,
)

DEFAULT_TRAINING: dict[str, Any] = {
    "stars": {},
    "unlocked": [CHAPTER_ORDER[0]],
    "streak": {"best": 0},
    "storm": {"best": 0},  # 预留区：限时冲刺已砍，不建逻辑/UI
}


def normalize(data: object) -> dict[str, Any]:
    """把任意（老配置/缺字段/坏类型）的 training 分区归一成合法结构。

    逐层补默认值、逐字段做类型校验 —— 坏存档不能让训练窗口打不开。
    """
    raw = data if isinstance(data, dict) else {}
    stars_raw = raw.get("stars") if isinstance(raw.get("stars"), dict) else {}
    stars: dict[str, int] = {}
    for pid, value in stars_raw.items():
        try:
            star = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= star <= 3:
            stars[str(pid)] = star
    unlocked_raw = raw.get("unlocked")
    opened = set(c for c in unlocked_raw if c in CHAPTER_ORDER) if isinstance(unlocked_raw, list) else set()
    # 解锁必须是从首章起的前缀（链式不跳级）：从第一章往后走，遇到第一个未解锁就停。
    # 坏存档里"只有逐鹿、没有破釜"这种跳级状态会被截成 ["揭竿"]，而不是放行。
    unlocked: list[str] = []
    for chapter in CHAPTER_ORDER:
        if chapter in opened:
            unlocked.append(chapter)
        else:
            break
    if not unlocked:
        unlocked = [CHAPTER_ORDER[0]]
    streak_raw = raw.get("streak") if isinstance(raw.get("streak"), dict) else {}
    try:
        best = max(0, int(streak_raw.get("best", 0)))
    except (TypeError, ValueError):
        best = 0
    return {
        "stars": stars,
        "unlocked": unlocked,
        "streak": {"best": best},
        "storm": {"best": 0},
    }


def read(config: Mapping[str, Any]) -> dict[str, Any]:
    """从配置读训练分区（缺字段自动补默认）。"""
    return normalize(config.get("training"))


def write(config: dict[str, Any], training: Mapping[str, Any]) -> None:
    """把训练分区写回配置（调用方负责 save_config 落盘）。"""
    config["training"] = normalize(training)


def record_stars(config: dict[str, Any], puzzle_id: str, stars: int) -> dict[str, Any]:
    """记录某题星级：**取历史最高星**（重做不会把 3 星刷回 1 星）。

    只记已解出（stars>=1）；0 星（未解）不写入。
    """
    state = read(config)
    if stars >= 1:
        state["stars"][puzzle_id] = max(state["stars"].get(puzzle_id, 0), int(stars))
    write(config, state)
    return state


def refresh_unlocks(config: dict[str, Any], puzzles: Sequence[Mapping[str, Any]]) -> list[str]:
    """按当前星级重算解锁列表并写回（星级提升后可能新开章节）。"""
    state = read(config)
    state["unlocked"] = unlocked_chapters(state["stars"], puzzles)
    write(config, state)
    return state["unlocked"]


def summary(config: dict[str, Any], puzzles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    state = read(config)
    return chapter_summary(state["stars"], state["unlocked"], puzzles)


def record_streak_best(config: dict[str, Any], count: int) -> int:
    """连对挑战结束后更新历史最高：**只增不减**，返回更新后的 best。"""
    state = read(config)
    state["streak"]["best"] = max(state["streak"]["best"], max(0, int(count)))
    write(config, state)
    return state["streak"]["best"]


def puzzle_pool(
    config: dict[str, Any], daily_id: str | None, puzzles: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    """连对挑战题池（已解锁章节、非 drill、排除当日题），按抽题优先级排序。"""
    state = read(config)
    return pool_for(state["stars"], state["unlocked"], daily_id, puzzles)
