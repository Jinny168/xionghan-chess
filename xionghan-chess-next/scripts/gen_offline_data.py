"""从 Python core 生成 Android 离线镜像的数据区（S5 数据层 codegen）。

只生成「数据」：TYPES / NAMES / DEFAULT_OPTIONS / PROFILE_DATA。
规则实现、`piece()`、`starPoints()` 与 `PROFILES` 构建仍是手写代码。

用法：
    python scripts/gen_offline_data.py --write   # 重写 offline.js 的生成区块
    python scripts/gen_offline_data.py --check   # 只校验，漂移则 exit 1

生成区块的边界由两个注释标记界定；`offline_rules_probe.cjs` 仍从
`const TYPES=` 切到 `const canvas=`，所以生成内容必须留在该区间内。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.model import PieceType  # noqa: E402
from xionghan_chess.core.profiles import PROFILES  # noqa: E402

TARGET = ROOT / "android" / "Resources" / "assets" / "offline" / "offline.js"
START = "// <generated:offline-data>"
END = "// </generated:offline-data>"

TYPES = [kind.value for kind in PieceType]


def _js(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _profile_payload() -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for profile in PROFILES.values():
        options = asdict(profile.options)
        for kind in TYPES:
            if kind not in {item.value for item in profile.enabled_piece_types}:
                options[f"{kind}_appear"] = False
        pieces = [
            [piece.type.value, piece.color.value, piece.row, piece.col]
            for piece in profile.pieces
            if piece.type in profile.enabled_piece_types
        ]
        enabled = [kind for kind in TYPES if kind in {item.value for item in profile.enabled_piece_types}]
        payload.append({
            "id": profile.id,
            "title": profile.title,
            "rows": profile.rows,
            "cols": profile.cols,
            "enabled": enabled,
            "options": options,
            "pieces": pieces,
        })
    return payload


def generated_block() -> str:
    names = {
        "red": {kind.value: name for kind, name in PROFILES["desktop_complete"].red_names.items()},
        "black": {kind.value: name for kind, name in PROFILES["desktop_complete"].black_names.items()},
    }
    default_options = asdict(PROFILES["desktop_complete"].options)
    for kind in TYPES:
        default_options.setdefault(f"{kind}_appear", True)
    return "\n".join([
        START,
        f"const TYPES={_js(TYPES)};",
        f"const NAMES={_js(names)};",
        f"const DEFAULT_OPTIONS={_js(default_options)};",
        f"const PROFILE_DATA={_js(_profile_payload())};",
        END,
    ])


def scaffolding_block() -> str:
    return "\n".join([
        "let idCounter=0;",
        "function piece(type,color,row,col){return{id:`offline-${++idCounter}`,type,color,row,col}}",
        "function starPoints(){const points=[];for(let r=0;r<13;r+=3)for(let c=0;c<13;c+=3)if((r/3+c/3)%2===0)points.push(pos(r,c));return points}",
        "const PROFILES=new Map(PROFILE_DATA.map(data=>[data.id,{id:data.id,title:data.title,rows:data.rows,cols:data.cols,pieces:data.pieces.map(([type,color,row,col])=>piece(type,color,row,col)),enabled:data.enabled,options:{...DEFAULT_OPTIONS,...data.options},archerStarPoints:data.rows===13&&data.enabled.includes('archer')?starPoints():[]}]));",
    ])


def replace_block(source: str) -> str:
    if START in source and END in source:
        start = source.index(START)
        end = source.index(END) + len(END)
        return source[:start] + generated_block() + source[end:]
    # 首次迁移：从手写数据区起点替换到 FEN_PIECES 之前（旧 side/profile 一并移除）。
    start_marker = "const TYPES="
    end_marker = "const FEN_PIECES="
    start = source.index(start_marker)
    end = source.index(end_marker)
    return source[:start] + generated_block() + "\n" + scaffolding_block() + "\n" + source[end:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.check):
        parser.error("one of --write/--check is required")
    source = TARGET.read_text(encoding="utf-8")
    updated = replace_block(source)
    if args.check:
        if updated != source:
            print(f"offline data drift: {TARGET}", file=sys.stderr)
            return 1
        print(f"offline data ok: {TARGET}")
        return 0
    TARGET.write_text(updated, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
