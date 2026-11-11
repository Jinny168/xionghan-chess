"""把「移除集合指纹」写盘：`tests/fixtures/removal_fingerprint.json`。

局面构造在 `tests/_removal_cases.py`（纯函数、测试与脚本共用同一份），这里只负责
算摘要 + 序列化。**不要把构造逻辑搬进来**：那样测试就得 subprocess 调脚本，既慢又多一层。

用法：
    python scripts/gen_removal_fingerprint.py --write   # 重写基线
    python scripts/gen_removal_fingerprint.py           # 只打印摘要与耗时，不写
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from _removal_cases import GENERATOR_VERSION, build_cases  # noqa: E402

from xionghan_chess.core.model import Color, GameState, Piece, PieceType  # noqa: E402
from xionghan_chess.core.profiles import RULE_VERSION, get_profile  # noqa: E402
from xionghan_chess.core.rules import RulesEngine  # noqa: E402

TARGET = ROOT / "tests" / "fixtures" / "removal_fingerprint.json"


def _engine(case: dict) -> tuple[RulesEngine, GameState]:
    profile = get_profile(case["profileId"])
    rules = RulesEngine(profile, profile.options.merged(case["options"]))
    pieces = [
        Piece.create(PieceType(kind), Color(color), row, col) for color, kind, row, col in case["pieces"]
    ]
    state = GameState(
        case["profileId"], pieces, turn=Color(case["turn"]), captured={Color.RED: [], Color.BLACK: []}
    )
    return rules, state


def case_digest(case: dict) -> dict:
    """一个 case 的三类摘要。

    - `perft1`  合法着法**条数**（整数）。不做复合摘要：`core/perft.py` 的语义就是"数叶子"，
      同一概念两个定义会立刻开始漂。
    - `capturable` 「谁能吃到谁」。**含 kind** —— 直接吃与三连旁吃是两回事，混掉就分不出来。
      格式 `r,c:kind:o.r:o.c>l.r:l.c`，按被吃子所在格排序；同一格多条用 `;` 连接。
    - `removals`  对**全部**合法着法逐一 `captured_by_move` 取并集（不是抽样）。**不含 kind**：
      `captured_by_move` 返回的是 `Piece` 元组，拿 kind 得碰私有的 `_apply_move`，不值得。
      kind 已由 `capturable` 覆盖，两者互补不重复。
    """
    rules, state = _engine(case)
    moves = rules.legal_moves(state)

    capturable: list[str] = []
    for position, spec in sorted(rules.capturable_squares(state, state.turn).items(), key=lambda kv: (kv[0].row, kv[0].col)):
        entries = [
            f"{position.row},{position.col}:{removal.kind.value}:"
            f"{removal.origin.row},{removal.origin.col}>{removal.landing.row},{removal.landing.col}"
            for removal in spec.removals
        ]
        capturable.extend(entries)

    removals: list[str] = []
    for move in moves:
        for victim in rules.captured_by_move(state, move):
            removals.append(
                f"{move.source.row}:{move.source.col}>{move.target.row}:{move.target.col}:"
                f"{victim.position.row}:{victim.position.col}"
            )

    return {
        "perft1": len(moves),
        "capturable": ";".join(sorted(capturable)),
        "removals": ";".join(sorted(removals)),
    }


def fingerprint() -> dict:
    """整份基线。case id 就是键 —— 加维度会让 id 集合变化，门禁立刻红。"""
    return {
        "ruleVersion": RULE_VERSION,
        "generatorVersion": GENERATOR_VERSION,
        "cases": {case["id"]: case_digest(case) for case in build_cases()},
    }


def main() -> int:
    write = "--write" in sys.argv[1:]
    started = time.perf_counter()
    payload = fingerprint()
    elapsed = time.perf_counter() - started
    moves = sum(case["perft1"] for case in payload["cases"].values())
    summary = f"{len(payload['cases'])} cases / {moves} moves / {elapsed:.2f}s"
    if not write:
        print(f"[removal-fingerprint] {summary}（未写盘，加 --write 才落盘）")
        return 0
    TARGET.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"[removal-fingerprint] wrote {TARGET.relative_to(ROOT)} — {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
