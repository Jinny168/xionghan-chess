import pytest

from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, GameState, Move, MoveRecord, Piece, PieceType, Position
from xionghan_chess.core.storage import game_document, game_from_document


def test_pause_freezes_clock_and_survives_document_round_trip(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("xionghan_chess.core.game.time.monotonic", lambda: now[0])
    game = Game("traditional", initial_minutes=5)
    game.state.turn_started_at = now[0]

    now[0] = 105.0
    game.set_paused(True, Color.RED)
    paused_clock = game.state.clocks_ms[Color.RED]
    assert paused_clock == 295_000
    assert game.state.paused is True

    now[0] = 205.0
    game.tick()
    assert game.state.clocks_ms[Color.RED] == paused_clock
    with pytest.raises(GameError, match="暂停"):
        game.move(game.rules.legal_moves(game.state)[0])

    restored = game_from_document(game_document(game))
    assert restored.state.paused is True
    assert restored.state.paused_by is Color.RED

    game.set_paused(False, Color.RED)
    now[0] = 206.0
    game.tick()
    assert game.state.clocks_ms[Color.RED] == paused_clock - 1_000


# --------------------------------------------------------------------------
# R-2: the terminal-state chain at Game._settle.
#
# The chain is the unit under test, and `_settle` is its only entry point that
# takes the piece that landed rather than a `Move` -- the resurrection path has
# no `Move` at all -- so these drive it directly. That is what makes the
# precedence assertions below honest: building a full game up to, say, a
# threefold draw would drag in whatever earlier level happens to fire first.
# --------------------------------------------------------------------------

def piece(kind, color, row, col):
    return Piece.create(kind, color, row, col)


def _game(pieces, **overrides) -> Game:
    game = Game("desktop_complete", option_overrides=overrides or None)
    game.state = GameState("desktop_complete", list(pieces), turn=Color.RED)
    game.state.clocks_ms = {Color.RED: 1_200_000, Color.BLACK: 1_200_000}
    return game


def _mate_board(**overrides) -> Game:
    """Black is in check from (5,0) with (5,1) covering both flight squares."""
    return _game([piece(PieceType.KING, Color.RED, 11, 6),
                  piece(PieceType.KING, Color.BLACK, 0, 0),
                  piece(PieceType.ROOK, Color.RED, 5, 0),
                  piece(PieceType.ROOK, Color.RED, 5, 1)], **overrides)


def _stalemate_board(**overrides) -> Game:
    """Black has no legal move but is not in check."""
    return _game([piece(PieceType.KING, Color.RED, 11, 6),
                  piece(PieceType.KING, Color.BLACK, 0, 0),
                  piece(PieceType.ROOK, Color.RED, 1, 1)], **overrides)


def _open_board(**overrides) -> Game:
    """Black still has moves, so no earlier level of the chain can fire."""
    return _game([piece(PieceType.KING, Color.RED, 11, 6),
                  piece(PieceType.KING, Color.BLACK, 0, 0),
                  piece(PieceType.ROOK, Color.RED, 9, 9)], **overrides)


def _settle(game: Game, moved=None):
    game._settle(Color.RED, moved)
    return game.state


def _repeat(game: Game, occurrences: int) -> None:
    game.state.position_counts = {"whatever": occurrences}


def _history(plies: int, *, captured=()) -> list[MoveRecord]:
    return [MoveRecord(move=Move(Position(0, 0), Position(0, 1)), color=Color.RED,
                       piece_type=PieceType.ROOK, captured=captured, notation="")
            for _ in range(plies)]


def test_settle_reports_king_captured_when_the_enemy_king_is_gone():
    game = _game([piece(PieceType.KING, Color.RED, 11, 6)])
    state = _settle(game)
    assert state.winner is Color.RED
    assert state.result_reason == "king_captured"


def test_settle_prefers_palace_invasion_over_a_simultaneous_checkmate():
    game = _mate_board()
    # The red king has walked into black's palace, and black is also mated --
    # the invasion sits higher in the chain, so it is the reported reason.
    game.state.pieces[0] = piece(PieceType.KING, Color.RED, 3, 6)
    state = _settle(game, moved=game.state.pieces[0])
    assert state.winner is Color.RED
    assert state.result_reason == "palace_invasion"


def test_palace_invasion_is_skipped_when_the_switch_is_off():
    game = _mate_board(invasion_victory=False)
    game.state.pieces[0] = piece(PieceType.KING, Color.RED, 3, 6)
    state = _settle(game, moved=game.state.pieces[0])
    assert state.result_reason == "checkmate"


def test_settle_reports_checkmate_and_stalemate_on_their_own():
    assert _settle(_mate_board()).result_reason == "checkmate"
    assert _settle(_stalemate_board()).result_reason == "stalemate"


def test_settle_prefers_stalemate_over_a_threefold_repetition():
    game = _stalemate_board()
    _repeat(game, 3)
    state = _settle(game)
    assert state.winner is Color.RED
    assert state.result_reason == "stalemate"


def test_settle_reports_threefold_repetition_only_from_the_third_occurrence():
    for occurrences, finished in ((2, False), (3, True)):
        game = _open_board()
        _repeat(game, occurrences)
        state = _settle(game)
        assert state.finished is finished
        if finished:
            assert state.draw is True
            assert state.winner is None
            assert state.result_reason == "threefold_repetition"


def test_threefold_repetition_is_skipped_when_the_switch_is_off():
    game = _open_board(threefold_draw=False)
    _repeat(game, 3)
    state = _settle(game)
    assert state.finished is False
    assert state.draw is False


def test_settle_prefers_threefold_repetition_over_no_progress():
    game = _open_board(no_progress_draw_plies=2)
    game.state.history = _history(4)
    _repeat(game, 3)
    assert _settle(game).result_reason == "threefold_repetition"


def test_settle_reports_no_progress_and_restarts_on_a_capture():
    game = _open_board(no_progress_draw_plies=3)
    game.state.history = _history(3)
    state = _settle(game)
    assert state.draw is True
    assert state.result_reason == "no_progress"

    # A capture restarts the counter, so the same length of history is not enough.
    game = _open_board(no_progress_draw_plies=3)
    game.state.history = _history(3, captured=(piece(PieceType.PAWN, Color.BLACK, 4, 4),))
    assert _settle(game).finished is False


def test_resurrection_runs_the_same_terminal_chain():
    # Resurrecting has no `Move`, which is exactly why `_settle` takes the piece
    # that landed; it has to reach the same verdict a normal move would.
    game = _stalemate_board()
    game.state.turn = Color.RED
    game.state.captured[Color.RED].append(piece(PieceType.PAWN, Color.RED, 4, 4))
    game.resurrect_pawn(Color.RED, Position(8, 0))
    assert game.state.winner is Color.RED
    assert game.state.result_reason == "stalemate"
