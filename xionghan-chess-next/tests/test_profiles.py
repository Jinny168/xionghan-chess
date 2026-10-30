from xionghan_chess.core.model import PieceType
from xionghan_chess.core.game import Game
from xionghan_chess.core.profiles import get_profile, profile_rule_values


def test_delivery_profiles_have_distinct_piece_sets():
    complete = get_profile("desktop_complete")
    web = get_profile("web")
    traditional = get_profile("traditional")

    # 软删甲/楯后：完整档 62 → 54 子（每方 27）；两者不在初始布局里，且默认 `*_appear` 为 False。
    # 注意 `enabled_piece_types` 仍是"该档**可以**出场的类型集合"（含甲/楯），
    # 这样把 `armor_appear` 打开就能回滚，规则分支也仍可被测试覆盖。
    assert len(complete.initial_pieces()) == 54
    assert PieceType.SHIELD not in {p.type for p in complete.initial_pieces()}
    assert PieceType.ARMOR not in {p.type for p in complete.initial_pieces()}
    assert complete.options.piece_enabled(PieceType.ARMOR) is False
    assert complete.options.piece_enabled(PieceType.SHIELD) is False
    assert PieceType.SHIELD not in web.enabled_piece_types
    assert PieceType.ARCHER in web.enabled_piece_types
    assert traditional.rows == 10 and traditional.cols == 9
    assert traditional.enabled_piece_types == {
        PieceType.KING, PieceType.ROOK, PieceType.HORSE, PieceType.ELEPHANT,
        PieceType.ADVISOR, PieceType.CANNON, PieceType.PAWN,
    }


def test_rule_options_can_be_overridden_without_mutating_profile():
    profile = get_profile("web")
    options = profile.options.merged({"pawn_resurrection": True})
    assert options.pawn_resurrection is True
    assert profile.options.pawn_resurrection is False


def test_archer_defaults_to_weak_mode_and_legacy_switch_is_migrated():
    profile = get_profile("desktop_complete")
    assert profile.options.archer_enhanced_mode is False
    assert profile.options.merged({"archer_enhanced_mode": True}).archer_enhanced_mode is True
    assert profile.options.merged({"archer_weak_mode": False}).archer_enhanced_mode is True
    assert profile.options.merged({"archer_weak_mode": True}).archer_enhanced_mode is False


def test_piece_appearance_filters_initial_layout_but_king_is_mandatory():
    game = Game("desktop_complete", {"rook_appear": False, "king_appear": False})
    assert all(piece.type is not PieceType.ROOK for piece in game.state.pieces)
    assert sum(piece.type is PieceType.KING for piece in game.state.pieces) == 2
    assert game.options.king_appear is True


def test_original_desktop_option_names_are_migrated():
    options = get_profile("desktop_complete").options.merged({
        "ju_appear": False,
        "shi_gain_straight_outside_palace": False,
        "xiang_gain_jump_two_outside_river": False,
    })
    assert options.rook_appear is False
    assert options.advisor_gain_straight_outside_palace is False
    assert options.elephant_gain_jump_two_enemy_territory is False


def test_profile_rule_values_do_not_leak_traditional_piece_disabling():
    traditional = profile_rule_values("traditional")
    complete = profile_rule_values("desktop_complete")

    assert not traditional["archer_appear"]
    assert not traditional["thunder_appear"]
    assert not traditional["armor_appear"]
    assert complete["archer_appear"]
    assert complete["thunder_appear"]
    assert not complete["armor_appear"], "甲已软删：完整档也不再出场"
