import pytest

from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color
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
