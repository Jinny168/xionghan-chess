"""复盘关键手档位 → 试走：真点标签、真走沙盘、真比权威字节。

关键约束：起点必须是该手**之前**的快照；只走沙盘、不悔棋、不写回权威局；
构造不了的档位灰掉而不是硬开。
"""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.desktop.ui import dialogs as dialogs_module  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import DocumentDialog, ReplayDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _played_game(plies: int) -> Game:
    game = Game()
    for _ in range(plies):
        moves = game.rules.legal_moves(game.state)
        assert moves
        game.move(moves[0])
    return game


def _bytes(state: object) -> bytes:
    return json.dumps(state.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _snapshots_bytes(game: Game) -> bytes:
    # Game._snapshots 里存的已经是 dict（见 sandbox.build_sandbox_game）。
    return json.dumps(game._snapshots, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pieces(state: object) -> object:
    return state.to_dict()["pieces"]


def _result(ply: int) -> dict[str, object]:
    return {
        "analyzedPlies": ply,
        "summary": {"best": 0, "good": 0, "inaccuracy": 0, "mistake": 1, "blunder": 0},
        "winRateCurve": [50.0, 42.0, 30.0, 28.0],
        "moves": [
            {"ply": index, "notation": f"着{index}", "quality": "mistake" if index == ply else "best", "scoreLoss": 300 if index == ply else 0}
            for index in range(1, ply + 1)
        ],
    }


def _feed_analysis(monkeypatch: pytest.MonkeyPatch, dialog: ReplayDialog, ply: int) -> None:
    monkeypatch.setattr(DocumentDialog, "exec", lambda _self: None)
    dialog._show_analysis_result(_result(ply))


def test_key_move_tag_enters_sandbox_from_pre_move_state_and_leaves_record_untouched(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = _played_game(4)
    dialog = ReplayDialog(game, {"language": "zh-CN"})
    before_state = _bytes(game.state)
    before_snapshots = _snapshots_bytes(game)

    _feed_analysis(monkeypatch, dialog, ply=3)
    buttons = [button for button in dialog._key_move_buttons if button.objectName() == "keyMoveTrial3"]
    assert len(buttons) == 1 and buttons[0].isEnabled()
    assert "失误" in buttons[0].text(), "档位标签应带质量档位"

    buttons[0].click()
    sandbox = dialog._sandbox_game
    assert sandbox is not None and dialog._sandbox_trial is True
    assert _pieces(sandbox.state) == _pieces(dialog.snapshots[2]), "必须从第 3 手**之前**的局面起"
    assert _pieces(sandbox.state) != _pieces(dialog.snapshots[3]), "起点不是前一格，等于把失误手走完了"
    assert dialog.sandbox_undo.isHidden() and not dialog.sandbox_undo.isEnabled()

    move = next(iter(sandbox.rules.legal_moves(sandbox.state)))
    dialog._sandbox_move(move)
    assert len(sandbox.state.history) == 1, "试走要真的能落子"

    dialog.tabs.setCurrentIndex(0)  # 退出试走，回到复盘
    assert dialog._sandbox_game is None and dialog._sandbox_trial is False
    assert not dialog.sandbox_undo.isHidden(), "退出试走后普通沙盘的悔棋按钮要恢复"
    assert _bytes(game.state) == before_state, "权威局面被试走写回"
    assert _snapshots_bytes(game) == before_snapshots, "棋谱快照被试走写回"
    dialog.close()


def test_unbuildable_key_move_tag_is_disabled(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = _played_game(3)
    dialog = ReplayDialog(game, {"language": "zh-CN"})
    warnings: list[str] = []

    def boom(_source: Game) -> Game:
        raise RuntimeError("历史局面构造失败")

    monkeypatch.setattr(dialogs_module, "build_sandbox_game", boom)
    monkeypatch.setattr(QMessageBox, "warning", lambda _parent, title, text: warnings.append(text))

    _feed_analysis(monkeypatch, dialog, ply=2)
    assert dialog._key_move_buttons, "分析报告应产出档位标签"
    assert all(not button.isEnabled() for button in dialog._key_move_buttons)
    assert not warnings, "预检阶段的构造失败应灰掉标签，不弹窗打断复盘"

    dialog._key_move_buttons[0].click()  # disabled 按钮点了也不该进沙盘
    assert dialog._sandbox_game is None and not dialog._sandbox_active
    dialog.close()
