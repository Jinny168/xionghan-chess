"""AI 台词：场景表（中/英双语）+ 确定性选词 + 频率约束。

## 为什么要重写

旧实现是单语 `TAUNTS` 字典 + `TAUNTS.get(scene, TAUNTS["opening"])`：
① 未知场景**静默回落**到 opening —— 新场景（如 `draw_declined`）写错名字时不会报错，
   只会一直说"请多指教"；② 只有中文，`language` 参数根本没有；③ 选词用
   `random.Random(seed)`，而调用方传的是 `seed=None`，于是同一事件每次都换词、
   也没法跳过"刚说过的那句"。

现在的分工：

- **表**：`TAUNTS_ZH` / `TAUNTS_EN`，键集必须相同（`tests/test_taunts.py` 钉住）；
  查未知场景直接 `KeyError`，不再回落。
- **选词**：`select_taunt` 用 `zlib.crc32(seed_material + scene)` 取模，同一事件
  （同一局、同一手、同一场景）永远同一句；`recent_texts` 用来跳过上一句，避免连说两遍。
- **频率**：`taunt_allowed` 是纯函数，桌面与服务端共用同一套上限，避免两端各写一份
  然后慢慢分叉。返回 `(bool, reason)`，reason 只用于测试/诊断，不进 UI。
"""

from __future__ import annotations

import random
import zlib
from collections.abc import Sequence
from typing import Literal, get_args

TauntScene = Literal["opening", "check", "victory", "defeat", "draw_declined", "random"]

# `random` 不是可发送的场景，只是"取全部台词"的聚合伪场景（快捷短语下拉用）。
SCENE_NAMES: tuple[str, ...] = tuple(
    name for name in get_args(TauntScene) if name != "random")

TAUNTS_ZH: dict[str, tuple[str, ...]] = {
    "opening": ("请多指教", "先行一步，静观其变。", "棋局方始，莫急。", "让我们看看谁更稳。"),
    "check": ("将军，留神脚下。", "这一手可不轻松。", "王前有变，慎之。", "请接招。"),
    "victory": ("承让，这局棋妙在收官。", "胜负已分，再来一局？", "多谢指教。", "这一局我先取胜。"),
    "defeat": ("好棋，我记下了。", "此局受教，再战。", "胜负常事，下一局见。", "这一手确实漂亮。"),
    "draw_declined": ("此局尚未到和棋之时。", "再走走看，胜负未分。", "局面还有变化，暂不接受。",
                      "想和？先过这一关。"),
}

TAUNTS_EN: dict[str, tuple[str, ...]] = {
    "opening": ("A good game to you.", "I'll take the first step and watch.",
                "The board is set — no rush.", "Let's see who holds steadier."),
    "check": ("Check — mind your footing.", "That move was not easy.",
              "Your king is exposed; be careful.", "Your move."),
    "victory": ("A good game — the endgame was the art.", "The result is settled. Another?",
                "Thank you for the game.", "I take this one."),
    "defeat": ("Well played — noted.", "A lesson for me. Again.",
               "Win and loss are common. Next game.", "That move was truly fine."),
    "draw_declined": ("Not a draw yet.", "Let's play on — nothing is settled.",
                      "The position still has life.", "A draw? Not so fast."),
}

# 语言键 → 场景表。`language` 走 `_language_key` 归一，不直接索引。
TAUNTS: dict[str, dict[str, tuple[str, ...]]] = {"zh": TAUNTS_ZH, "en": TAUNTS_EN}

# 频率上限（每局）：总量 ≤4；每场景各自上限；两次之间至少隔 4 手。
# 用户口径（2026-11-09 定稿）：6/2 → 4/4；`draw_declined` 也计入总量 4。
# `draw_declined` 是"被拒必发"：不受 4 手冷却约束，也只受总数 4 约束（不做单场景限 1），
# 否则连续两次提和被拒时"必发"就不成立。
TAUNT_TOTAL_LIMIT = 4
TAUNT_MIN_PLY_GAP = 4
TAUNT_SCENE_LIMITS: dict[str, int] = {
    "opening": 1, "check": 2, "draw_declined": TAUNT_TOTAL_LIMIT,
    "victory": 1, "defeat": 1,
}
# 绕过冷却的场景（"必发"类）。
TAUNT_COOLDOWN_EXEMPT: frozenset[str] = frozenset({"draw_declined"})

# 「局势大幅波动」触发阈值：AI 视角 `_evaluate` 的一步变化 ≥240（VALUES 兵=120，即 2 兵）。
# AI 变好 → `check`（挑衅），AI 变差 → `defeat`（自嘲）。方向由 service/desktop 判定，
# 这里只放数值，避免两端各写一个 240。
TAUNT_SWING_THRESHOLD = 240.0


def _language_key(language: str) -> str:
    return "en" if language.lower().startswith("en") else "zh"


def taunts(scene: TauntScene | str = "random", language: str = "zh-CN") -> list[str]:
    """取某场景的全部台词。未知场景 **KeyError**（旧实现会静默回落到 opening）。"""
    table = TAUNTS[_language_key(language)]
    if scene == "random":
        return [text for values in table.values() for text in values]
    return list(table[scene])


def select_taunt(scene: TauntScene | str, language: str = "zh-CN",
                 seed_material: str = "", recent_texts: Sequence[str] = ()) -> str | None:
    """确定性选词：同一 `seed_material` + 场景 → 同一句；跳过 `recent_texts` 的最后一句。

    返回 `None` 只可能发生在场景表为空时（当前不会）；签名保留 `None` 是为了让调用方
    显式处理"没有可说的话"，而不是拿到空串往聊天框里塞。
    """
    values = taunts(scene, language)
    if not values:
        return None
    index = zlib.crc32(f"{seed_material}:{scene}".encode()) % len(values)
    if recent_texts and len(values) > 1 and values[index] == recent_texts[-1]:
        index = (index + 1) % len(values)
    return values[index]


def swing_scene(previous_eval: float, current_eval: float) -> TauntScene | None:
    """一步之内 AI 视角评估变化 ≥ `TAUNT_SWING_THRESHOLD` 时该说哪一句。

    - AI 变好（delta > 0）→ `check`（挑衅类）；
    - AI 变差（delta < 0）→ `defeat`（自嘲类）；
    - 变化不足 → `None`（本步不触发）。
    """
    delta = current_eval - previous_eval
    if abs(delta) < TAUNT_SWING_THRESHOLD:
        return None
    return "check" if delta > 0 else "defeat"


def taunt_allowed(scene: TauntScene | str, plies: int, sent_total: int,
                  sent_by_scene: dict[str, int], last_ply: int | None,
                  last_text: str | None, next_text: str | None = None) -> tuple[bool, str]:
    """频率判定（纯函数）。返回 `(是否允许, 原因)`；原因仅用于测试/诊断。

    规则（与设计口径一致）：
    - 每局总量 ≤ `TAUNT_TOTAL_LIMIT`（4）；
    - 每场景各自的 `TAUNT_SCENE_LIMITS`；
    - 两次台词至少隔 `TAUNT_MIN_PLY_GAP`（4）手；`draw_declined` 例外（被拒必发，
      见 `TAUNT_COOLDOWN_EXEMPT`），但仍计入总数；
    - 同一句不连续：`select_taunt` 已主动跳过上一句，这里在 `next_text` 给出时再兜一层
      （调用方若自己选词，仍然受这条约束）。
    """
    if scene not in TAUNT_SCENE_LIMITS:
        return False, "not_a_scene"
    if sent_total >= TAUNT_TOTAL_LIMIT:
        return False, "total_limit"
    if sent_by_scene.get(scene, 0) >= TAUNT_SCENE_LIMITS[scene]:
        return False, "scene_limit"
    if last_ply is not None and plies - last_ply < TAUNT_MIN_PLY_GAP \
            and scene not in TAUNT_COOLDOWN_EXEMPT:
        return False, "too_soon"
    if next_text is not None and last_text is not None and next_text == last_text:
        return False, "same_text"
    return True, ""


def choose_taunt(scene: TauntScene | str = "random", seed: int | None = None,
                 language: str = "zh-CN") -> str:
    """旧接口（保留）：随机取一句。新代码请用 `select_taunt`（确定性、可跳过上一句）。"""
    return random.Random(seed).choice(taunts(scene, language))
