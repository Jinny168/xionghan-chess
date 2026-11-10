"""规则矩阵：11 种棋子 × 3 种对弈模式，逐条压合法/非法/冲突场景。

判据来自 `docs/PIECE_RULES.md`（规则的定义文件），不是从实现反推。
三种模式的规则基线见 `profiles.COMPLETE_OPTIONS` / `CLASSIC_OPTIONS`：

| 维度 | 完整 desktop_complete | 经典 desktop_classic | 精简 web |
|---|---|---|---|
| 棋子 | 11 型 25 枚 | 11 型 25 枚 | 9 型 22 枚 |
| 规则 | 全加强 | 传统棋子回退经典 | 同完整 |

所有局面都用"稀疏局"构造：两王放在对角，避免同列照面把着法全挡掉。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.game import Game, GameState
from xionghan_chess.core.model import Color, Piece, PieceType

RED, BLACK = Color.RED, Color.BLACK
K, R, H, E, A, C, P, G, S, T, X = (
    PieceType.KING,
    PieceType.ROOK,
    PieceType.HORSE,
    PieceType.ELEPHANT,
    PieceType.ADVISOR,
    PieceType.CANNON,
    PieceType.PAWN,
    PieceType.GUARD,
    PieceType.ARCHER,
    PieceType.THUNDER,
    PieceType.PATROL,
)
MODES = ("desktop_complete", "desktop_classic", "web")


def _game(mode: str, placements=(), *, turn: Color = RED, kings=((12, 0), (0, 12)), **options) -> Game:
    pieces = [Piece.create(K, RED, *kings[0]), Piece.create(K, BLACK, *kings[1])]
    pieces += [Piece.create(kind, color, row, col) for kind, color, row, col in placements]
    state = GameState(mode, pieces, turn=turn)
    return Game.from_state(state, option_overrides=options or None)


def _targets(game: Game, source: tuple[int, int]) -> set[tuple[int, int]]:
    return {
        (m.target.row, m.target.col)
        for m in game.rules.legal_moves(game.state)
        if (m.source.row, m.source.col) == source
    }


def _pseudo(game: Game, source: tuple[int, int], target: tuple[int, int]) -> bool:
    from xionghan_chess.core.model import Move, Position

    return game.rules.pseudo_legal(game.state, Move(Position(*source), Position(*target)))


# --- 汉 / 汗（KING）-------------------------------------------------------


@pytest.mark.parametrize("mode,expected", [("desktop_complete", 8), ("desktop_classic", 4), ("web", 8)])
def test_king_inside_palace(mode: str, expected: int) -> None:
    """九宫中心：加强档可斜走（8 向），经典档只有正交 4 向。"""
    assert _targets(_game(mode, [(K, RED, 10, 6)], kings=((12, 0), (0, 12))), (10, 6)) == _palace_ring(expected, 10, 6)


def _palace_ring(count: int, row: int, col: int) -> set[tuple[int, int]]:
    orthogonal = {(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)}
    diagonal = {(row - 1, col - 1), (row - 1, col + 1), (row + 1, col - 1), (row + 1, col + 1)}
    return orthogonal | diagonal if count == 8 else orthogonal


@pytest.mark.parametrize("mode,expect_moves", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_king_may_not_leave_palace_in_classic(mode: str, expect_moves: bool) -> None:
    """宫外的王：加强档仍可走，经典档被"不许出宫"钉死（0 着）。"""
    game = _game(mode, [(K, RED, 6, 6)], kings=((6, 6), (0, 12)))
    assert bool(_targets(game, (6, 6))) is expect_moves


def test_kings_facing_counts_as_check() -> None:
    """同列无遮挡 = 照面，计入被将（这条与模式无关）。"""
    pieces = [Piece.create(K, RED, 5, 6), Piece.create(K, BLACK, 1, 6)]
    state = GameState("desktop_complete", pieces, turn=RED)
    game = Game.from_state(state)
    assert game.rules.in_check(state, RED) is True
    # 中间插一子即解除
    blocked = GameState("desktop_complete", pieces + [Piece.create(P, RED, 3, 6)], turn=RED)
    assert Game.from_state(blocked).rules.in_check(blocked, RED) is False


# --- 车（ROOK）------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_rook_lines_blocking_and_capture(mode: str) -> None:
    game = _game(mode, [(R, RED, 6, 6), (P, RED, 6, 9), (P, BLACK, 3, 6)])
    targets = _targets(game, (6, 6))
    assert (6, 8) in targets, "己子前一格应可走"
    assert (6, 9) not in targets, "不能吃己子 / 不能越子"
    assert (6, 12) not in targets, "被己子挡住后不能越过"
    assert (4, 6) in targets and (3, 6) in targets, "应能沿直线吃敌子"
    assert (2, 6) not in targets, "吃子后不能继续越子"
    assert (5, 5) not in targets, "车不能斜走"


# --- 马（HORSE）-----------------------------------------------------------


@pytest.mark.parametrize("mode,expected", [("desktop_complete", 8), ("desktop_classic", 6), ("web", 8)])
def test_horse_leg_blocking_by_mode(mode: str, expected: int) -> None:
    """右腿被堵：加强档（不别腿）8 着，经典档挡掉两格剩 6 着。"""
    game = _game(mode, [(H, RED, 6, 6), (P, RED, 6, 7)], horse_straight_three=False)
    assert len(_targets(game, (6, 6))) == expected


@pytest.mark.parametrize("mode,allowed", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_horse_straight_three_by_mode(mode: str, allowed: bool) -> None:
    game = _game(mode, [(H, RED, 6, 6)])
    targets = _targets(game, (6, 6))
    assert ((6, 3) in targets) is allowed, "直走三格只在加强档出现"
    assert ((6, 9) in targets) is allowed


@pytest.mark.parametrize("mode", MODES)
def test_horse_straight_three_requires_clear_path(mode: str) -> None:
    game = _game(mode, [(H, RED, 6, 6), (P, RED, 6, 7)])
    assert (6, 9) not in _targets(game, (6, 6)), "三格路径有子即不可走"


def test_horse_move_only_is_explicit_and_blocks_capture() -> None:
    """仅可移动：只在显式开启时生效，且不吃子但空格照走。"""
    base = [(H, RED, 6, 6), (P, BLACK, 6, 9)]
    on = _targets(_game("desktop_complete", base, horse_straight_three_move_only=True), (6, 6))
    off = _targets(_game("desktop_complete", base, horse_straight_three_move_only=False), (6, 6))
    assert (6, 9) not in on and (6, 9) in off
    quiet = _game("desktop_complete", [(H, RED, 6, 6)], horse_straight_three_move_only=True)
    assert (6, 9) in _targets(quiet, (6, 6)), "落点为空时仍可走"


# --- 相 / 象（ELEPHANT）---------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_elephant_eye_blocks_in_every_mode(mode: str) -> None:
    game = _game(mode, [(E, RED, 8, 4), (P, RED, 7, 3)])
    assert (6, 2) not in _targets(game, (8, 4)), "塞象眼必须无效"


@pytest.mark.parametrize("mode,can_cross", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_elephant_river_by_mode(mode: str, can_cross: bool) -> None:
    game = _game(mode, [(E, RED, 7, 5)])
    assert ((5, 3) in _targets(game, (7, 5))) is can_cross


@pytest.mark.parametrize("mode,can_jump", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_elephant_two_step_in_enemy_territory_by_mode(mode: str, can_jump: bool) -> None:
    game = _game(mode, [(E, RED, 5, 5)])
    assert ((5, 7) in _targets(game, (5, 5))) is can_jump


def test_elephant_jump_two_needs_cross_river() -> None:
    """依赖：过河关掉后，"敌境横竖两格"必须是死开关。"""
    game = _game(
        "desktop_complete",
        [(E, RED, 5, 5)],
        elephant_can_cross_river=False,
        elephant_gain_jump_two_enemy_territory=True,
    )
    assert (5, 7) not in _targets(game, (5, 5))


# --- 仕 / 士（ADVISOR）----------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_advisor_inside_palace_is_diagonal_only(mode: str) -> None:
    game = _game(mode, [(A, RED, 10, 6)])
    targets = _targets(game, (10, 6))
    assert targets == {(9, 5), (9, 7), (11, 5), (11, 7)}
    assert (10, 5) not in targets, "九宫内不能直走"


@pytest.mark.parametrize("mode,can_exit", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_advisor_palace_exit_by_mode(mode: str, can_exit: bool) -> None:
    game = _game(mode, [(A, RED, 10, 5)])
    assert ((9, 4) in _targets(game, (10, 5))) is can_exit


@pytest.mark.parametrize(
    "mode,can_straight_outside", [("desktop_complete", True), ("desktop_classic", False), ("web", True)]
)
def test_advisor_straight_outside_palace_by_mode(mode: str, can_straight_outside: bool) -> None:
    game = _game(mode, [(A, RED, 7, 7)])
    assert ((7, 8) in _targets(game, (7, 7))) is can_straight_outside


def test_advisor_straight_needs_palace_exit() -> None:
    """依赖：不能出宫时，"出宫后可直走"必须是死开关。"""
    game = _game(
        "desktop_complete", [(A, RED, 7, 7)], advisor_can_leave_palace=False, advisor_gain_straight_outside_palace=True
    )
    assert (7, 8) not in _targets(game, (7, 7))


# --- 炮（CANNON）----------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_cannon_move_and_capture(mode: str) -> None:
    game = _game(mode, [(C, RED, 6, 6), (P, RED, 6, 8), (P, BLACK, 6, 10)])
    targets = _targets(game, (6, 6))
    assert (6, 7) in targets, "无遮挡可平移"
    assert (6, 8) not in targets, "不能吃己方"
    assert (6, 10) in targets, "隔一子可吃"
    assert (6, 11) not in targets, "隔着屏不能越过吃第二个"
    assert (3, 6) in targets, "无子时直线通行"


@pytest.mark.parametrize("mode", MODES)
def test_cannon_without_screen_cannot_capture(mode: str) -> None:
    game = _game(mode, [(C, RED, 6, 6), (P, BLACK, 6, 10)])
    assert (6, 10) not in _targets(game, (6, 6))


# --- 兵 / 卒（PAWN）-------------------------------------------------------


@pytest.mark.parametrize("mode,can_leap", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_pawn_fast_move_by_mode(mode: str, can_leap: bool) -> None:
    game = _game(mode, [(P, RED, 7, 4)])
    assert ((5, 4) in _targets(game, (7, 4))) is can_leap


@pytest.mark.parametrize("mode", MODES)
def test_pawn_sideways_after_river(mode: str) -> None:
    game = _game(mode, [(P, RED, 5, 4)])
    targets = _targets(game, (5, 4))
    assert (5, 3) in targets and (5, 5) in targets


@pytest.mark.parametrize("mode", MODES)
def test_pawn_on_river_line_cannot_move_sideways(mode: str) -> None:
    """阴山行本身不算敌境：红兵在 row 6 不能横走。"""
    game = _game(mode, [(P, RED, 6, 4)])
    assert (6, 3) not in _targets(game, (6, 4))


@pytest.mark.parametrize("mode", MODES)
def test_pawn_charge_never_swallows_adjacent_capture(mode: str) -> None:
    """冲突回归：冲锋"不吃子"不得吞掉正前方一格的常规吃子。

    改前（`if 落点有子: return False`）升变位的兵无法吃子，连带 in_check 漏判。
    """
    game = _game(mode, [(P, RED, 1, 6), (P, BLACK, 0, 6)], pawn_promotion=False)
    assert _pseudo(game, (1, 6), (0, 6)) is True


@pytest.mark.parametrize("mode", MODES)
def test_pawn_charge_stops_before_piece(mode: str) -> None:
    game = _game(mode, [(P, RED, 5, 3), (P, RED, 3, 3)])
    targets = _targets(game, (5, 3))
    assert (3, 3) not in targets, "不能吃己子"
    assert (4, 3) in targets, "应停在己子前面"


def test_pawn_three_line_capture_is_on_in_complete_off_in_classic() -> None:
    """三连吃子：完整模式默认生效，经典模式默认不生效。"""
    from xionghan_chess.core.model import Move, Position

    placements = [(P, RED, 7, 2), (P, RED, 6, 3), (H, BLACK, 6, 4)]
    move = Move(Position(7, 2), Position(6, 2))
    for mode, should_capture in (("desktop_complete", True), ("desktop_classic", False)):
        game = _game(mode, placements)
        after = game.rules.apply_unchecked(game.state, move, switch_turn=False)
        assert (not any(p.type is H for p in after.pieces)) is should_capture, mode


@pytest.mark.parametrize("mode", MODES)
def test_pawn_at_enemy_base_cannot_step_back_by_default(mode: str) -> None:
    """锁现状：2.0.0 起，兵到对方底线**不再后退**（所有模式一致）。

    产品定稿口径（2.0.0）：`pawn_backward_at_base` 默认关 → 底线兵只剩横走；
    横走由 `crossed` 放行，与本开关无关。旧的 `pawn_full_movement_at_base`
    已整项删除（它在默认配置下不改变任何走法，真正多给的只有"后退"）。
    锁定者：产品（team-lead）；改口径须产品确认，并同步更新本 docstring 与期望值。
    对应需求：兵底线不再"全向"。

    注意：本用例关掉升变才看得到走法 —— 开升变时底线落子必须带 promotion，
    `legal_moves` 会按升变展开，看不出"能不能后退"。
    """
    game = _game(mode, [(P, RED, 0, 4)], pawn_promotion=False)
    assert (1, 4) not in _targets(game, (0, 4)), "默认关：底线兵不能后退"
    assert (0, 3) in _targets(game, (0, 4)), "横走仍在（crossed 放的）"
    # 显式打开开关 → 后退回来（开关本身仍有效，只是默认关）
    back_on = _game(mode, [(P, RED, 0, 4)], pawn_promotion=False, pawn_backward_at_base=True)
    assert (1, 4) in _targets(back_on, (0, 4))


# --- 尉 / 卫（GUARD）------------------------------------------------------


@pytest.mark.parametrize("mode", ("desktop_complete", "desktop_classic"))
def test_guard_diagonal_any_distance_but_never_straight(mode: str) -> None:
    game = _game(mode, [(G, RED, 6, 6)])
    targets = _targets(game, (6, 6))
    assert (2, 2) in targets and (10, 10) in targets, "斜向任意距离"
    assert (6, 5) not in targets and (5, 6) not in targets, "尉不能走直线"


def test_guard_stops_at_first_piece() -> None:
    game = _game("desktop_complete", [(G, RED, 6, 6), (P, BLACK, 8, 8)])
    targets = _targets(game, (6, 6))
    assert (8, 8) in targets, "应能吃到第一枚敌子"
    assert (9, 9) not in targets, "吃到子后不能继续"


# --- 射 / 䠶（ARCHER）-----------------------------------------------------


@pytest.mark.parametrize("mode,free_four", [("desktop_complete", True), ("desktop_classic", False), ("web", True)])
def test_archer_reach_by_mode(mode: str, free_four: bool) -> None:
    """加强档可自由斜走三格；基础档限于同一条星位线段。"""
    game = _game(mode, [(S, RED, 1, 1)])
    targets = _targets(game, (1, 1))
    assert (0, 0) in targets and (3, 3) in targets
    assert ((4, 4) in targets) is free_four


# --- 檑 / 礌（THUNDER）----------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_thunder_captures_only_adjacent(mode: str) -> None:
    game = _game(mode, [(T, RED, 6, 6), (P, BLACK, 4, 4), (P, BLACK, 6, 7)])
    targets = _targets(game, (6, 6))
    assert (6, 7) in targets, "相邻可吃"
    assert (4, 4) not in targets, "不相邻不能吃"


@pytest.mark.parametrize("mode", MODES)
def test_thunder_cannot_capture_protected_piece(mode: str) -> None:
    game = _game(mode, [(T, RED, 6, 6), (P, BLACK, 6, 7), (P, BLACK, 6, 8)])
    assert (6, 7) not in _targets(game, (6, 6)), "目标有四正邻同色保护子时不可吃"


# --- 巡 / 廵（PATROL）-----------------------------------------------------


@pytest.mark.parametrize("mode", ("desktop_complete", "desktop_classic"))
def test_patrol_even_steps_only(mode: str) -> None:
    game = _game(mode, [(X, RED, 6, 6)])
    targets = _targets(game, (6, 6))
    assert (6, 8) in targets and (6, 4) in targets
    assert (6, 7) not in targets, "奇数格不可走"


@pytest.mark.parametrize("mode", ("desktop_complete", "desktop_classic"))
def test_patrol_capture_only_at_distance_two(mode: str) -> None:
    game = _game(mode, [(X, RED, 6, 6), (P, BLACK, 6, 10)])
    targets = _targets(game, (6, 6))
    assert (6, 10) not in targets, "四格外不能吃"
    game2 = _game(mode, [(X, RED, 6, 6), (P, BLACK, 6, 8)])
    assert (6, 8) in _targets(game2, (6, 6)), "隔着两格可以吃"


# --- 模式间关系（结构不变量）----------------------------------------------


@pytest.mark.parametrize(
    "piece,spot",
    [
        (K, (10, 6)),
        (A, (10, 5)),
        (E, (7, 5)),
        (H, (6, 6)),
        (P, (7, 4)),
    ],
)
def test_classic_targets_are_subset_of_complete(piece, spot) -> None:
    """经典模式对传统棋子只会更严：可走集合必须是完整模式的子集。"""
    complete = _targets(_game("desktop_complete", [(piece, RED, *spot)]), spot)
    classic = _targets(_game("desktop_classic", [(piece, RED, *spot)]), spot)
    assert classic <= complete, f"{piece.value} 在经典档出现了完整档没有的着法"


# --- 模式结构不变量（整局级） ---------------------------------------------


def test_no_two_pieces_share_a_square_in_any_mode() -> None:
    for mode in MODES:
        game = Game(mode)
        squares = [(p.position.row, p.position.col) for p in game.state.pieces]
        assert len(squares) == len(set(squares)), f"{mode} 开局有棋子重叠"


def test_every_piece_is_inside_the_board() -> None:
    for mode in MODES:
        game = Game(mode)
        rows, cols = game.profile.rows, game.profile.cols
        for piece in game.state.pieces:
            assert 0 <= piece.position.row < rows and 0 <= piece.position.col < cols, (
                f"{mode} 的 {piece.type.value} 越界：{piece.position}"
            )


def test_opening_position_has_no_side_in_check() -> None:
    """开局不能有一方已被将军——那通常意味着布局把王暴露了。"""
    for mode in MODES:
        game = Game(mode)
        assert game.rules.in_check(game.state, Color.RED) is False, mode
        assert game.rules.in_check(game.state, Color.BLACK) is False, mode


def test_opening_moves_exist_for_the_side_to_move() -> None:
    for mode in MODES:
        game = Game(mode)
        assert len(list(game.rules.legal_moves(game.state))) > 0, f"{mode} 开局无法行棋"


def test_each_mode_can_play_a_deterministic_sequence() -> None:
    """每种模式连走 24 手不抛异常、不出现零合法着法（规则组合的冒烟）。"""
    for mode in MODES:
        game = Game(mode)
        for _ in range(24):
            moves = list(game.rules.legal_moves(game.state))
            if not moves or game.state.finished:
                break
            game.move(moves[0])
        assert len(game.state.history) > 0, f"{mode} 一手都走不了"


def test_piece_roster_matches_the_declared_mode() -> None:
    """棋子构成必须与模式定义一致：完整/经典 11 型 25 枚，精简 9 型 22 枚。"""
    expected = {
        "desktop_complete": {"types": 11, "per_side": 25, "has_guard": True, "has_patrol": True},
        "desktop_classic": {"types": 11, "per_side": 25, "has_guard": True, "has_patrol": True},
        "web": {"types": 9, "per_side": 22, "has_guard": False, "has_patrol": False},
    }
    for mode, spec in expected.items():
        game = Game(mode)
        red = [p for p in game.state.pieces if p.color is Color.RED]
        kinds = {p.type for p in red}
        assert len(kinds) == spec["types"], f"{mode} 兵种数不符"
        assert len(red) == spec["per_side"], f"{mode} 每方枚数不符"
        assert (G in kinds) is spec["has_guard"]
        assert (X in kinds) is spec["has_patrol"]
