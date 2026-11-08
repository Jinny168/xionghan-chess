"""校验内置训练题库（`core/data/puzzles.json`），并打印覆盖度矩阵。

原题库 9 条**全是「开局第一步」drill**，标题却叫「残局与排局训练」，
且甲/刺/楯三种子力零覆盖（见迭代计划 P1-M）。本脚本负责把「题库说的」和
「题库实际做到的」对齐 —— 覆盖度一律从解法反推，不信题目自带的声明字段。

判定标准（缺一条就报错）
1. 题面必须能构建：优先读内联 `document`，否则重放 `positionMoves` 前缀，
   每一步都要在该 profile 下合法；
2. 解法首着必须在题面下合法；
3. 若声明了 `pieceTypes` / `captureKinds` / `requiresCapture`，必须与实跑一致
   —— 这是为了防止「标着练甲、实际没碰甲」这类名不副实的回归（P1-M 的原始症状）。

用法：
    python scripts/build_puzzles.py             # 校验 + 覆盖度矩阵（默认）
    python scripts/build_puzzles.py --inline     # 把 positionMoves 换成内联 document
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    Color,
    Move,
    PieceType,
    Position,
)
from xionghan_chess.core.rules import CaptureKind  # noqa: E402
from xionghan_chess.core.puzzles import Puzzle  # noqa: E402
from xionghan_chess.core.storage import game_document, game_from_document  # noqa: E402

DATA = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"


def m(source: tuple[int, int], target: tuple[int, int]) -> dict[str, int]:
    """(row, col) -> {"row": .., "col": ..}，只为让下面的题面可读。"""
    return {"from": {"row": source[0], "col": source[1]},
            "to": {"row": target[0], "col": target[1]}}


def move_of(raw: dict) -> Move:
    return Move(Position(**raw["from"]), Position(**raw["to"]))


def build_game(profile_id: str, position_moves: list[dict]) -> Game:
    game = Game(profile_id)
    for raw in position_moves:
        game.move(move_of(raw))
    return game


def position_game(item: dict) -> Game:
    """题面怎么来：优先用内联 `document`，否则重放 `positionMoves` 前缀。

    两种写法都要支持 —— 手写题库时 `positionMoves` 更好读，而 `--inline` 之后
    文件里存的是 `document`（避免每次加载重放，见 `inline_documents`）。
    """
    if isinstance(item.get("document"), dict):
        return game_from_document(item["document"])
    return build_game(item.get("profileId", "desktop_complete"), item.get("positionMoves", []))


def check_puzzle(item: dict) -> list[str]:
    """返回问题清单；空列表表示通过。"""
    problems: list[str] = []
    pid = item["id"]
    game = position_game(item)

    if game.state.finished:
        problems.append(f"{pid}: 题面已是终局")
    for kind in item.get("pieceTypes", []):
        if not any(p.type is PieceType(kind) for p in game.state.pieces):
            problems.append(f"{pid}: 题面缺少声明的子力 {kind}")

    solution = item["solution"]
    if not solution:
        problems.append(f"{pid}: 无解法")
        return problems
    first = move_of(solution[0])
    if not game.rules.is_legal(game.state, first):
        problems.append(f"{pid}: 解法首着不合法 {m((first.source.row, first.source.col), (first.target.row, first.target.col))}")

    # 首着必须真的有战术意义 —— 否则「残局训练」退化成随便走一步。
    # 走 `capturable_squares` 这个公开查询而不是 `_apply_move`：前者是 HUD 与
    # 对拍门禁共用的唯一口径，拿它当判据能保证「题库说的吃法」和「界面显示的
    # 可吃方块」不会各说各话。
    #
    # 关键细节：甲的成线吃、刺的拖拽吃都被记在**受害者格子**上，而不是落点，
    # 所以不能只看 `caps[first.target]`。这里按 removal.origin == 首着起点 过滤，
    # 直接吃（DIRECT）另外用 `captured_by_move` 补齐。
    caps = game.rules.capturable_squares(game.state, game.state.turn)
    origin = (first.source.row, first.source.col)
    kinds = {
        removal.kind.value
        for spec in caps.values()
        for removal in spec.removals
        if (removal.origin.row, removal.origin.col) == origin
    }
    # `direct` 只认「落点原本就站着敌子」。`captured_by_move` 会把成线吃、拖拽吃的
    # 受害者一起返回，直接拿它当 direct 的判据，等于把 armor_line 也算成 direct ——
    # 声明写错也能过，校验就失去意义了。
    victims = game.rules.captured_by_move(game.state, first)
    landing = game.rules.get(game.state, first.target)
    if landing is not None and landing.color is not game.state.turn:
        kinds.add(CaptureKind.DIRECT.value)
    for kind in item.get("captureKinds", []):
        if kind not in kinds:
            problems.append(f"{pid}: 首着未触发声明的吃法 {kind}（实际 {sorted(kinds) or '无'}）")
    if item.get("requiresCapture") and not victims:
        problems.append(f"{pid}: 声明为吃子题，但首着无吃子")

    # 后续解法步（多步题）也要连贯地走通。
    probe = position_game(item)
    for index, raw in enumerate(solution):
        step = move_of(raw)
        if not probe.rules.is_legal(probe.state, step):
            problems.append(f"{pid}: 第 {index + 1} 步不合法")
            break
        probe.move(step)
    return problems


def document_for(item: dict, *, with_snapshots: bool = False) -> dict:
    """把 `positionMoves` 前缀煎成一份可直接加载的局面文档。

    **默认丢掉 `snapshots`**，两个原因：
    1. 体积：快照存的是每步之后的完整局面，8-12 步前缀能让单条题目涨到 100-180 KB；
    2. 语义：题面是一个固定起点，玩家不需要把棋「悔」回前缀里去。空快照是合法的
      （`game_from_document` 只在 `snapshots` 非空时才校验长度），玩家自己走的第一手
      仍可正常悔棋。
    """
    game = build_game(item.get("profileId", "desktop_complete"), item.get("positionMoves", []))
    document = game_document(game)
    if not with_snapshots:
        document.pop("snapshots", None)
    return document


def inline_documents() -> None:
    """把题库里的 `positionMoves` 前缀就地换成 `document`（幂等）。

    为什么必须这么做：`load_puzzles` 遇到 `positionMoves` 要**重放**这段棋谱，
    而每一步都会跑将军/终局判定。实测 7 条带前缀的新题重放共 **9.27 秒**，
    最慢单条 2.48 秒 —— 训练对话框每次 `reload()` 都会调 `load_puzzles()`，
    等于一开窗就卡 9 秒。内联后加载只剩一次 `json.loads`。
    """
    items = json.loads(DATA.read_text(encoding="utf-8"))
    changed = 0
    for item in items:
        if "positionMoves" not in item:
            continue
        item["document"] = document_for(item)
        del item["positionMoves"]
        changed += 1
    DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"已内联 {changed} 条题目的局面文档 -> {DATA.relative_to(ROOT)}")


def coverage_of(item: dict) -> tuple[set[str], set[str]]:
    """从解法**反推**这道题实际练到什么子力、触发什么吃法。

    实现在 `Puzzle.exercise()`（core/puzzles.py），这里只是把裸 dict 转成 Puzzle
    再调用 —— 口径只有一份，避免「校验器算的覆盖」和「界面/文档说的覆盖」两套。

    题面同样走 `position_game`：内联过的条目只有 `document`，用 `document_for`
    会拿到**初始棋阵**，覆盖度会整体算错（内联后曾因此把甲/刺/楯全算丢）。
    """
    document = (item["document"] if isinstance(item.get("document"), dict)
                else document_for(item))
    puzzle = Puzzle(
        str(item["id"]), str(item["title"]), str(item["difficulty"]),
        str(item.get("description", "")), document,
        tuple(move_of(raw) for raw in item["solution"]),
        tuple(str(hint) for hint in item.get("hints", [])),
        tuple(str(tag) for tag in item.get("tags", [])),
    )
    pieces, kinds = puzzle.exercise()
    return set(pieces), set(kinds)


def report() -> None:
    items = json.loads(DATA.read_text(encoding="utf-8"))
    by_level: dict[str, int] = {}
    pieces: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for item in items:
        by_level[item["difficulty"]] = by_level.get(item["difficulty"], 0) + 1
        item_pieces, item_kinds = coverage_of(item)
        for kind in item_pieces:
            pieces[kind] = pieces.get(kind, 0) + 1
        for kind in item_kinds:
            kinds[kind] = kinds.get(kind, 0) + 1
    print(f"题目总数 {len(items)}")
    print("  难度分布:", ", ".join(f"{k}={v}" for k, v in sorted(by_level.items())))
    print("  子力覆盖:", ", ".join(f"{k}={v}" for k, v in sorted(pieces.items())) or "（空）")
    print("  吃法覆盖:", ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "（无吃子）")
    missing = [kind.value for kind in PieceType if kind.value not in pieces]
    print("  未覆盖子力:", ", ".join(missing) or "无")
    failures = [p for item in items for p in check_puzzle(item)]
    print("  校验:", "全部通过" if not failures else f"{len(failures)} 个问题")
    for failure in failures:
        print("   -", failure)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true",
                        help="校验全部题目并打印覆盖度矩阵（默认行为）")
    parser.add_argument("--inline", action="store_true",
                        help="把 positionMoves 前缀就地换成内联 document（幂等）")
    args = parser.parse_args()
    if args.inline:
        inline_documents()
    report()
