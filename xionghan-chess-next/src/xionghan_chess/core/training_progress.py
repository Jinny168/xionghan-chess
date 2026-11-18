"""训练进度纯算法（批次 A / P1-3 章节化 + P1-4 连对挑战）。

## 单一口径

本章节/星级/解锁/题池算法以本模块为**权威实现**，webapp（`webapp/js/ui/training_progress.js`）
与 web 旧树各有一份 JS 镜像，靠 node 探针与本模块逐项对拍（`tests/test_training_parity.py`）。
改这里的语义必须同步改两端 JS，否则对拍门禁会红。

## 零依赖约束

**零 DOM、零存储、零网络**：只吃普通 dict/list，只出普通值。存储（localStorage /
settings.json["training"]）由各端组合根自己负责，本模块不碰——它是纯算法，便于对拍。

## 命名纪律（四词表，全局统一）

- 坚持天数：每日一题的连续天数，单位「天」，记在 xh-daily，本模块不碰；
- 连胜局数：对局胜局的 winStreak，单位「局」，既有统计不动，本模块不碰；
- 连对题数：连对挑战（一错即止）的成绩，单位「题」，记在 training.streak.best；
- 本次得分：本轮分数，本轮不使用。

Storm（限时冲刺）已砍：不建 score/next/storm 函数，仅为存储预留 storm.best 区。
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from xionghan_chess.core.puzzles import CHAPTERS

# 与 CHAPTERS 同源，不再单独维护一份列表（消除重复维护漂移）。
CHAPTER_ORDER: tuple[str, ...] = CHAPTERS

# 受控标签：守题/特色/反击/练习
_TAG_DEFENSE = "defense"
_TAG_EQUILIBRIUM = "equilibrium"
_TAG_DRILL = "drill"
_FEATURE_PREFIX = "feature:"
_SOFT_HINT_THRESHOLD = 5


def chapter_index(name: str | None) -> int:
    """章节序号；未知/空串排在最后（与 JS chapterIndex 一致）。"""
    return CHAPTER_ORDER.index(name) if name in CHAPTER_ORDER else len(CHAPTER_ORDER)


def stars_for(misses: int, hints: int) -> int:
    """星级：只罚错着与提示，不奖励速度。0→3、1–2→2、≥3→1。

    与桌面 `PuzzleSession.stars` 同一公式（penalty = attempts + hints_shown）。
    未解出由调用方传 0；本函数只管"已解出"的罚分映射。
    """
    penalty = (misses or 0) + (hints or 0)
    if penalty == 0:
        return 3
    return 2 if penalty <= 2 else 1


def _field(item: Any, name: str, default: Any = None) -> Any:
    """统一读取字段：题库加载后是 `Puzzle` dataclass，JS 对拍喂进来的是 dict。"""
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _is_drill(item: Any) -> bool:
    return _TAG_DRILL in (_field(item, "tags", ()) or ())


def chapter_puzzles(puzzles: Iterable[Any], chapter: str) -> list[Any]:
    """某章的正式题（排除 drill），保持题库原序。"""
    return [item for item in puzzles if _field(item, "chapter") == chapter and not _is_drill(item)]


def unlocked_chapters(
    stars: Mapping[str, int],
    puzzles: Iterable[Mapping[str, Any]],
    chapters: Sequence[str] = CHAPTER_ORDER,
) -> list[str]:
    """章节解锁：首章默认开；第 N 章 = 第 N-1 章全部题解出过（stars>=1）。

    「用过提示 / 错过也算解出」——所以判据是 stars>=1 而非 ==3；星级不做门槛。
    严格链式：前一章没解锁后面一律锁死，不许跳级。空章不算「全部解出」
    （那是题库数据缺陷，不能静默放行；真实五章都有题）。
    """
    solved = stars or {}
    pool = list(puzzles)
    unlocked: list[str] = []
    for i, chapter in enumerate(chapters):
        if i == 0:
            unlocked.append(chapter)
            continue
        if chapters[i - 1] not in unlocked:
            continue
        previous = chapter_puzzles(pool, chapters[i - 1])
        if previous and all((solved.get(_field(item, "id"), 0) or 0) >= 1 for item in previous):
            unlocked.append(chapter)
    return unlocked


def pool_for(
    stars: Mapping[str, int],
    unlocked: Sequence[str],
    daily_id: str | None,
    puzzles: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """连对挑战题池：已解锁章节 + 非 drill + 排除当日每日一题。

    只返回**按抽题优先级排好的池**；一轮内不重复由会话层维护 used 集合。
    优先级：未做过(0) → 星级<3(1) → 其余(2)；同级按章节顺序，再按题库原序。
    """
    solved = stars or {}
    opened = set(unlocked or ())

    def rank(item: Any) -> int:
        star = solved.get(_field(item, "id"), 0) or 0
        if star == 0:
            return 0
        if star < 3:
            return 1
        return 2

    eligible = [
        item
        for item in puzzles
        if _field(item, "chapter")
        and _field(item, "chapter") in opened
        and not _is_drill(item)
        and _field(item, "id") != daily_id
    ]
    indexed = list(enumerate(eligible))
    indexed.sort(
        key=lambda pair: (
            rank(pair[1]),
            chapter_index(_field(pair[1], "chapter")),
            pair[0],
        )
    )
    return [item for _, item in indexed]


def soft_hint_due(consecutive_misses: int, threshold: int = _SOFT_HINT_THRESHOLD) -> bool:
    """卡关软提示：某题连续错误达到阈值就问一句「要不要看条提示？」。"""
    return (consecutive_misses or 0) >= threshold


def chapter_summary(
    stars: Mapping[str, int],
    unlocked: Sequence[str],
    puzzles: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """章节汇总：每章 {chapter,total,solved,stars,max,unlocked}。"""
    solved = stars or {}
    opened = set(unlocked or ())
    pool = list(puzzles)
    rows: list[dict[str, Any]] = []
    for chapter in CHAPTER_ORDER:
        items = chapter_puzzles(pool, chapter)
        earned = sum((solved.get(_field(item, "id"), 0) or 0) for item in items)
        rows.append(
            {
                "chapter": chapter,
                "total": len(items),
                "solved": sum(1 for item in items if (solved.get(_field(item, "id"), 0) or 0) >= 1),
                "stars": earned,
                "max": len(items) * 3,
                "unlocked": chapter in opened,
            }
        )
    return rows


def is_defense_puzzle(item: Any) -> bool:
    """守题/解均势题：正解是化解威胁而非将死，末手不该是杀棋。"""
    tags = _field(item, "tags", ()) or ()
    return _TAG_DEFENSE in tags or _TAG_EQUILIBRIUM in tags


def is_feature_puzzle(item: Any) -> bool:
    """特色子题：正解必须用到射/巡/檑/尉之一。"""
    return any(str(tag).startswith(_FEATURE_PREFIX) for tag in (_field(item, "tags", ()) or ()))
