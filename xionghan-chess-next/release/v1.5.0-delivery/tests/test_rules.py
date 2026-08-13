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


def test_shield_cannot_be_captured_and_protects_adjacent_piece():
    red, black = kings()
    rook = piece(PieceType.ROOK, Color.RED, 6, 0)
    shield = piece(PieceType.SHIELD, Color.BLACK, 6, 3)
    pawn = piece(PieceType.PAWN, Color.BLACK, 6, 4)
    board = state(red, black, rook, shield, pawn)
    rules = RulesEngine(get_profile("desktop_complete"))
    assert not rules.is_legal(board, Move(rook.position, shield.position))
    assert not rules.is_legal(board, Move(rook.position, pawn.position))


def test_assassin_exchange_removes_both_pieces():
    red, black = kings()
    assassin = piece(PieceType.ASSASSIN, Color.RED, 6, 4)
    victim = piece(PieceType.HORSE, Color.BLACK, 6, 3)
    board = state(red, black, assassin, victim)
    rules = RulesEngine(get_profile("desktop_complete"))
    move = Move(assassin.position, Position(6, 5))
    assert rules.is_legal(board, move)
    result = rules.apply_unchecked(board, move)
    assert all(p.id not in {assassin.id, victim.id} for p in result.pieces)


def test_armor_three_piece_line_captures_enemy():
    red, black = kings()
    armor = piece(PieceType.ARMOR, Color.RED, 6, 0)
    ally = piece(PieceType.PAWN, Color.RED, 6, 3)
    enemy = piece(PieceType.HORSE, Color.BLACK, 6, 4)
    board = state(red, black, armor, ally, enemy)
    rules = RulesEngine(get_profile("desktop_complete"))
    move = Move(armor.position, Position(6, 2))
    assert rules.is_legal(board, move)
    result = rules.apply_unchecked(board, move)
    assert result.piece_at(enemy.position) is None
    assert rules.captured_by_move(board, move) == (enemy,)


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
