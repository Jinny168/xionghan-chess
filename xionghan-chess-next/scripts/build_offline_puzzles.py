"""把内置题库导出成 Android 离线包能吃的 JS 数据（`offline-puzzles.js`）。

## 为什么需要这个脚本

Android 端是 WebView 壳，跑的是 `android/Resources/assets/offline/` 下的离线包。
那份包里原先有 3 条**手写**的 `OFFLINE_PUZZLES`，每条只是「在开局局面下走一步」，
和桌面端 16 条真实残局完全不是一回事 —— 同一款游戏，两端练的东西不一样。

这里把 `core/data/puzzles.json`（唯一数据源）导出成 JS 常量，离线包用
`gameFromDocument()` 载入真实题面，于是三端练的是同一套题。

用法：
    python scripts/build_offline_puzzles.py            # 重新生成
    python scripts/build_offline_puzzles.py --check    # 只校验是否与数据源一致
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xionghan_chess.core.puzzles import load_puzzles, move_to_dict  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"
OUTPUT = ROOT / "android" / "Resources" / "assets" / "offline" / "offline-puzzles.js"

HEADER = """'use strict';
// 由 scripts/build_offline_puzzles.py 生成，**请勿手改**。
// 数据源：src/xionghan_chess/core/data/puzzles.json（与桌面端/服务端同一份题库）。
"""


def _stable_ids(value: object, counter: list[int] | None = None) -> object:
    """给棋子重编稳定 id。

    原题目里 `piece.id` 是每次构造 `Game` 时随机生成的（老 9 条题没有内联
    document，加载器会现建一局），直接导出会让每次产物都不同、`--check` 永远
    失败。这里按遍历顺序重编 `p0001…`：结构不变时编号就不变，两端的规则只要求
    id 唯一且稳定，不要求它是随机值。
    """
    if counter is None:
        counter = [0]
    if isinstance(value, dict):
        if {"id", "type", "color", "row", "col"} <= set(value):
            counter[0] += 1
            normalized = {"id": f"p{counter[0]:04d}"}
            normalized.update({k: _stable_ids(v, counter) for k, v in value.items() if k != "id"})
            return normalized
        return {k: _stable_ids(v, counter) for k, v in value.items()}
    if isinstance(value, list):
        return [_stable_ids(item, counter) for item in value]
    return value


def build_payload() -> list[dict]:
    """取 `load_puzzles()` 的结果 —— 老题目没有内联 document，加载器会按 profile 构建。

    直接用原始 JSON 会拿到「没有 document」的条目（原有 9 条就是这种），
    所以这里统一走加载器，两端看到的题面才是同一个。
    """
    payload: list[dict] = []
    for puzzle in load_puzzles():
        # `savedAt` 是加载时现写的当前时间，留着会让每次生成的产物都不同，
        # `--check` 就永远失败。题目是固定题面，这个字段本就没有意义。
        document = _stable_ids({key: value for key, value in puzzle.document.items()
                               if key != "savedAt"})
        payload.append({
            "id": puzzle.id,
            "title": puzzle.title,
            "difficulty": puzzle.difficulty,
            "description": puzzle.description,
            "hints": list(puzzle.hints),
            "solution": [move_to_dict(move) for move in puzzle.solution],
            "document": document,
        })
    return payload


def render(payload: list[dict]) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"{HEADER}window.XH_OFFLINE_PUZZLES = {body};\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验生成物是否最新")
    args = parser.parse_args()

    payload = build_payload()
    content = render(payload)
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != content:
            print("离线题库与数据源不一致，请重新生成：python scripts/build_offline_puzzles.py")
            return 1
        print(f"OFFLINE_PUZZLES_OK  {len(payload)} 条")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"已生成 {OUTPUT.relative_to(ROOT)}  {len(payload)} 条  {size_kb:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
