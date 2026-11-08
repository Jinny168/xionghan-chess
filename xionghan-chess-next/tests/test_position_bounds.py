"""坐标校验（B-01）：负坐标进不来，越界在读档时明确报错。

审计复现：王在 `(-1,-1)` 的存档能静默载入，形成"无王可吃"的僵尸局。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.model import Position, UnsupportedSaveError
from xionghan_chess.core.storage import game_from_document


def _document(pieces: list[dict]) -> dict:
    return {
        "formatVersion": 1,
        "profileId": "desktop_complete",
        "state": {"profileId": "desktop_complete", "pieces": pieces, "turn": "red",
                  "captured": {"red": [], "black": []}, "history": [], "clocksMs": {}},
        "snapshots": [],
    }


def _king(color: str, row: int, col: int, pid: str) -> dict:
    return {"id": pid, "type": "king", "color": color, "row": row, "col": col}


def test_position_itself_allows_out_of_board_probes() -> None:
    """`Position` **不**校验范围 —— 引擎要靠它探测越界格（`get()` 返回 None 即出界）。

    这条是在钉住"不要在值对象里加范围校验"：加了会打断 `rules.py`/`ai.py` 的探测写法
    （实测会让 63 条测试红）。越界防线在读档边界。
    """
    assert Position(-1, 4).row == -1
    assert Position(13, 0).col == 0


def test_save_with_negative_coordinates_is_rejected() -> None:
    """审计复现：王在 `(-1,-1)` 的存档必须被明确拒绝，而不是载入成僵尸局。"""
    doc = _document([_king("red", -1, -1, "k1"), _king("black", 0, 4, "k2")])
    with pytest.raises(UnsupportedSaveError, match="坐标越界：row=-1, col=-1"):
        game_from_document(doc)


def test_save_with_out_of_board_coordinates_is_rejected() -> None:
    """上界按 profile 校验：13×13 的棋盘上 row=13 必须被拒，且提示要给人看。"""
    doc = _document([_king("red", 13, 0, "k1"), _king("black", 0, 4, "k2")])
    with pytest.raises(UnsupportedSaveError, match="坐标越界：row=13, col=0"):
        game_from_document(doc)


def test_valid_document_still_loads() -> None:
    game = game_from_document(_document([_king("red", 12, 6, "k1"), _king("black", 0, 4, "k2")]))
    assert game.profile.rows == 13
