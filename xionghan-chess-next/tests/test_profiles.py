from xionghan_chess.core.game import Game
from xionghan_chess.core.model import PieceType, Position
from xionghan_chess.core.profiles import get_profile


def test_rule_options_can_be_overridden_without_mutating_profile():
    profile = get_profile("web")
    assert profile.options.horse_straight_three_move_only is False
    options = profile.options.merged({"horse_straight_three_move_only": True})
    assert options.horse_straight_three_move_only is True
    assert profile.options.horse_straight_three_move_only is False


def test_archer_enhancement_is_per_profile_and_legacy_switch_is_migrated():
    """射的加强按档案而定：完整/精简=加强版，经典/传统=基础版；旧键仍能迁移。"""
    complete = get_profile("desktop_complete")
    assert complete.options.archer_enhanced_mode is True
    assert get_profile("web").options.archer_enhanced_mode is True
    assert get_profile("desktop_classic").options.archer_enhanced_mode is False

    assert complete.options.merged({"archer_enhanced_mode": False}).archer_enhanced_mode is False
    # 旧键 archer_weak_mode 与 archer_enhanced_mode 语义相反，迁移后必须逐值对应
    assert complete.options.merged({"archer_weak_mode": False}).archer_enhanced_mode is True
    assert complete.options.merged({"archer_weak_mode": True}).archer_enhanced_mode is False


def test_piece_appearance_filters_initial_layout_but_king_is_mandatory():
    game = Game("desktop_complete", {"rook_appear": False, "king_appear": False})
    assert all(piece.type is not PieceType.ROOK for piece in game.state.pieces)
    assert sum(piece.type is PieceType.KING for piece in game.state.pieces) == 2
    assert game.options.king_appear is True


def test_original_desktop_option_names_are_migrated():
    options = get_profile("desktop_complete").options.merged(
        {
            "ju_appear": False,
            "shi_gain_straight_outside_palace": False,
            "xiang_gain_jump_two_outside_river": False,
        }
    )
    assert options.rook_appear is False
    assert options.advisor_gain_straight_outside_palace is False
    assert options.elephant_gain_jump_two_enemy_territory is False


def test_guard_sits_behind_king_and_advisors_flank_it() -> None:
    """开局布局：尉在将**正后方**、士在将两侧各一枚（红 (11,5)/(11,7)）。

    尉 (12,6) 的两条斜线正好被这两只士占住 → 首着 0。**这是刻意的平衡约束**，
    不是缺陷（1.7.4 曾对调成尉 (11,5) 首着 4，用户明确该限制要保留）。
    """
    from xionghan_chess.core.model import Color

    game = Game("desktop_complete")
    rules = game.rules

    def moves_from(row: int, col: int, color: Color) -> int:
        return sum(1 for m in rules.legal_moves(game.state, color) if (m.source.row, m.source.col) == (row, col))

    # 红方：尉在将后 (12,6) 首着 0；士在 (11,5)/(11,7) 各 2 着
    assert game.state.piece_at(Position(12, 6)).type is PieceType.GUARD
    assert game.state.piece_at(Position(11, 5)).type is PieceType.ADVISOR
    assert game.state.piece_at(Position(11, 7)).type is PieceType.ADVISOR
    assert moves_from(12, 6, Color.RED) == 0, "尉开局不该有子可动（强子的平衡约束）"
    assert moves_from(11, 5, Color.RED) == 2
    assert moves_from(11, 7, Color.RED) == 2

    # 黑方镜像逐位对称：尉 (0,6)、士 (1,5)/(1,7)
    assert game.state.piece_at(Position(0, 6)).type is PieceType.GUARD
    assert game.state.piece_at(Position(1, 5)).type is PieceType.ADVISOR
    assert game.state.piece_at(Position(1, 7)).type is PieceType.ADVISOR
    assert moves_from(0, 6, Color.BLACK) == 0
    assert moves_from(1, 5, Color.BLACK) == 2


def test_opening_never_contains_a_type_the_profile_disables() -> None:
    """不变量：开局阵容里不许出现该档 `enabled_piece_types` 之外的棋子。

    F1-a 的由来。`desktop_classic` / `web` 的 (11,5) 曾是一枚 GUARD：95c2784 的
    尉/仕对调**只对启用尉的完整档成立**，而这两档的 enabled 不含 GUARD，于是留下了
    一枚 `moves=0` + `guard_appear=False` 的尉 —— 玩家看不见它，它却真实占格，
    实测各挡掉 4 个合法着（classic 110→114、web 104→108 是"删掉它"的差值），
    同时还顶掉了本该在那里的第二只仕。

    根因不是"坐标写错"，而是 roster 只按 `piece_enabled`（即 `*_appear`）过滤、
    不看 `enabled_piece_types` —— 两套口径各说各话，所以这枚子既被放进 `pieces`
    又被判定"不显示"。因此这里钉的不是坐标，是**集合关系**：
    以后任何 profile 的 `pieces` 与 `enabled_piece_types` 再对不上，这条立刻红。
    """
    for profile_id in ("desktop_complete", "desktop_classic", "web", "traditional"):
        game = Game(profile_id)
        stray = sorted(
            (piece.type.value, piece.position.row, piece.position.col)
            for piece in game.state.pieces
            if piece.type not in game.profile.enabled_piece_types
        )
        assert not stray, (
            f"{profile_id} 开局含该档未启用的棋子：{stray} —— "
            "这类子走不动、又按 *_appear=False 不显示，却真实占格挡住其他子。"
        )


def test_delivery_profiles_have_distinct_piece_sets() -> None:
    """各交付档的初始棋子集必须互不相同（否则"选档案"没有意义）。"""
    sets = {}
    for profile_id in ("desktop_complete", "web", "traditional", "desktop_classic"):
        profile = get_profile(profile_id)
        sets[profile_id] = {(p.type, p.position) for p in profile.initial_pieces()}

    complete = get_profile("desktop_complete")
    assert len(complete.initial_pieces()) == 50, "完整档应为 50 子（每方 25）"

    # 完整与经典**子集相同**（都部署全部 11 型），区别只在规则 —— 这是刻意设计：
    # 用户换模式时只需理解"规则变不变"，不用重新认棋子。
    assert sets["desktop_classic"] == sets["desktop_complete"], "经典模式应与完整模式部署同一批棋子，差异只来自规则"
    assert get_profile("desktop_classic").options != get_profile("desktop_complete").options, (
        "经典模式必须真的把传统棋子回退成经典规则，否则与完整模式没有区别"
    )

    # 精简模式去掉尉/巡，棋子集必须与前两者不同
    assert sets["web"] not in (sets["desktop_complete"], sets["traditional"])
    distinct = {frozenset(v) for k, v in sets.items() if k != "desktop_classic"}
    assert len(distinct) == len(sets) - 1, f"有档案的棋子集重复：{sorted(sets)}"
