from xionghan_chess.core.taunts import TAUNTS, choose_taunt, taunts


def test_taunt_catalog_has_all_scenes_and_random_selection():
    assert set(TAUNTS) == {"opening", "check", "victory", "defeat"}
    assert len(taunts("random")) >= 16
    assert choose_taunt("check", seed=3) in TAUNTS["check"]
