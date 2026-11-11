"""生成「移除集合指纹」基线：`tests/fixtures/removal_fingerprint.json`。

## 这个文件拦什么

`RULE_VERSION` 存在的理由只有一个：**走法语义变了，两端不能同桌、旧谱不能照读**。
可它有一个人性弱点 —— 改语义的人只要忘了 `+1`，一切照样绿：没有测试会因为
"某一步不再吃子"而红，因为**没有任何测试知道"应该吃哪些子"**。

这个指纹补的就是那一层：把一批**确定性生成**的局面上的
「合法着法」「谁能吃到谁」「每一步吃掉哪些子」三类摘要钉进基线。语义一动，
摘要必变，门禁红，红灯文案直接告诉你要同步 `RULE_VERSION` 与重生成基线。

## 为什么是"确定性解空间"而不是手写用例

手写用例只能覆盖你想到的口径；三连吃子这种"窗口 × 位移 × 长短线"的组合，
漏一条就是一个沉默的语义漂移。用固定种子扫一批稀疏局面，能把组合面铺开，
而"固定种子 + 排序后规范化"保证同一份代码每次算出同一个摘要（可复现、可 review）。

## 口径

- 摘要一律 **sha256 前 16 位十六进制**，输入是**排序后**的规范化字符串；
- 被吃子只记 `(color, type, row, col)`，**不记 id** —— `Piece.create` 的 id 不稳定，
  记进去等于把随机数写进基线；
- 局面规模刻意做小（≤8 枚子）：`captured_by_move` 每算一步都要 apply 一次，
  基线的价值在"覆盖面 × 跑得快"，不在单局复杂度（复杂局面对拍交给
  `tests/test_cross_engine.py`）。

用法：
    python scripts/gen_removal_fingerprint.py            # 重写基线
    python scripts/gen_removal_fingerprint.py --check     # 只打印摘要与耗时，不写
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.model import (  # noqa: E402
    Color,
    GameState,
    Piece,
    PieceType,
)
from xionghan_chess.core.profiles import RULE_VERSION, get_profile  # noqa: E402
from xionghan_chess.core.rules import RulesEngine  # noqa: E402

TARGET = ROOT / "tests" / "fixtures" / "removal_fingerprint.json"
SEED = 20260807
CASES_PER_PROFILE = 50  # 4 档案 × 50 = 200
DIGEST_LEN = 16

PROFILES = ("web", "desktop_complete", "desktop_classic", "traditional")

# 每个 case 会把这些开关按位"翻转"一下，让基线对开关也敏感（否则只钉住了默认档）。
TOGGLE_KEYS = (
    "pawn_three_line_capture",
    "pawn_charge",
    "pawn_fast_move_before_enemy_territory",
    "enforce_self_check",
)
PIECE_POOL = (
    PieceType.PAWN,
    PieceType.ROOK,
    PieceType.HORSE,
    PieceType.CANNON,
    PieceType.ADVISOR,
    PieceType.ELEPHANT,
    PieceType.GUARD,
    PieceType.ARCHER,
    PieceType.THUNDER,
    PieceType.PATROL,
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:DIGEST_LEN]


def _piece_key(piece: Piece) -> str:
    return f"{piece.color.value}:{piece.type.value}:{piece.position.row}:{piece.position.col}"


def build_cases() -> list[dict]:
    """确定性生成的一批局面（同种子 → 同结果）。

    布局刻意**聚簇**：棋子撒在棋盘各处时，能出现的吃子/三连组合少得可怜
    （实测：纯均匀撒 200 例，"可吃格"摘要全是空串哈希，基线等于什么都没钉）。
    所以每例先随机一个 4..6 格见方的窗口，把子塞进窗口里，让"两我一敌成线"
    这类组合真的会发生；王单独留在各自后方，避免一开局就照面把着法表压空。
    """
    rng = random.Random(SEED)
    cases: list[dict] = []
    for profile_id in PROFILES:
        profile = get_profile(profile_id)
        rows, cols = profile.rows, profile.cols
        for index in range(CASES_PER_PROFILE):
            occupied: set[tuple[int, int]] = set()
            pieces: list[Piece] = []
            for color, row_range in ((Color.RED, (rows - 3, rows - 1)), (Color.BLACK, (0, 2))):
                for _attempt in range(64):
                    row = rng.randint(*row_range)
                    col = rng.randint(2, cols - 3)
                    if (row, col) not in occupied:
                        occupied.add((row, col))
                        pieces.append(Piece.create(PieceType.KING, color, row, col))
                        break
            # 窗口边长受棋盘限制：窄盘（9 列）不能照搬 6，否则 randint 区间为空。
            span = rng.randint(4, max(4, min(6, min(rows, cols) - 5)))
            base_row = rng.randint(2, rows - span - 2)
            base_col = rng.randint(2, cols - span - 2)
            # 兵占多数：三连吃子只认兵，兵太少就测不到它。
            layout = [PieceType.PAWN] * rng.randint(2, 4) + [
                rng.choice(PIECE_POOL) for _ in range(rng.randint(1, 3))
            ]
            rng.shuffle(layout)
            for kind in layout:
                for _attempt in range(48):
                    row = base_row + rng.randint(0, span - 1)
                    col = base_col + rng.randint(0, span - 1)
                    if (row, col) not in occupied:
                        occupied.add((row, col))
                        pieces.append(Piece.create(kind, rng.choice((Color.RED, Color.BLACK)), row, col))
                        break
            options = {
                key: bool((index >> offset) & 1) for offset, key in enumerate(TOGGLE_KEYS)
            }
            cases.append(
                {
                    "id": f"{profile_id}#{index:03d}",
                    "profileId": profile_id,
                    "options": options,
                    "turn": (Color.RED if index % 2 == 0 else Color.BLACK).value,
                    "pieces": [
                        [p.color.value, p.type.value, p.position.row, p.position.col]
                        for p in sorted(pieces, key=_piece_key)
                    ],
                }
            )
    return cases


def case_digests(case: dict) -> dict:
    """算一个局面的三类摘要。"""
    profile = get_profile(case["profileId"])
    options = profile.options.merged(case["options"])
    rules = RulesEngine(profile, options)
    pieces = [
        Piece.create(PieceType(kind), Color(color), row, col)
        for color, kind, row, col in case["pieces"]
    ]
    state = GameState(
        case["profileId"],
        pieces,
        turn=Color(case["turn"]),
        captured={Color.RED: [], Color.BLACK: []},
    )

    moves = rules.legal_moves(state)
    legal_lines = sorted(
        f"{m.source.row},{m.source.col}>{m.target.row},{m.target.col}"
        f"{':' + m.promotion.value if m.promotion else ''}"
        for m in moves
    )

    # 「谁能吃到谁」：键是被吃子所在格，值是每条移除路径（kind + 起点 + 落点）。
    specs = rules.capturable_squares(state, state.turn)
    spec_lines = []
    for position, spec in specs.items():
        for removal in spec.removals:
            spec_lines.append(
                f"{position.row},{position.col}|{removal.kind.value}|"
                f"{removal.victim_type.value}:{removal.victim_color.value}|"
                f"{removal.origin.row},{removal.origin.col}>{removal.landing.row},{removal.landing.col}"
            )
    spec_lines.sort()

    # 「每一步吃掉哪些子」：只记被吃子的 (颜色, 种类, 位置)，不记 id。
    removal_lines = []
    for move in sorted(moves, key=lambda m: (m.source.row, m.source.col, m.target.row, m.target.col)):
        victims = sorted(_piece_key(p) for p in rules.captured_by_move(state, move))
        removal_lines.append(
            f"{move.source.row},{move.source.col}>{move.target.row},{move.target.col}"
            f"={'/'.join(victims)}"
        )

    return {
        "perft1": len(moves),
        "legalDigest": _digest("\n".join(legal_lines)),
        "capturableDigest": _digest("\n".join(spec_lines)),
        "capturedByMoveDigest": _digest("\n".join(removal_lines)),
        # 这一例里出现过哪些吃法。写进基线是为了让"基线自身覆盖了什么"可 review ——
        # 一份连三连吃子都没出现过的基线，钉不住三连吃子的语义（第一版就是这个毛病）。
        "kinds": sorted({removal.kind.value for spec in specs.values() for removal in spec.removals}),
    }


def fingerprint() -> dict:
    """整份基线（含 `ruleVersion` —— 它是这份基线的"适用前提"）。"""
    cases = build_cases()
    return {
        "ruleVersion": RULE_VERSION,
        "generator": "scripts/gen_removal_fingerprint.py",
        "seed": SEED,
        "caseCount": len(cases),
        "cases": [{**case, **case_digests(case)} for case in cases],
    }


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    started = time.perf_counter()
    payload = fingerprint()
    elapsed = time.perf_counter() - started
    if check_only:
        print(f"cases={payload['caseCount']} ruleVersion={payload['ruleVersion']} "
              f"elapsed={elapsed:.2f}s")
        print(_digest(json.dumps(payload, sort_keys=True, ensure_ascii=False)))
        return 0
    TARGET.write_text(json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)} cases={payload['caseCount']} "
          f"ruleVersion={payload['ruleVersion']} elapsed={elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
