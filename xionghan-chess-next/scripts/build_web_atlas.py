"""生成网页「棋子图谱」的首屏静态快照：`web/data/piece_atlas.json`。

为什么是静态快照（C 方案）：
网页端**没有本地规则引擎**（不加载 `offline.js`，以免变成第三套引擎）。
首屏只需"预设局面 + 该子可走格"，构建时用服务端同源的 `RulesEngine` 算好导出即可，
零请求、零漂移；用户真的走第二步时才打 `/api/analysis/legal`。

用法：python scripts/build_web_atlas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game          # noqa: E402
from xionghan_chess.core.model import (            # noqa: E402
    Color, GameState, Piece, PieceType, Position,
)
from xionghan_chess.core.profiles import RuleOptions  # noqa: E402

PROFILE = "web"


def piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def build_state(pieces: list[Piece], options: dict) -> Game:
    state = GameState(PROFILE, pieces, turn=Color.RED,
                      captured={Color.RED: [], Color.BLACK: []})
    return Game.from_state(state, options, None)


def preset(preset_id: str, label: str, note: str, pieces: list[Piece],
           spotlight: tuple[int, int], options: dict | None = None) -> dict:
    game = build_state(pieces, options or {})
    row, col = spotlight
    target = game.state.piece_at(Position(row, col))
    moves = [m for m in game.rules.legal_moves(game.state) if m.source == Position(row, col)]
    return {
        "id": preset_id,
        "label": label,
        "note": note,
        "options": options or {},
        "pieces": [{"type": p.type.value, "color": p.color.value,
                    "row": p.position.row, "col": p.position.col} for p in pieces],
        "spotlight": {"row": row, "col": col, "type": target.type.value if target else None},
        "moves": [{"row": m.target.row, "col": m.target.col} for m in moves],
        "check": game.rules.in_check(game.state, game.state.turn),
        # `capturable_squares` 返回 {目标格: [Removal...]}，键就是被吃子的格子
        "captures": [{"row": pos.row, "col": pos.col}
                     for pos in game.rules.capturable_squares(game.state, game.state.turn)],
        "rows": game.profile.rows,
        "cols": game.profile.cols,
    }


# 与桌面 `piece_atlas.py::_demo_pieces` **同源**：同一套摆法，避免两端演示不同的东西
KINGS = [piece(PieceType.KING, Color.RED, 12, 12), piece(PieceType.KING, Color.BLACK, 0, 10)]

PRESETS = [
    preset("clamp", "夹逼", "斜走段两侧同时有子 → 这一段不通过（更远的敌子也吃不到）",
           KINGS + [
               piece(PieceType.ARCHER, Color.RED, 6, 6),    # 射：斜走
               piece(PieceType.PAWN, Color.RED, 7, 6),      # 起点夹逼的一侧
               piece(PieceType.PAWN, Color.RED, 6, 7),      # 另一侧 → 该斜段无效
               piece(PieceType.HORSE, Color.BLACK, 9, 9),   # 同一条斜线更远处，被夹逼挡住
           ], (6, 6)),
    preset("three", "三连", "己方两子（含兵）夹住敌子成一线 → 该敌子被吃",
           KINGS + [
               piece(PieceType.PAWN, Color.RED, 7, 2),
               piece(PieceType.PAWN, Color.RED, 6, 3),
               piece(PieceType.HORSE, Color.BLACK, 6, 4),
           ], (7, 2), {"pawn_three_line_capture": True}),
    preset("facing", "照面", "两王正面相对、中间无子 → 被将",
           [piece(PieceType.KING, Color.RED, 6, 3), piece(PieceType.KING, Color.BLACK, 6, 9)],
           (6, 3)),
    preset("free", "自由", "常规局面：点任意子看它的可走格",
           KINGS + [
               piece(PieceType.ARCHER, Color.RED, 6, 6),
               piece(PieceType.PAWN, Color.BLACK, 4, 6),
               piece(PieceType.PAWN, Color.BLACK, 6, 9),
           ], (6, 6)),
]


def main() -> None:
    out = {"profile": PROFILE, "presets": PRESETS}
    path = ROOT / "web" / "data" / "piece_atlas.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in PRESETS:
        print(f"{item['id']:7s} moves={len(item['moves']):2d} check={item['check']}")
    print("已生成", path)


if __name__ == "__main__":
    main()
