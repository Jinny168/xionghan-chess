from xionghan_chess.core.model import PieceType
from xionghan_chess.core.game import Game
from xionghan_chess.core.profiles import get_profile


def test_delivery_profiles_have_distinct_piece_sets():
    complete = get_profile("desktop_complete")
    web = get_profile("web")
    traditional = get_profile("traditional")

    assert len(complete.initial_pieces()) == 62
    assert PieceType.SHIELD in complete.enabled_piece_types
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
