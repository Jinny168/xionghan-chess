
import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.legacy import migrate_legacy_game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.desktop import storage
from xionghan_chess.desktop.storage import (
    game_document,
    game_from_document,
    load_game,
    save_game,
)


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


# ── F1-a 旧档迁移：`guard@(1,5)/(11,5)` → `advisor` ─────────────────────────
# `95c2784` 的尉/仕对调只在启用尉的 `desktop_complete` 上成立；`desktop_classic` /
# `web` 当时被连带换成了一枚"走不动、不显示、却挡子"的尉，F1-a 已把 roster 改回仕。
# 于是**F1-a 之前保存的这两档棋谱**，`setup` 槽位里还写着 `red:guard:11:5`，
# 直接加载会被 `GameSetup.build` 的 `unavailable piece slots` 拒掉 —— 用户升级后
# 打不开自己的棋谱。迁移在 `storage.game_from_document`（文档加载边界）做。
# 注意：离线端文档不带 `setup`（`offline.js::gameDocument()` 不写），所以这条覆盖
# 不到离线包；离线题库 13 题也全是 `desktop_complete`，不受影响。
_F1A_SQUARES = {(1, 5), (11, 5)}
_F1A_PERFT = {"desktop_classic": 113, "web": 107}
_F1A_PERFT_MID = {"desktop_classic": 110, "web": 104}


def _legacy_f1a_document(profile_id: str, plies: int = 0) -> dict:
    """造一份 **F1-a 之前**会写出的存档（把 (1,5)/(11,5) 的仕退回成尉）。

    做法：先用今天的代码摆出局面并（可选）走几手，再把 `state` 与 `snapshots` 里
    那两个坐标的 `advisor` 退回 `guard`、`setup` 槽位同步退回 —— 这样得到的文档
    与 `0bc3377` 时代 `game_document()` 的产物同形（柯桥良用旧代码生成的四份 fixture
    已对照过：加载结果逐项一致）。

    ⚠️ **台账（`positionCounts`）不能靠字符串替换回退，只能从源头重算。** 实测三种替换
    写法都还原不出真旧键：① 朴素 `replace(':advisor:',':guard:')` 会连**合法的第二只仕**
    `(11,7)` 一起改成尉，造出 `guard:11:7` 这个从不存在的局面；② 就算只替换两格也不等，
    因为 `position_key` 的棋盘段是 `sorted()` 过的、`advisor < guard`，**改类型会改变段
    在字符串里的排列位置**。手改派生值得到的是"从未存在过的状态"，拿它去断言比空转更坏
    （可能冤枉实现，也可能恒真）。所以这里先改**棋子**，再让引擎用 `position_key` 重算。
    """
    game = Game(profile_id)
    assert PieceType.GUARD not in game.profile.enabled_piece_types, profile_id
    for _ in range(plies):
        game.move(sorted(game.rules.legal_moves(game.state), key=lambda m: m.key())[0])

    data = game_document(game)
    # 迁移前的 live key：用来证明"回退真的改变了局面"（③）
    key_before_retrofit = game.rules.position_key(game.state)

    def downgrade_pieces(state_dict: dict) -> None:
        for piece in state_dict["pieces"]:
            if piece["type"] == PieceType.ADVISOR.value and (piece["row"], piece["col"]) in _F1A_SQUARES:
                piece["type"] = PieceType.GUARD.value

    downgrade_pieces(data["state"])
    for snapshot in data.get("snapshots", []):
        downgrade_pieces(snapshot)
    for key in ("redSlots", "blackSlots"):
        data["setup"][key] = [
            slot.replace("advisor:11:5", "guard:11:5").replace("advisor:1:5", "guard:1:5")
            for slot in data["setup"][key]
        ]

    # 从源头重算台账：每个 snapshot（走子前的局面）+ live 局面，逐个用 position_key 生成
    counts: dict[str, int] = {}
    for state_dict in [*data.get("snapshots", []), data["state"]]:
        position_key = game.rules.position_key(GameState.from_dict(state_dict))
        counts[position_key] = counts.get(position_key, 0) + 1
    data["state"]["positionCounts"] = counts

    # ── fixture 自证（三条各管一件事，都不做"重算结果 vs 重算结果"的自我比较）──
    # ① 源头确实改了：两个目标格上都已经是尉
    retro = GameState.from_dict(data["state"])
    assert retro.piece_at(Position(1, 5)).type is PieceType.GUARD
    assert retro.piece_at(Position(11, 5)).type is PieceType.GUARD
    # ② 派生确实是重算出来的：旧档里含 guard 的键数 == plies+1（写数字，不写 any(...)）
    assert sum("guard" in key for key in counts) == plies + 1
    # ③ 回退真的改变了局面：抓"改了棋子、却拿错 state 去重算"
    old_key = game.rules.position_key(retro)
    assert old_key != key_before_retrofit
    return data


@pytest.mark.parametrize("profile_id", ["desktop_classic", "web"])
def test_opening_archive_from_before_f1a_is_upgraded_on_load(profile_id):
    """验收 1：开局档（`history` 为空）→ 槽位与盘面都升级为仕，perft 回到新布局值。"""
    document = _legacy_f1a_document(profile_id)
    assert any("guard:11:5" in slot for slot in document["setup"]["redSlots"]), "前提：旧档槽位里确实有尉"

    game = game_from_document(document)

    assert all("guard" not in slot for slot in game.setup.red_slots + game.setup.black_slots)
    assert game.state.piece_at(Position(11, 5)).type is PieceType.ADVISOR
    assert game.state.piece_at(Position(1, 5)).type is PieceType.ADVISOR
    assert len(game.rules.legal_moves(game.state)) == _F1A_PERFT[profile_id]
    # 旧台账里的键带 guard，升级后永远产生不出来 —— 必须重建，不能留幽灵键
    assert all("guard" not in key for key in game.state.position_counts)


@pytest.mark.parametrize("profile_id", ["desktop_classic", "web"])
def test_in_progress_archive_from_before_f1a_still_loads_but_keeps_the_board(profile_id):
    """验收 2：进行中档 → 只保证能开。

    盘面原样（那枚尉仍是尉），因为对进行中的对局做追溯性棋子变更会让它凭空变得能动，
    并让 `history[].pieceType` 与盘面对不上。它能做的着法仍是 0，但**仍然是合法吃子
    目标** —— "死子"不等于"无效子"。
    """
    document = _legacy_f1a_document(profile_id, plies=1)
    assert document["state"]["history"], "前提：这份档有对局历史"

    game = game_from_document(document)

    assert all("guard" not in slot for slot in game.setup.red_slots)      # 槽位仍要迁移，否则拒载
    guard = game.state.piece_at(Position(1, 5))
    assert guard.type is PieceType.GUARD, "进行中的档不许改盘面"
    assert game.state.piece_at(Position(11, 5)).type is PieceType.GUARD
    assert len(game.rules.legal_moves(game.state)) == _F1A_PERFT_MID[profile_id]
    assert PieceType.GUARD.value not in {record.piece_type.value for record in game.state.history}

    # 它自己的合法着 = 0（`enabled_piece_types` 把它挡在伪合法着之外）
    own = [m for m in game.rules.legal_moves(game.state)
           if (m.source.row, m.source.col) == (1, 5)]
    assert own == []

    # 但它仍然可以被吃：在 (2,5) 放一枚红俥，应能吃掉 (1,5) 的尉并产生一条 removal
    game.state.pieces.append(Piece.create(PieceType.ROOK, Color.RED, 2, 5))
    captures = [m for m in game.rules.legal_moves(game.state, Color.RED)
                if (m.target.row, m.target.col) == (1, 5)]
    assert len(captures) == 1
    assert len(game.rules.board_removals(game.state, captures[0])) == 1

    # 还能继续下：黑方（存档时轮到黑）走一步不报错
    assert game.state.turn is Color.BLACK
    game.move(sorted(game.rules.legal_moves(game.state), key=lambda m: m.key())[0])
    assert len(game.state.history) == 2


def test_unavailable_slot_that_is_not_the_f1a_pair_still_raises():
    """验收 3：迁移只处理 `guard@(1,5)/(11,5)` 这一对，别的坏槽位必须继续报错。

    否则"宽松加载"会把真损坏的存档一起放过 —— 那比拒载更糟（用户以为读到了）。
    """
    document = _legacy_f1a_document("desktop_classic")
    slots = document["setup"]["redSlots"]
    # 前提断言不是装饰：替换目标不存在时 `str.replace` 是空转，文档仍然合法，
    # 于是"应该报错"的用例会变成"不报错"—— 那种反向用例等于没有。
    assert "red:guard:11:5" in slots, "前提：旧档里必须有这个尉槽位"
    document["setup"]["redSlots"] = [slot.replace("red:guard:11:5", "red:armor:11:5") for slot in slots]
    assert "red:armor:11:5" in document["setup"]["redSlots"], "前提：替换必须真的发生"
    with pytest.raises(ValueError, match="unavailable piece slots"):
        game_from_document(document)


def test_guard_slot_on_a_non_f1a_square_still_raises():
    """同类型也不泛化：尉槽位若不在旧对调位，仍按"该档不启用尉"报错。"""
    document = _legacy_f1a_document("desktop_classic")
    slots = document["setup"]["redSlots"]
    assert "red:guard:11:5" in slots, "前提：旧档里必须有这个尉槽位"
    document["setup"]["redSlots"] = [slot.replace("red:guard:11:5", "red:guard:2:5") for slot in slots]
    assert "red:guard:2:5" in document["setup"]["redSlots"], "前提：替换必须真的发生"
    with pytest.raises(ValueError, match="unavailable piece slots"):
        game_from_document(document)


def test_opening_does_not_migrate_a_profile_that_enables_guard():
    """3c：迁移的前置条件「仅当该档 `enabled_piece_types` 不含 guard」必须生效。

    `desktop_complete` 的 `(1,5)/(11,5)` 是 `95c2784` 对调后**合法**的尉
    （`guard@(11,5)` 实测 4 着）。迁移条件一旦被写宽成"任何 `(1,5)` 上的 guard 都
    改成仕"，就会把 F1-a 的修正**反向渗透**到这唯一不需要它的一档。

    为什么这条必须单独存在：四档 `nativeOpening` 对拍只测**全新开局**，根本不走
    存档路径 —— 条件写宽了那条腿不会红。**它是这条前置条件唯一的守卫。**
    """
    game = Game("desktop_complete")
    loaded = game_from_document(game_document(game))

    assert loaded.state.piece_at(Position(1, 5)).type is PieceType.GUARD
    assert loaded.state.piece_at(Position(11, 5)).type is PieceType.GUARD
    assert len(loaded.rules.legal_moves(loaded.state)) == 108
    assert any("guard" in slot for slot in loaded.setup.red_slots + loaded.setup.black_slots)

