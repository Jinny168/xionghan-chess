import json

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.legacy import migrate_legacy_game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType
from xionghan_chess.core.profiles import get_profile
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


def _downgrade_to_pre_pool_key(data: dict) -> dict:
    """Turn a current document into what a pre-方案A build would have written.

    Those builds had no `positionKeyVersion` marker and keyed `positionCounts`
    with the pool-blind format, so strip the marker and cut every `||pool:` tail
    back off the keys. This is the shape `game_from_document` has to migrate.
    """
    data.pop("positionKeyVersion", None)
    counts = data["state"]["positionCounts"]
    data["state"]["positionCounts"] = {key.split("||pool:")[0]: count
                                       for key, count in counts.items()}
    return data


def test_legacy_document_rebuilds_the_ledger_in_the_current_key_format():
    """A pre-方案A .xhgame can never reproduce its own keys, so loading it must
    re-derive the ledger in today's pool-aware format.

    Keeping the old keys would drop every pre-load occurrence (漏判); a load that
    invented keys would mis-count (误判). This asserts the counts survive the
    format change intact and no stale old-format key survives beside them.
    """
    game = Game("desktop_complete")
    for _ in range(6):
        game.move(sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())[0])
    live = dict(game.state.position_counts)
    assert live, "the live game recorded its positions"

    restored = game_from_document(_downgrade_to_pre_pool_key(game_document(game)))

    assert restored.state.position_counts == live
    assert all("||pool:" in key for key in restored.state.position_counts)


def test_legacy_document_still_reaches_threefold_after_the_upgrade():
    """The pool-aware rebuild must not cost a repetition: a game that saw a
    position twice before 方案A still draws when it appears a third time."""
    def sparse() -> Game:
        profile = get_profile("desktop_complete")
        pieces = [
            Piece.create(PieceType.KING, Color.RED, 0, 0),
            Piece.create(PieceType.KING, Color.BLACK, profile.rows - 1, profile.cols - 1),
            Piece.create(PieceType.ROOK, Color.RED, 6, 4),
            Piece.create(PieceType.ROOK, Color.BLACK, 3, 4),
        ]
        return Game.from_state(GameState(profile.id, pieces, turn=Color.RED))

    def play(game: Game, sr: int, sc: int, tr: int, tc: int) -> None:
        move = next(m for m in game.rules.legal_moves(game.state)
                    if (m.source.row, m.source.col, m.target.row, m.target.col) == (sr, sc, tr, tc))
        game.move(move)

    cycle = [(6, 4, 6, 5), (3, 4, 3, 5), (6, 5, 6, 4), (3, 5, 3, 4)]
    game = sparse()
    for squares in cycle:                       # one full cycle: start position now seen twice
        play(game, *squares)

    restored = game_from_document(_downgrade_to_pre_pool_key(game_document(game)))
    assert restored.state.draw is False

    for squares in cycle:                       # return to it a third time
        play(restored, *squares)
    assert restored.state.draw is True
    assert restored.state.result_reason == "threefold_repetition"


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
