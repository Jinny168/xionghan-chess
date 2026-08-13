from xionghan_chess.core.taunts import TAUNTS, choose_taunt, taunts
from xionghan_chess.service.rooms import RoomManager

import asyncio


def test_taunt_catalog_has_all_scenes_and_random_selection():
    assert set(TAUNTS) == {"opening", "check", "victory", "defeat"}
    assert len(taunts("random")) >= 16
    assert choose_taunt("check", seed=3) in TAUNTS["check"]


def test_ai_taunt_history_respects_setting_and_deduplicates():
    async def scenario():
        manager = RoomManager()
        enabled, _ = await manager.create("traditional", "ai", "player")
        await manager._broadcast_ai_taunt(enabled, "opening")
        await manager._broadcast_ai_taunt(enabled, "opening")
        assert len(enabled.chat_history) == 1
        assert enabled.chat_history[0]["automated"] is True

        disabled, _ = await manager.create(
            "traditional", "ai", "player", taunts_enabled=False)
        await manager._broadcast_ai_taunt(disabled, "opening")
        assert disabled.chat_history == []

    asyncio.run(scenario())
