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


CYCLE = [(Position(9, 9), Position(9, 10)), (Position(0, 4), Position(0, 5)),
         (Position(9, 10), Position(9, 9)), (Position(0, 5), Position(0, 4))]
"""4 拍一轮、回到同一局面的真实循环（红车来回 + 黑王在宫内来回）。

黑王必须在 `(0,4)↔(0,5)`：走到 `(0,6)` 会与红王 `(11,6)` 同列**照面**，直接非法走棋 ——
这条路我试过了，别再把黑王放回 `(0,6)`。
"""


def _cycle_board(**overrides) -> Game:
    """专门用来制造重复局面的小局面：红王 + 黑王 + 红车。"""
    return _game([piece(PieceType.KING, Color.RED, 11, 6),
                  piece(PieceType.KING, Color.BLACK, 0, 4),
                  piece(PieceType.ROOK, Color.RED, 9, 9)], **overrides)


def _play_cycles(game: Game, times: int) -> None:
    """真走棋 `times` 轮（每轮回到同一局面）。**不注入 counts** —— 这是行为测试。"""
    for _ in range(times):
        for source, target in CYCLE:
            if game.state.finished:
                return
            game.move(Move(source, target))


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
    # 白盒：直接给**当前局面**注入 3 次计数，专测 settle 的判定顺序（僵局先于重复）。
    game = _stalemate_board()
    game.state.position_counts = {game.rules.position_key(game.state): 3}
    state = _settle(game)
    assert state.winner is Color.RED
    assert state.result_reason == "stalemate"


def test_threefold_repetition_fires_only_on_the_third_occurrence():
    """真走棋：走 2 轮回到同一局面两次**不判和**，第 3 次才判和。

    为什么这条必须走真棋：旧的 `_repeat` 只有一行
    `position_counts = {"whatever": n}` —— **一步都没走**，验的是 `max()` 的实现细节。

    这也是 L-06 的直接证据：**用旧的 `max(...)` 实现跑这个 `CYCLE`，第 3 轮内就会
    `GameError("对局已经结束")`** —— 因为只要"历史上任何局面"计数到 3 就判和，
    与"当前局面是否重复"无关。改成 `get(当前 key)` 之后，轨迹才是：
    ```
    第1轮后 counts=[1,1,1,1]  finished=False
    第2轮后 counts=[2,2,2,2]  finished=False
    第3轮后 counts=[3,2,2,2]  finished=True reason=threefold_repetition
    ```
    """
    game = _cycle_board()
    _play_cycles(game, 2)
    assert game.state.finished is False, "第 2 次重复不该判和"

    _play_cycles(game, 1)
    assert game.state.finished is True
    assert game.state.draw is True
    assert game.state.winner is None
    assert game.state.result_reason == "threefold_repetition"


def test_threefold_repetition_is_skipped_when_the_switch_is_off():
    game = _cycle_board(threefold_draw=False)
    _play_cycles(game, 3)
    assert game.state.finished is False
    state = _settle(game)
    assert state.finished is False
    assert state.draw is False


def test_threefold_repetition_is_reported_instead_of_no_progress():
    """同一次落子同时满足"三次重复"与"无进展"时，报 `threefold_repetition`。

    为什么用白盒：真走棋时 `no_progress_draw_plies=2` 会在第 2 拍就先判无进展，
    根本走不到第 3 次重复 —— 那样测的是"谁先发生"，不是"同时满足时谁优先"。
    """
    game = _cycle_board(no_progress_draw_plies=2)
    game.state.history = _history(4)
    game.state.position_counts = {game.rules.position_key(game.state): 3}
    _settle(game)
    assert game.state.finished is True
    assert game.state.result_reason == "threefold_repetition"


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


def test_stale_injected_counts_never_cause_a_draw():
    """白盒：直接注入 counts —— 别的 key 上挂着 5 次，当前局面只有 1 次，**不许判和**。

    这条守的是 L-06 的真实影响路径：counts 会随存档/导入/网络从外部进来。
    删掉"假构造器"不该把这个风险一起删掉，但它必须以白盒身份存在，不能冒充行为测试。
    """
    game = _cycle_board()
    current = game.rules.position_key(game.state)
    game.state.position_counts = {"stale-key": 5, current: 1}
    _settle(game)
    assert game.state.finished is False
    assert game.state.draw is False
