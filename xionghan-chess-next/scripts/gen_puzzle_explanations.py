"""从创意侧文案生成 35 道真题的「为什么」解析数据（文案的唯一可复现来源）。

文案源：`docs/PUZZLE_EXPLANATIONS_2026-11-25.md`（创意侧产出，本脚本只读）。
产物两份，内容同源：
  1. `src/xionghan_chess/core/data/puzzle_explanations.json` —— 桌面/Python 侧读取；
  2. `webapp/js/data/puzzle_explanations.js` —— Webapp 侧 import。

**不改 `puzzles.json`**：解析是文案，不是题库数据；下次改文案只需重跑本脚本。
文末「数据存疑清单」章节不解析（它记录的是题库与题面描述的差异，不是给玩家的文案）。

用法（与 `scripts/gen_web_profiles.py` 同惯例）：
    python scripts/gen_puzzle_explanations.py --write   # 重写两份产物
    python scripts/gen_puzzle_explanations.py --check   # 只校验，漂移则 exit 1

`--check` 每次都从 Markdown 重新解析，再与磁盘上的 JSON / JS 逐字比对 ——
不只比「脚本自己的返回值」，防止脚本内硬编码第二份数据造成假绿。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "PUZZLE_EXPLANATIONS_2026-11-25.md"
JSON_TARGET = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzle_explanations.json"
JS_TARGET = ROOT / "webapp" / "js" / "data" / "puzzle_explanations.js"

HEADING_RE = re.compile(r"^### (?P<id>gen-\d{2}) · (?P<title>.+)$")
STOP_HEADING = "## 数据存疑清单"
EXPECTED_IDS = tuple(f"gen-{number:02d}" for number in range(1, 36))
JS_HEADER = (
    "/**\n"
    " * 35 道真题的非权威「为什么」解析 —— 由 `scripts/gen_puzzle_explanations.py` 生成，请勿手改。\n"
    " * 文案源：docs/PUZZLE_EXPLANATIONS_2026-11-25.md（只读）。题库数据仍只在 puzzles.json。\n"
    " */\n"
)


def parse_source() -> dict[str, dict[str, str]]:
    """逐段解析 Markdown；任何结构异常都直接报错，不静默吞掉。"""
    text = SOURCE.read_text(encoding="utf-8")
    if STOP_HEADING not in text:
        raise AssertionError(f"[parse] 文案缺少收尾章节 {STOP_HEADING!r}")
    body = text.split(STOP_HEADING, 1)[0]

    found: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("### "):
            match = HEADING_RE.match(line)
            if not match:
                raise AssertionError(f"[parse] 非法段标题：{line!r}")
            current = match.group("id")
            if current in found:
                raise AssertionError(f"[parse] 重复题号：{current}")
            found[current] = {}
            continue
        if line.startswith("## "):
            current = None
            continue
        if current is None or not line.startswith("- "):
            continue
        for field, label in (("key_move", "关键手"), ("why", "为什么")):
            prefix = f"- {label}："
            if line.startswith(prefix):
                if field in found[current]:
                    raise AssertionError(f"[parse] {current} 重复字段 {label}")
                found[current][field] = line[len(prefix):].strip()

    ids = tuple(sorted(found))
    if ids != EXPECTED_IDS:
        missing = sorted(set(EXPECTED_IDS) - set(ids))
        extra = sorted(set(ids) - set(EXPECTED_IDS))
        raise AssertionError(f"[parse] 题号集合分叉：missing={missing} extra={extra}")
    for puzzle_id, item in found.items():
        for field in ("key_move", "why"):
            value = item.get(field)
            if not value:
                raise AssertionError(f"[parse] {puzzle_id} 缺 {field}")
            if "你应该" in value or re.search(r"\d+\s*分", value):
                raise AssertionError(f"[parse] {puzzle_id} 的 {field} 出现指令式措辞或分值：{value!r}")
    return {key: found[key] for key in EXPECTED_IDS}


def json_text(data: dict[str, dict[str, str]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def js_text(data: dict[str, dict[str, str]]) -> str:
    return JS_HEADER + f"export const PUZZLE_EXPLANATIONS = {json.dumps(data, ensure_ascii=False, indent=2)};\n"


def check() -> int:
    data = parse_source()
    problems: list[str] = []
    for path, expected in ((JSON_TARGET, json_text(data)), (JS_TARGET, js_text(data))):
        if not path.exists():
            problems.append(f"[explanation-missing] {path.relative_to(ROOT)} 不存在 —— 先跑 --write")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            first_difference = next(
                (index for index, (a, b) in enumerate(zip(actual, expected)) if a != b),
                min(len(actual), len(expected)),
            )
            problems.append(
                f"[explanation-drift] {path.relative_to(ROOT)} 与文案解析结果不一致 "
                f"(offset={first_difference}) —— 跑 --write"
            )
    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        print(f"\ngen_puzzle_explanations --check FAILED: {len(problems)} 处", file=sys.stderr)
        return 1
    print(f"puzzle explanations ok: {len(data)} 条 / {JSON_TARGET.relative_to(ROOT)} + {JS_TARGET.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not (args.write ^ args.check):
        parser.error("exactly one of --write/--check is required")
    if args.check:
        return check()
    data = parse_source()
    JSON_TARGET.parent.mkdir(parents=True, exist_ok=True)
    JS_TARGET.parent.mkdir(parents=True, exist_ok=True)
    JSON_TARGET.write_text(json_text(data), encoding="utf-8", newline="\n")
    JS_TARGET.write_text(js_text(data), encoding="utf-8", newline="\n")
    print(f"wrote {JSON_TARGET.relative_to(ROOT)}")
    print(f"wrote {JS_TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
