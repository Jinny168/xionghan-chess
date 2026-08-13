import json

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.desktop.storage import game_document, game_from_document, load_game, save_game


def test_game_document_round_trip_preserves_state_and_replay(tmp_path):
    game = Game("desktop_complete")
    game.move(game.rules.legal_moves(game.state)[0])
    path = save_game(game, tmp_path / "record.xhgame")

    restored = load_game(path)

    assert restored.state.to_dict() == game.state.to_dict()
    assert restored.public_state()["replay"] == game.public_state()["replay"]


def test_game_document_rejects_unknown_version():
    data = game_document(Game("web"))
    data["formatVersion"] = 99

    with pytest.raises(ValueError, match="版本"):
        game_from_document(data)


def test_game_document_rejects_incomplete_replay_data():
    game = Game("traditional")
    game.move(game.rules.legal_moves(game.state)[0])
    data = game_document(game)
    data["snapshots"] = []

    restored = game_from_document(data)
    assert restored.state.to_dict() == game.state.to_dict()

    data["snapshots"] = [{"profileId": "web", "pieces": []}]
    with pytest.raises(ValueError, match="不同规则档案"):
        game_from_document(data)
