from xionghan_chess.core.model import PieceType, Position
from xionghan_chess.core.game import Game
from xionghan_chess.core.profiles import get_profile, profile_rule_values




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




def test_guard_and_advisor_are_swapped_at_the_opening() -> None:
    """尉与仕对调（红 (11,5)↔(12,6)，黑镜像 (1,5)↔(0,6)）。

    尉改成标准主教后，原来的 (12,6) 两侧斜格被两只仕同时占死、首着 0；
    对调后尉首着 4，且仕/檑/王的首着数一格不变。
    """
    from xionghan_chess.core.model import Color

    game = Game("desktop_complete")
    rules = game.rules

    def moves_from(row: int, col: int, color: Color) -> int:
        return sum(1 for m in rules.legal_moves(game.state, color)
                   if (m.source.row, m.source.col) == (row, col))

    # 红方：尉在 (11,5) 有 4 着；仕在 (12,6) 与 (11,7) 各 2 着
    assert game.state.piece_at(Position(11, 5)).type is PieceType.GUARD
    assert game.state.piece_at(Position(12, 6)).type is PieceType.ADVISOR
    assert moves_from(11, 5, Color.RED) == 4
    assert moves_from(12, 6, Color.RED) == 2
    assert moves_from(11, 7, Color.RED) == 2

    # 黑方镜像逐位对称：(1,5) 是尉、(0,6) 是仕
    assert game.state.piece_at(Position(1, 5)).type is PieceType.GUARD
    assert game.state.piece_at(Position(0, 6)).type is PieceType.ADVISOR
    assert moves_from(1, 5, Color.BLACK) == 4
    assert moves_from(0, 6, Color.BLACK) == 2


def test_delivery_profiles_have_distinct_piece_sets() -> None:
    """各交付档的初始棋子集必须互不相同（否则"选档案"没有意义）。"""
    sets = {}
    for profile_id in ("desktop_complete", "web", "traditional", "desktop_classic"):
        profile = get_profile(profile_id)
        sets[profile_id] = {(p.type, p.position) for p in profile.initial_pieces()}

    complete = get_profile("desktop_complete")
    assert len(complete.initial_pieces()) == 50, "完整档应为 50 子（每方 25）"

    distinct = {frozenset(v) for v in sets.values()}
    assert len(distinct) == len(sets), f"有档案的棋子集重复：{sorted(sets)}"
