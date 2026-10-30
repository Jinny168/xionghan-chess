from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import RulesEngine


def state(*pieces, turn=Color.RED, profile="desktop_complete"):
    return GameState(profile, list(pieces), turn=turn)


def piece(kind, color, row, col):
    return Piece.create(kind, color, row, col)


def kings():
    return piece(PieceType.KING, Color.RED, 11, 6), piece(PieceType.KING, Color.BLACK, 1, 5)


def test_king_can_leave_palace_when_enabled():
    red, black = kings()
    board = state(red, black)
    move = Move(red.position, Position(12, 6))
    assert RulesEngine(get_profile("desktop_complete")).is_legal(board, move)
    assert not RulesEngine(get_profile("desktop_complete"),
                           get_profile("desktop_complete").options.merged({"king_can_leave_palace": False})).is_legal(board, move)


def test_shield_can_be_captured_when_unprotected():
    """楯不再是绝对免疫：没有同阵营楯四正相贴时可以吃。"""
    red, black = kings()
    rook = piece(PieceType.ROOK, Color.RED, 6, 0)
    shield = piece(PieceType.SHIELD, Color.BLACK, 6, 3)
    board = state(red, black, rook, shield)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert rules.is_legal(board, Move(rook.position, shield.position))


def test_shield_protects_only_orthogonally_adjacent_pieces():
    """保护收窄到**四正**：正侧相邻能护住，斜贴不算。"""
    red, black = kings()
    rules = RulesEngine(get_profile("desktop_complete"))

    # 四正：楯在 (6,2)，被吃的子在 (6,3) → 护住
    ortho = state(red, black, piece(PieceType.ROOK, Color.RED, 6, 0),
                  piece(PieceType.SHIELD, Color.BLACK, 6, 2),
                  piece(PieceType.PAWN, Color.BLACK, 6, 3))
    assert not rules.is_legal(ortho, Move(Position(6, 0), Position(6, 3)))

    # 斜贴：楯在 (5,2)，被吃的子在 (6,3) → 不护
    diagonal = state(red, black, piece(PieceType.ROOK, Color.RED, 6, 0),
                     piece(PieceType.SHIELD, Color.BLACK, 5, 2),
                     piece(PieceType.PAWN, Color.BLACK, 6, 3))
    assert rules.is_legal(diagonal, Move(Position(6, 0), Position(6, 3)))


def test_shield_does_not_protect_another_shield():
    """例外：楯不保护楯 —— 否则两楯四正相邻会成对无敌。"""
    red, black = kings()
    rules = RulesEngine(get_profile("desktop_complete"))
    # 保护者在 (5,3)，不在攻击路径上；目标楯在 (6,3)
    board = state(red, black, piece(PieceType.ROOK, Color.RED, 6, 0),
                  piece(PieceType.SHIELD, Color.BLACK, 5, 3),
                  piece(PieceType.SHIELD, Color.BLACK, 6, 3))
    assert rules.is_legal(board, Move(Position(6, 0), Position(6, 3))), "楯不保护楯，应可吃"
    # 但非楯的子仍然受四正保护
    guarded = state(red, black, piece(PieceType.ROOK, Color.RED, 6, 0),
                    piece(PieceType.SHIELD, Color.BLACK, 5, 3),
                    piece(PieceType.PAWN, Color.BLACK, 6, 3))
    assert not rules.is_legal(guarded, Move(Position(6, 0), Position(6, 3)))


def test_assassin_walks_one_step_and_captures_diagonally():
    red, black = kings()
    assassin = piece(PieceType.ASSASSIN, Color.RED, 6, 4)
    victim = piece(PieceType.HORSE, Color.BLACK, 8, 2)   # 斜向两格；且不会将军红王（含直三马腿）
    board = state(red, black, assassin, victim)
    rules = RulesEngine(get_profile("desktop_complete"))

    # 走：只前进一格
    assert rules.is_legal(board, Move(assassin.position, Position(5, 4)))
    # 走不能横向、也不能一次两格
    assert not rules.is_legal(board, Move(assassin.position, Position(6, 5)))
    assert not rules.is_legal(board, Move(assassin.position, Position(4, 4)))
    # 吃：斜向任意距离；落子后目标消失，且**自己不会同归于尽**
    capture = Move(assassin.position, victim.position)
    assert rules.is_legal(board, capture)
    after = rules.apply_unchecked(board, capture)
    assert after.piece_at(victim.position) is not None
    assert after.piece_at(victim.position).type is PieceType.ASSASSIN
    # 直线上的敌子吃不到（只能走空点）
    straight = state(red, black, piece(PieceType.ASSASSIN, Color.RED, 6, 4),
                     piece(PieceType.HORSE, Color.BLACK, 6, 7))
    assert not rules.is_legal(straight, Move(Position(6, 4), Position(6, 7)))


def test_armor_moves_one_step_but_runs_like_a_rook_forward():
    red, black = kings()
    armor = piece(PieceType.ARMOR, Color.RED, 6, 3)
    board = state(red, black, armor)
    rules = RulesEngine(get_profile("desktop_complete"))

    # 前方：车式，多格都可（(4,3)、(2,3)）
    assert rules.is_legal(board, Move(armor.position, Position(4, 3)))
    assert rules.is_legal(board, Move(armor.position, Position(2, 3)))
    # 侧、后：只有一格
    assert rules.is_legal(board, Move(armor.position, Position(6, 4)))
    assert rules.is_legal(board, Move(armor.position, Position(7, 3)))
    assert not rules.is_legal(board, Move(armor.position, Position(6, 5)))
    assert not rules.is_legal(board, Move(armor.position, Position(8, 3)))
    # 仍不能吃子：前方有敌子时既不能前进也不能吃
    blocked = state(red, black, piece(PieceType.ARMOR, Color.RED, 6, 3),
                    piece(PieceType.PAWN, Color.BLACK, 3, 3))
    # 敌子在 (3,3)：甲**不能吃**，但可以走到它前面的 (4,3)
    assert not rules.is_legal(blocked, Move(Position(6, 3), Position(3, 3)))
    assert rules.is_legal(blocked, Move(Position(6, 3), Position(4, 3)))


def test_armor_three_piece_line_captures_enemy():
    """三连移除保持不变（甲只是"移动"，三连是走完后全盘结算）。"""
    red, black = kings()
    armor = piece(PieceType.ARMOR, Color.RED, 6, 5)
    ally = piece(PieceType.PAWN, Color.RED, 6, 3)
    enemy = piece(PieceType.HORSE, Color.BLACK, 6, 2)
    board = state(red, black, armor, ally, enemy)
    rules = RulesEngine(get_profile("desktop_complete"))
    move = Move(armor.position, Position(6, 4))
    assert rules.is_legal(board, move)
    result = rules.apply_unchecked(board, move)
    assert result.piece_at(enemy.position) is None
    assert rules.captured_by_move(board, move) == (enemy,)


def test_archer_captures_through_blockers_but_moves_only_on_clear_path():
    """射：吃子无视阻挡；位移仍要求路径无子（射程/星点/夹逼不变）。"""
    red, black = kings()
    rules = RulesEngine(get_profile("desktop_complete"))

    one = state(red, black, piece(PieceType.ARCHER, Color.RED, 0, 0),
                piece(PieceType.PAWN, Color.RED, 1, 1),
                piece(PieceType.HORSE, Color.BLACK, 3, 3))
    assert rules.is_legal(one, Move(Position(0, 0), Position(3, 3))), "隔 1 子应能吃到"
    assert not rules.is_legal(one, Move(Position(0, 0), Position(2, 2))), "空着位移被挡应非法"

    two = state(red, black, piece(PieceType.ARCHER, Color.RED, 0, 0),
                piece(PieceType.PAWN, Color.RED, 1, 1),
                piece(PieceType.PAWN, Color.RED, 2, 2),
                piece(PieceType.HORSE, Color.BLACK, 3, 3))
    assert rules.is_legal(two, Move(Position(0, 0), Position(3, 3))), "隔 2 子也应能吃到"
    assert not rules.is_legal(two, Move(Position(0, 0), Position(1, 1))), "己方子所在格不能落"


def test_pawn_charge_is_opt_in_and_never_captures():
    """兵冲锋：开关默认关；开启后过阴山可直线多格，但不吃子、遇子即停。"""
    red, black = kings()
    profile = get_profile("desktop_complete")
    on = RulesEngine(profile, profile.options.merged({"pawn_charge": True}))
    off = RulesEngine(profile)

    pawn = piece(PieceType.PAWN, Color.RED, 5, 3)
    board = state(red, black, pawn)
    assert on.is_legal(board, Move(Position(5, 3), Position(2, 3))), "过阴山后可冲锋多格"
    assert off.is_legal(board, Move(Position(5, 3), Position(2, 3))) is False, "默认关不应生效"

    # 未过阴山（row 6 是阴山行本身）不冲锋
    middle = state(red, black, piece(PieceType.PAWN, Color.RED, 6, 3))
    assert on.is_legal(middle, Move(Position(6, 3), Position(3, 3))) is False

    # 路径有子：只能走到子前面
    blocked = state(red, black, piece(PieceType.PAWN, Color.RED, 5, 3),
                    piece(PieceType.PAWN, Color.RED, 4, 3))
    assert on.is_legal(blocked, Move(Position(5, 3), Position(2, 3))) is False
    assert on.is_legal(blocked, Move(Position(5, 3), Position(4, 3))) is False

    # 目标有子：冲锋不吃子
    occupied = state(red, black, piece(PieceType.PAWN, Color.RED, 5, 3),
                     piece(PieceType.HORSE, Color.BLACK, 2, 3))
    assert on.is_legal(occupied, Move(Position(5, 3), Position(2, 3))) is False


def test_pawn_three_line_capture_is_opt_in():
    """兵参与三连吃子：默认关；开启后「两枚己方兵 + 一枚敌子成线」吃掉敌子。"""
    red, black = kings()
    profile = get_profile("desktop_complete")
    on = RulesEngine(profile, profile.options.merged({"pawn_three_line_capture": True}))
    off = RulesEngine(profile)

    board = state(red, black, piece(PieceType.PAWN, Color.RED, 7, 2),
                  piece(PieceType.PAWN, Color.RED, 6, 3),
                  piece(PieceType.HORSE, Color.BLACK, 6, 4))
    move = Move(Position(7, 2), Position(6, 2))          # 落到 (6,2) 后成 6,2/6,3/6,4 三连
    assert on.is_legal(board, move)
    after = on.apply_unchecked(board, move, switch_turn=False)
    assert not any(p.type is PieceType.HORSE for p in after.pieces), "开启三连应吃掉敌子"

    after_off = off.apply_unchecked(board, move, switch_turn=False)
    assert any(p.type is PieceType.HORSE for p in after_off.pieces), "默认关不应触发"


def test_patrol_moves_four_ways_and_captures_at_distance_two():
    red, black = kings()
    patrol = piece(PieceType.PATROL, Color.RED, 6, 6)
    victim = piece(PieceType.PAWN, Color.BLACK, 6, 9)
    board = state(red, black, patrol, victim)
    rules = RulesEngine(get_profile("desktop_complete"))

    # 横竖都行（不再限制在 5/7 行），偶数格
    assert rules.is_legal(board, Move(patrol.position, Position(6, 4)))
    assert rules.is_legal(board, Move(patrol.position, Position(2, 6)))
    assert not rules.is_legal(board, Move(patrol.position, Position(6, 5)))   # 奇数格不行
    # 吃子仅限距离 2
    assert rules.is_legal(board, Move(patrol.position, Position(6, 8)))       # 走空点
    assert not rules.is_legal(board, Move(patrol.position, Position(6, 9)))   # 距离 3 吃不到
    near = state(red, black, piece(PieceType.PATROL, Color.RED, 6, 6),
                 piece(PieceType.PAWN, Color.BLACK, 6, 8))
    assert rules.is_legal(near, Move(Position(6, 6), Position(6, 8)))         # 距离 2 可吃


def test_promotion_requires_captured_allowed_piece():
    red, black = kings()
    pawn = piece(PieceType.PAWN, Color.RED, 1, 0)
    dead_rook = piece(PieceType.ROOK, Color.RED, 5, 5)
    board = state(red, black, pawn)
    board.captured[Color.RED].append(dead_rook)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert not rules.is_legal(board, Move(pawn.position, Position(0, 0)))
    promoted = Move(pawn.position, Position(0, 0), PieceType.ROOK)
    assert rules.is_legal(board, promoted)
    result = rules.apply_unchecked(board, promoted)
    assert result.piece_at(Position(0, 0)).type is PieceType.ROOK


def test_legal_moves_enumerate_required_promotion_choices():
    red, black = kings()
    pawn = piece(PieceType.PAWN, Color.RED, 1, 0)
    board = state(red, black, pawn)
    board.captured[Color.RED].extend([
        piece(PieceType.ROOK, Color.RED, 5, 5),
        piece(PieceType.HORSE, Color.RED, 5, 6),
    ])
    moves = [move for move in RulesEngine(get_profile("desktop_complete")).legal_moves(board)
             if move.source == pawn.position and move.target == Position(0, 0)]
    assert {move.promotion for move in moves} == {PieceType.ROOK, PieceType.HORSE}
    assert all(move.promotion is not None for move in moves)


def test_game_undo_restores_authoritative_snapshot():
    game = Game("traditional")
    move = next(iter(game.rules.legal_moves(game.state)))
    original = game.state.to_dict()
    game.move(move)
    game.undo()
    assert game.state.to_dict()["pieces"] == original["pieces"]
    assert game.state.turn is Color.RED


def test_king_outside_palace_diagonal_is_independently_configurable():
    red = piece(PieceType.KING, Color.RED, 8, 6)
    black = piece(PieceType.KING, Color.BLACK, 1, 5)
    board = state(red, black)
    move = Move(red.position, Position(7, 7))
    profile = get_profile("desktop_complete")
    assert not RulesEngine(profile).pseudo_legal(board, move)
    options = profile.options.merged({"king_lose_diagonal_outside_palace": False})
    assert RulesEngine(profile, options).pseudo_legal(board, move)


def test_advisor_straight_move_only_applies_outside_palace_when_enabled():
    red, black = kings()
    advisor = piece(PieceType.ADVISOR, Color.RED, 8, 4)
    board = state(red, black, advisor)
    move = Move(advisor.position, Position(8, 5))
    profile = get_profile("desktop_complete")
    assert RulesEngine(profile).pseudo_legal(board, move)
    options = profile.options.merged({"advisor_gain_straight_outside_palace": False})
    assert not RulesEngine(profile, options).pseudo_legal(board, move)


def test_elephant_enemy_territory_orthogonal_move_is_independently_configurable():
    red, black = kings()
    elephant = piece(PieceType.ELEPHANT, Color.RED, 5, 4)
    board = state(red, black, elephant)
    move = Move(elephant.position, Position(5, 6))
    profile = get_profile("desktop_complete")
    assert RulesEngine(profile).pseudo_legal(board, move)
    options = profile.options.merged({"elephant_gain_jump_two_enemy_territory": False})
    assert not RulesEngine(profile, options).pseudo_legal(board, move)


def test_disabled_piece_type_cannot_be_used_for_promotion():
    red, black = kings()
    pawn = piece(PieceType.PAWN, Color.RED, 1, 0)
    dead_rook = piece(PieceType.ROOK, Color.RED, 5, 5)
    board = state(red, black, pawn)
    board.captured[Color.RED].append(dead_rook)
    profile = get_profile("desktop_complete")
    options = profile.options.merged({"rook_appear": False})
    assert not RulesEngine(profile, options).is_legal(
        board, Move(pawn.position, Position(0, 0), PieceType.ROOK)
    )


def test_archer_default_mode_uses_next_diagonal_star_as_boundary():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 3, 3)
    board = state(red, black, archer)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert rules.pseudo_legal(board, Move(archer.position, Position(6, 6)))
    assert not rules.pseudo_legal(board, Move(archer.position, Position(7, 7)))


def test_archer_default_mode_connects_corner_to_adjacent_star():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 0, 0)
    board = state(red, black, archer)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert rules.pseudo_legal(board, Move(archer.position, Position(3, 3)))
    assert not rules.pseudo_legal(board, Move(archer.position, Position(4, 4)))


def test_archer_default_mode_stays_inside_one_valid_star_segment():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 1, 1)
    board = state(red, black, archer)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert rules.pseudo_legal(board, Move(archer.position, Position(0, 0)))
    assert rules.pseudo_legal(board, Move(archer.position, Position(3, 3)))
    assert not rules.pseudo_legal(board, Move(archer.position, Position(4, 4)))


def test_archer_invalid_star_is_not_a_strong_mode_attack_origin():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 0, 3)
    enemy = piece(PieceType.HORSE, Color.BLACK, 1, 4)
    board = state(red, black, archer, enemy)
    profile = get_profile("desktop_complete")
    rules = RulesEngine(profile, profile.options.merged({"archer_enhanced_mode": True}))
    assert not rules.pseudo_legal(board, Move(archer.position, enemy.position))


def test_archer_star_visuals_follow_piece_appearance_setting():
    profile = get_profile("desktop_complete")
    disabled = profile.options.merged({"archer_appear": False})
    assert not RulesEngine(profile, disabled).archer_star_points


def test_archer_star_points_are_thirteen_diamonds_not_twenty_five():
    # Audit item C-2. The three live paths already agree — `rules.py` filters
    # with `(row // 3 + col // 3) % 2 == 0` (13 points), `web/js/app.js`
    # `drawStarPoints` paints whatever `profile.archerStarPoints` carries, and
    # `offline.js` `starPoints()` mirrors the same condition. The only file that
    # still spells out the pre-migration 25 points (`row` and `col` both
    # multiples of 3) is the legacy `web/js/core/game-rules.js`, which the
    # running service never mounts — so it is pinned by this test instead of by
    # editing a file that cannot reach a browser.
    lattice = {(r, c) for r in range(0, 13, 3) for c in range(0, 13, 3) if (r // 3 + c // 3) % 2 == 0}
    assert len(lattice) == 13
    expected = frozenset(Position(row, col) for row, col in lattice)
    assert RulesEngine(get_profile("desktop_complete")).archer_star_points == expected


# --------------------------------------------------------------------------
# R-3: patrol (巡) was the only one of the 14 piece types with no direct
# coverage at all.
# --------------------------------------------------------------------------

def _patrol_board(*extra, row=5, col=0, profile="desktop_complete"):
    return state(*kings(), piece(PieceType.PATROL, Color.RED, row, col), *extra, profile=profile)


def _patrol_move(rules, board, row, col):
    source = next(p.position for p in board.pieces if p.type is PieceType.PATROL)
    return rules.pseudo_legal(board, Move(source, Position(row, col)))


def test_patrol_steps_an_even_number_of_columns_along_its_home_row():
    rules = RulesEngine(get_profile("desktop_complete"))
    board = _patrol_board()
    assert _patrol_move(rules, board, 5, 2)
    assert _patrol_move(rules, board, 5, 4)


def test_patrol_accepts_both_home_rows():
    rules = RulesEngine(get_profile("desktop_complete"))
    assert _patrol_move(rules, _patrol_board(row=5), 5, 2)
    assert _patrol_move(rules, _patrol_board(row=7), 7, 2)


def test_patrol_rejects_odd_distances_and_staying_put():
    rules = RulesEngine(get_profile("desktop_complete"))
    board = _patrol_board()
    assert not _patrol_move(rules, board, 5, 1)
    assert not _patrol_move(rules, board, 5, 3)
    assert not _patrol_move(rules, board, 5, 0)


def test_patrol_rejects_leaving_its_home_row():
    rules = RulesEngine(get_profile("desktop_complete"))
    board = _patrol_board()
    assert not _patrol_move(rules, board, 4, 2)
    assert not _patrol_move(rules, board, 6, 2)
    # Even staying on a legal column is not enough if the row changes.
    assert not _patrol_move(rules, board, 4, 0)


def test_patrol_rejects_a_blocked_path():
    rules = RulesEngine(get_profile("desktop_complete"))
    board = _patrol_board(piece(PieceType.PAWN, Color.RED, 5, 2))
    assert not _patrol_move(rules, board, 5, 4)


def test_patrol_captures_two_columns_away_but_not_four():
    rules = RulesEngine(get_profile("desktop_complete"))
    near = _patrol_board(piece(PieceType.PAWN, Color.BLACK, 5, 2))
    assert _patrol_move(rules, near, 5, 2)
    far = _patrol_board(piece(PieceType.PAWN, Color.BLACK, 5, 4))
    assert not _patrol_move(rules, far, 5, 4)


def test_traditional_profile_has_no_patrol():
    rules = RulesEngine(get_profile("traditional"))
    board = state(piece(PieceType.KING, Color.RED, 9, 4),
                  piece(PieceType.PATROL, Color.RED, 5, 0),
                  piece(PieceType.KING, Color.BLACK, 0, 4),
                  profile="traditional")
    assert not _patrol_move(rules, board, 5, 2)


def test_pawn_fast_move_reaches_enemy_territory_edge_but_does_not_cross_it():
    red, black = kings()
    pawn = piece(PieceType.PAWN, Color.RED, 8, 0)
    board = state(red, black, pawn)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert rules.pseudo_legal(board, Move(pawn.position, Position(5, 0)))
    assert not rules.pseudo_legal(board, Move(pawn.position, Position(4, 0)))

    black_pawn = piece(PieceType.PAWN, Color.BLACK, 4, 2)
    black_board = state(red, black, black_pawn, turn=Color.BLACK)
    assert rules.pseudo_legal(black_board, Move(black_pawn.position, Position(7, 2)))
    assert not rules.pseudo_legal(black_board, Move(black_pawn.position, Position(8, 2)))


def test_pawn_fast_move_cannot_capture_or_jump_and_can_be_disabled():
    red, black = kings()
    pawn = piece(PieceType.PAWN, Color.RED, 8, 0)
    target = piece(PieceType.HORSE, Color.BLACK, 6, 0)
    blocker = piece(PieceType.CANNON, Color.BLACK, 7, 2)
    profile = get_profile("desktop_complete")
    rules = RulesEngine(profile)
    target = piece(PieceType.HORSE, Color.BLACK, 5, 0)
    assert not rules.pseudo_legal(state(red, black, pawn, target),
                                  Move(pawn.position, target.position))
    blocked_pawn = piece(PieceType.PAWN, Color.RED, 8, 2)
    assert not rules.pseudo_legal(state(red, black, blocked_pawn, blocker),
                                  Move(blocked_pawn.position, Position(5, 2)))
    disabled = RulesEngine(profile, profile.options.merged({
        "pawn_fast_move_before_enemy_territory": False,
    }))
    assert not disabled.pseudo_legal(board := state(red, black, pawn),
                                     Move(pawn.position, Position(5, 0)))


def test_archer_strong_mode_allows_empty_three_step_move_but_attack_requires_star():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 4, 4)
    enemy = piece(PieceType.HORSE, Color.BLACK, 5, 5)
    board = state(red, black, archer)
    profile = get_profile("desktop_complete")
    strong = profile.options.merged({"archer_enhanced_mode": True})
    rules = RulesEngine(profile, strong)
    assert rules.pseudo_legal(board, Move(archer.position, Position(7, 7)))
    attack_board = state(red, black, archer, enemy)
    assert not rules.pseudo_legal(attack_board, Move(archer.position, enemy.position))
    star_archer = piece(PieceType.ARCHER, Color.RED, 3, 3)
    star_board = state(red, black, star_archer, enemy)
    assert rules.pseudo_legal(star_board, Move(star_archer.position, enemy.position))


def test_archer_origin_and_path_pinch_are_both_rejected():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 3, 3)
    origin_board = state(red, black, archer,
                        piece(PieceType.PAWN, Color.BLACK, 3, 4),
                        piece(PieceType.PAWN, Color.BLACK, 4, 3))
    rules = RulesEngine(get_profile("desktop_complete"))
    assert not rules.pseudo_legal(origin_board, Move(archer.position, Position(6, 6)))
    path_board = state(red, black, archer,
                       piece(PieceType.PAWN, Color.BLACK, 4, 5),
                       piece(PieceType.PAWN, Color.BLACK, 5, 4))
    assert not rules.pseudo_legal(path_board, Move(archer.position, Position(6, 6)))


def test_archer_screenshot_position_allows_upper_left_star_but_not_pinched_lower_right():
    red, black = kings()
    archer = piece(PieceType.ARCHER, Color.RED, 9, 9)
    thunder = piece(PieceType.THUNDER, Color.RED, 9, 10)
    rook = piece(PieceType.ROOK, Color.RED, 10, 9)
    board = state(red, black, archer, thunder, rook)
    profile = get_profile("desktop_complete")

    for enhanced in (False, True):
        rules = RulesEngine(profile, profile.options.merged({
            "archer_enhanced_mode": enhanced,
        }))
        assert rules.pseudo_legal(board, Move(archer.position, Position(6, 6)))
        for target in (Position(10, 10), Position(11, 11), Position(12, 12)):
            assert not rules.pseudo_legal(board, Move(archer.position, target))


def test_diagonal_pinch_applies_to_elephant_advisor_and_king():
    profile = get_profile("desktop_complete")
    red, black = kings()

    elephant = piece(PieceType.ELEPHANT, Color.RED, 3, 3)
    elephant_board = state(red, black, elephant,
                           piece(PieceType.PAWN, Color.BLACK, 4, 5),
                           piece(PieceType.PAWN, Color.BLACK, 5, 4))
    assert not RulesEngine(profile).pseudo_legal(
        elephant_board, Move(elephant.position, Position(5, 5))
    )

    advisor = piece(PieceType.ADVISOR, Color.RED, 10, 6)
    advisor_board = state(red, black, advisor,
                          piece(PieceType.PAWN, Color.BLACK, 10, 7),
                          piece(PieceType.PAWN, Color.BLACK, 11, 6))
    assert not RulesEngine(profile).pseudo_legal(
        advisor_board, Move(advisor.position, Position(11, 7))
    )

    king = piece(PieceType.KING, Color.RED, 10, 6)
    king_board = state(king, black,
                       piece(PieceType.PAWN, Color.BLACK, 10, 7),
                       piece(PieceType.PAWN, Color.BLACK, 11, 6))
    assert not RulesEngine(profile).pseudo_legal(
        king_board, Move(king.position, Position(11, 7))
    )


def test_diagonal_pinch_applies_to_guard_and_thunder_paths():
    profile = get_profile("desktop_complete")
    red, black = kings()
    pinch_a = piece(PieceType.PAWN, Color.BLACK, 3, 4)
    pinch_b = piece(PieceType.PAWN, Color.BLACK, 4, 3)

    guard = piece(PieceType.GUARD, Color.RED, 3, 3)
    screen = piece(PieceType.PAWN, Color.RED, 5, 5)
    guard_board = state(red, black, guard, screen, pinch_a, pinch_b)
    assert not RulesEngine(profile).pseudo_legal(
        guard_board, Move(guard.position, Position(6, 6))
    )

    thunder = piece(PieceType.THUNDER, Color.RED, 3, 3)
    thunder_board = state(red, black, thunder, pinch_a, pinch_b)
    assert not RulesEngine(profile).pseudo_legal(
        thunder_board, Move(thunder.position, Position(6, 6))
    )


# ---------------------------------------------------------------------------
# has_any_legal_move：与 `bool(legal_moves(...))` 必须逐局面等价
# ---------------------------------------------------------------------------
def test_has_any_legal_move_matches_legal_moves():
    """短路版与全量枚举必须给出同一个布尔值（`_settle` 依赖它判困毙/将死）。"""
    for profile in ("desktop_complete", "desktop_classic", "web", "traditional"):
        game = Game(profile)
        for _ in range(4):
            for color in (Color.RED, Color.BLACK):
                assert (game.rules.has_any_legal_move(game.state, color)
                        == bool(game.rules.legal_moves(game.state, color))), profile
            legal = game.rules.legal_moves(game.state)
            if not legal:
                break
            game.move(legal[0])
