import json

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.legacy import migrate_legacy_game
from xionghan_chess.desktop import storage
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


def test_legacy_traditional_fen_is_migrated():
    document = migrate_legacy_game("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR r")
    assert document["formatVersion"] == 1
    assert document["profileId"] == "traditional"
    assert document["source"] == "legacy-fen"
    assert len(document["state"]["pieces"]) == 32


def test_legacy_json_wrapped_fen_loads_from_desktop(tmp_path):
    path = tmp_path / "legacy.fen"
    path.write_text('{"position":"4k4/9/9/9/9/9/9/9/9/4K4 b"}', encoding="utf-8")
    game = load_game(path)
    assert game.profile.id == "traditional"
    assert game.state.turn.value == "black"


def test_statistics_upgrade_old_schema_and_track_streak(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "statistics_path", lambda: tmp_path / "statistics.json")
    storage.statistics_path().write_text('{"games":2,"wins":1,"losses":1,"draws":0,"moves":12}', encoding="utf-8")
    game = Game("traditional")
    game.state.winner = game.state.turn
    stats = storage.record_result(game, game.state.turn.value)
    assert stats["games"] == 3
    assert stats["winStreak"] == {"current": 1, "max": 1}
    assert stats["perColor"][game.state.turn.value]["wins"] == 1
