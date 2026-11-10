import asyncio
import re

import pytest

from xionghan_chess.core.taunts import (
    SCENE_NAMES,
    TAUNT_MIN_PLY_GAP,
    TAUNT_SCENE_LIMITS,
    TAUNT_SWING_THRESHOLD,
    TAUNT_TOTAL_LIMIT,
    TAUNTS_EN,
    TAUNTS_ZH,
    choose_taunt,
    select_taunt,
    swing_scene,
    taunt_allowed,
    taunts,
)
from xionghan_chess.service.rooms import RoomManager

# 用户定稿的 12 条（场景内顺序即展示顺序）。测试逐字钉住：改一个字都要连测试一起改。
EXPECTED_ZH = {
    "opening": ("请多指教。", "开局不必急。", "我先落子，静观其变。"),
    "check": ("将军，脚下留神。", "这一手，你大概没算到。", "让一让，我要过路了。"),
    "victory": ("承让，这局收官不错。", "多谢指教，再来一局？"),
    "defeat": ("好棋，我记下了。", "这一手我确实没想到。"),
    "draw_declined": ("和棋？我这局还没下够。", "局面还没到那一步。"),
}
EXPECTED_EN = {
    "opening": ("Your move.", "No need to rush the opening.", "I'll start and see where this goes."),
    "check": ("Check — mind your footing.", "Bet you didn't count on that one.", "Coming through."),
    "victory": ("Good game — clean finish.", "Thanks for the game. Again?"),
    "defeat": ("Well played. Noted.", "I genuinely missed that."),
    "draw_declined": ("A draw? I'm not done yet.", "The position isn't there yet."),
}


def test_bilingual_tables_match_the_final_12_lines():
    """用户定稿 12 条：opening 3 / check 3 / victory 2 / defeat 2 / draw_declined 2。"""
    assert set(TAUNTS_ZH) == set(TAUNTS_EN) == set(SCENE_NAMES)
    assert "random" not in TAUNTS_ZH
    for scene in SCENE_NAMES:
        assert TAUNTS_ZH[scene] == EXPECTED_ZH[scene], scene
        assert TAUNTS_EN[scene] == EXPECTED_EN[scene], scene
    assert sum(len(values) for values in TAUNTS_ZH.values()) == 12
    assert len(taunts("random")) == 12
    assert taunts("random", "en") != taunts("random", "zh-CN")
    assert choose_taunt("check", seed=3) in TAUNTS_ZH["check"]


def test_unknown_scene_raises_keyerror_instead_of_falling_back():
    """旧实现 `TAUNTS.get(scene, TAUNTS["opening"])` 会把写错的场景静默说成"请多指教"。"""
    with pytest.raises(KeyError):
        taunts("no_such_scene")
    with pytest.raises(KeyError):
        select_taunt("no_such_scene", "zh-CN", "seed")


def test_english_tables_contain_no_cjk():
    for values in TAUNTS_EN.values():
        for text in values:
            assert not re.search(r"[\u4e00-\u9fff]", text), text


def test_select_taunt_is_deterministic_and_skips_the_previous_line():
    first = select_taunt("check", "zh-CN", "room-1:2:check")
    assert first is not None
    assert first == select_taunt("check", "zh-CN", "room-1:2:check")
    # 换任意 seed_material，也要跳过"上一句"（表长 4，跳过必然换一条）。
    for index in range(12):
        following = select_taunt("check", "zh-CN", f"room-1:{index}:check", [first])
        assert following is not None and following != first


def test_taunt_allowed_enforces_all_four_rules():
    assert TAUNT_TOTAL_LIMIT == 4 and TAUNT_MIN_PLY_GAP == 4
    assert taunt_allowed("opening", 2, 0, {}, None, None) == (True, "")
    assert taunt_allowed("opening", 2, TAUNT_TOTAL_LIMIT, {}, None, None) == (False, "total_limit")
    assert taunt_allowed("check", 10, 0, {"check": TAUNT_SCENE_LIMITS["check"]}, None, None) == (False, "scene_limit")
    assert taunt_allowed("check", 10, 0, {}, 10 - TAUNT_MIN_PLY_GAP + 1, None) == (False, "too_soon")
    assert taunt_allowed("check", 10, 0, {}, 1, "同一句", "同一句") == (False, "same_text")
    assert taunt_allowed("check", 10, 0, {}, 1, "上一句", "另一句") == (True, "")
    assert taunt_allowed("random", 10, 0, {}, None, None) == (False, "not_a_scene")
    # 「被拒必发」：draw_declined 绕过 4 手冷却，但仍受总数 4 约束。
    assert taunt_allowed("draw_declined", 10, 0, {}, 10, "上一句") == (True, "")
    assert taunt_allowed("draw_declined", 10, TAUNT_TOTAL_LIMIT, {}, 10, "上一句") == (False, "total_limit")


def test_swing_scene_maps_direction_and_threshold():
    """AI 变好 → check（挑衅），变差 → defeat（自嘲）；|Δ| < 2 兵不触发。"""
    assert TAUNT_SWING_THRESHOLD == 240.0
    assert swing_scene(0.0, TAUNT_SWING_THRESHOLD) == "check"
    assert swing_scene(0.0, TAUNT_SWING_THRESHOLD - 0.1) is None
    assert swing_scene(0.0, -TAUNT_SWING_THRESHOLD) == "defeat"
    assert swing_scene(0.0, -(TAUNT_SWING_THRESHOLD - 0.1)) is None
    assert swing_scene(-500.0, 0.0) == "check"
    assert swing_scene(500.0, 0.0) == "defeat"


def test_ai_taunt_history_respects_setting_and_deduplicates():
    async def scenario():
        manager = RoomManager()
        enabled, _ = await manager.create("traditional", "ai", "player")
        await manager._broadcast_ai_taunt(enabled, "opening")
        await manager._broadcast_ai_taunt(enabled, "opening")
        assert len(enabled.chat_history) == 1
        assert enabled.chat_history[0]["automated"] is True
        assert enabled.chat_history[0]["scene"] == "opening"

        disabled, _ = await manager.create("traditional", "ai", "player", taunts_enabled=False)
        await manager._broadcast_ai_taunt(disabled, "opening")
        assert disabled.chat_history == []

    asyncio.run(scenario())
