"""题库体检：把「一条题算不算合格」变成可执行的检查。

为什么需要它：设计定稿给了 10 条验收标准，但其中「首着唯一」「每手最强」
「对手应着强制」三条要靠引擎算 —— 人工出题时最容易跳过这三条，而它们恰恰决定
一道题是"真的有唯一解"还是"随便走也能过"。

用法：
    python scripts/puzzle_doctor.py                # 检查全部题目（含引擎项）
    python scripts/puzzle_doctor.py --quick        # 只做静态检查（秒级）
    python scripts/puzzle_doctor.py --id endgame-cannon-screen-01

退出码：有任一题目不合格则 1。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.ai import ChessAI, Difficulty  # noqa: E402
from xionghan_chess.core.game import Game, GameError  # noqa: E402
from xionghan_chess.core.model import Color, Move, Position  # noqa: E402
from xionghan_chess.core.puzzles import Puzzle, load_puzzles  # noqa: E402
from xionghan_chess.core.storage import game_from_document  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from author_puzzles import _all_lines as _forced_first_lines  # noqa: E402

# 判"被将死"时只看一步 —— 对手应着的强制性用"除它之外都会立刻被杀"来判
MATE_DEPTH = 1
# 坐标泄露只认这两种写法，别用「含行/列」这种粗判据
COORDINATE = re.compile(r"\(\s*\d+\s*[,，]\s*\d+\s*\)|第\s*\d+\s*[行列]")


def _apply(game: Game, move: Move) -> bool:
    """在自己的副本上试走一手；非法或会让局面无法继续就返回 False。"""
    try:
        game.move(move)
        return True
    except (GameError, ValueError):
        return False


def _is_mated(game: Game) -> bool:
    """轮到的一方是否已被将死（用"没有任何合法着法"近似）。"""
    if game.state.finished:
        return True
    return not game.rules.legal_moves(game.state, game.state.turn)


def _mate_in_one(game: Game) -> list[Move]:
    """当前轮走方有没有一步结束战斗的着法。

    每个候选都从 `document` 重新建一局：`Game` 没有可靠的 `clone`，
    而直接 `move` 会污染调用方的局面。
    """
    mates: list[Move] = []
    for move in game.rules.legal_moves(game.state, game.state.turn):
        probe = game_from_document(_document(game))
        if _apply(probe, move) and _is_mated(probe):
            mates.append(move)
    return mates


def _document(game: Game) -> dict:
    from xionghan_chess.core.storage import game_document
    return game_document(game)


def _fresh(puzzle: Puzzle) -> Game:
    return game_from_document(puzzle.document)


def check(puzzle: Puzzle, *, quick: bool) -> list[str]:
    """返回问题列表；空列表 = 合格。"""
    problems: list[str] = []
    total = len(puzzle.solution)

    # 1) 解法长度：必须奇数（偶数会停在对手刚走完）
    if total % 2 == 0:
        problems.append(f"解法 {total} ply 为偶数，会停在对手刚走完")

    # 2) 题面：载入后不能已经结束
    try:
        game = _fresh(puzzle)
    except Exception as exc:  # noqa: BLE001 - 坏文档要如实报出来
        return [f"题面无法载入：{exc}"]
    if game.state.finished:
        problems.append("题面载入即终局")
    if game.state.turn is not Color.RED and game.state.turn is not Color.BLACK:
        problems.append("题面轮走方异常")

    # 3) 解法逐步合法
    probe = game
    for index, move in enumerate(puzzle.solution):
        if not _apply(probe, move):
            problems.append(f"第 {index + 1} 手不合法：{move.key()}")
            break

    # 4) 提示条数与坐标泄露
    hands = (total + 1) // 2
    if len(puzzle.hints) < hands:
        problems.append(f"提示 {len(puzzle.hints)} 条 < 解方 {hands} 手")
    # 只抓真正的坐标写法：`(11,5)` / `第 3 行第 5 列`。
    # 不能简单搜"行/列"——中文里"强制执行"本身就含"行"，第一版就是这么误报的。
    for key in ("title", "description"):
        text = getattr(puzzle, key)
        if COORDINATE.search(text):
            problems.append(f"{key} 疑似泄露坐标：{text}")

    if quick:
        return problems

    # 5) 首着唯一：**按题目自己的深度数强制线**，而不是只数"一步杀"。
    #
    #    1 手题（1 ply）看"恰好一手能将死"；多步题（3/5/7 ply）首着本来就不将死，
    #    要看"有几条首着能强制杀到底"。用分数差判更是错的：静着局面里一堆着法
    #    分数完全相同（实测现有题库前三分 101/101/101、-5/-5/-5），差 0 只说明
    #    "随便走都差不多"，那恰恰说明它不是题。
    lines = _forced_first_lines(_fresh(puzzle), (total + 1) // 2, [4000])
    if not lines:
        problems.append("这不是杀题：没有任何着法能强制杀到底")
    elif len(lines) > 1:
        problems.append(f"能强制杀到底的首着有 {len(lines)} 手（应恰好 1 手）")
    elif lines[0][0].key() != puzzle.solution[0].key():
        problems.append(
            f"解法首着不是唯一解：题面写 {puzzle.solution[0].key()}，实际唯一首着 {lines[0][0].key()}")
    elif len(lines[0]) != total:
        problems.append(f"最强线长度 {len(lines[0])} ply，与解法 {total} ply 不一致")

    # 6) 每手最强 + 对手应着强制（逐 ply 走）
    walker = _fresh(puzzle)
    for index, move in enumerate(puzzle.solution):
        if index % 2 == 1:
            # 对手应着：除题面给定的那一手之外，还有几种"不会被立刻将死"的选择
            escapes = 0
            for candidate in walker.rules.legal_moves(walker.state, walker.state.turn):
                probe2 = game_from_document(_document(walker))
                if not _apply(probe2, candidate):
                    continue
                if not _mate_in_one(probe2):
                    escapes += 1
            if escapes > 1:
                problems.append(f"第 {index + 1} 手对手有 {escapes} 种不被将死的应法（应 ≤1）")
        if not _apply(walker, move):
            break

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="只做静态检查，不跑引擎")
    parser.add_argument("--id", action="append", help="只查指定题目（可重复）")
    parser.add_argument("--file", help="改查候选文件（出题器产出的 JSON 数组）")
    args = parser.parse_args()

    if args.file:
        # 出题器的产物还没入库，按同一套 Puzzle 结构解析
        from xionghan_chess.core.puzzles import Puzzle as _Puzzle
        raw = json.loads(Path(args.file).read_text(encoding="utf-8"))
        def _to_puzzle(item: dict) -> _Puzzle:
            return _Puzzle(
                str(item["id"]), str(item["title"]), str(item["difficulty"]),
                str(item.get("description", "")), dict(item["document"]),
                tuple(Move(Position(m["from"]["row"], m["from"]["col"]),
                           Position(m["to"]["row"], m["to"]["col"])) for m in item["solution"]),
                tuple(item.get("hints", [])), tuple(item.get("tags", [])),
            )
        puzzles = [_to_puzzle(item) for item in raw]
    else:
        puzzles = load_puzzles()
    if args.id:
        wanted = set(args.id)
        puzzles = [item for item in puzzles if item.id in wanted]

    bad = 0
    for puzzle in puzzles:
        problems = check(puzzle, quick=args.quick)
        status = "OK" if not problems else "FAIL"
        print(f"[{status}] {puzzle.id:26s} {len(puzzle.solution)} ply  {puzzle.difficulty}")
        for problem in problems:
            print(f"       - {problem}")
        bad += 1 if problems else 0
    print(f"\n共 {len(puzzles)} 条，合格 {len(puzzles) - bad}，不合格 {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
