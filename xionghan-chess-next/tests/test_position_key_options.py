"""`position_key` 必须包含**影响合法着法的选项摘要**（L-07）。

风险场景：`positionCounts` 会随存档/导入/网络带进**选项不同**的新对局，那些计数是按旧选项算的。
key 不含选项时，两种规则下的同一盘面会共用一份计数 —— 按旧选项的历史计数判和。
"""

from __future__ import annotations

from xionghan_chess.core.game import Game
from xionghan_chess.core.rules import POSITION_KEY_VERSION


def _game(**options) -> Game:
    return Game("desktop_complete", option_overrides=options)


def test_key_version_is_bumped() -> None:
    """改了 key 格式就必须 bump；v3 起含 `||opt:` 段。"""
    assert POSITION_KEY_VERSION >= 3


def test_same_board_different_options_yield_different_keys() -> None:
    base = _game()
    with_flag = _game(pawn_three_line_capture=True)
    no_promo = _game(pawn_promotion=False)
    keys = {base.rules.position_key(base.state),
            with_flag.rules.position_key(with_flag.state),
            no_promo.rules.position_key(no_promo.state)}
    assert len(keys) == 3, f"三种选项下 key 撞了：{keys}"


def test_key_carries_the_option_digest_segment() -> None:
    key = _game(pawn_three_line_capture=True).rules.position_key(
        _game(pawn_three_line_capture=True).state)
    assert "||opt:" in key
    assert "p3l1" in key, key


def test_old_key_counts_never_cause_a_draw() -> None:
    """白盒：旧格式 key（无 opt 段）上挂着 5 次计数 → 当前局面仍按 0 计，**不判和**。"""
    game = _game(pawn_three_line_capture=True)
    board = ";".join(f"{p.color.value}:{p.type.value}:{p.position.row}:{p.position.col}"
                     for p in sorted(game.state.pieces,
                                     key=lambda p: (p.color.value, p.type.value,
                                                    p.position.row, p.position.col)))
    legacy_key = f"{game.state.turn.value}|{board}||pool:"
    assert legacy_key != game.rules.position_key(game.state)

    game.state.position_counts = {legacy_key: 5}
    game._settle(game.state.turn, None)
    assert game.state.finished is False
