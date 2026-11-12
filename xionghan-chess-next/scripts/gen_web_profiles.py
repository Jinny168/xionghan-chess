"""从 Python `core/profiles.py` 生成网页端规则档案的**唯一源**。

只生成一份产物：`webapp/js/core/profiles.js`（ES module）。
另有 `webapp/js/core/profiles.manifest.json` 记录产物/内核 hash，供
`gen_rule_fixtures.py` 与 `build_webapp_bundle.py --check` 做前置断言。

范式照抄 `scripts/gen_offline_data.py`：
    python scripts/gen_web_profiles.py --write    # 重写 profiles.js + manifest
    python scripts/gen_web_profiles.py --check    # 只校验，漂移则 exit 1

为什么必须同源（A-2 实跑反证）：旧 `profiles.js::mergeOptions` 第 91-93 行是
`for (const key of Object.keys(normalized)) { if (key in result) ... }`，
`key in result` 会**过滤未知键**。实测
`mergeOptions(DEFAULT_OPTIONS, {pawn_three_line_capture: true})`
→ `p3l in result ? false / value = undefined`。不先重建档案，fixtures 里的
`p3l: true` 会被 `verify-rules.mjs` 的 `buildEngine → mergeOptions` 静默丢弃，
整个 removals 护栏必然空跑。

`--check` 的 8 条断言全部**从产物的 JS 文本里读回再比**，而不是只比
"生成函数自己的输出" —— 后者在脚本内硬编码第二份值时同样会绿。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.profiles import (  # noqa: E402
    BLACK_NAMES,
    CLASSIC_OPTIONS,
    COMPLETE_OPTIONS,
    NEGATED_OPTIONS,
    OPTION_ALIASES,
    PROFILES,
    RED_NAMES,
    RULE_VERSION,
    WEB_OPTIONS,
    RuleOptions,
    action_requirements,
    option_dependencies,
)

TARGET = ROOT / "webapp" / "js" / "core" / "profiles.js"
MANIFEST = ROOT / "webapp" / "js" / "core" / "profiles.manifest.json"
RULES_JS = ROOT / "webapp" / "js" / "core" / "rules.js"
GENERATED_BY = "scripts/gen_web_profiles.py"

# UI 展示元数据：Python `core/profiles.py` 不持有这些字段（它们不是规则口径，
# 只是设置页的短标题与说明）。本轮「展示/文案项全部延后」，故逐字保留
# 旧 profiles.js 的原文，不参与 §2.3 的 8 条规则数据比对。
UI_META = {
    "desktop_complete": {
        "shortTitle": "完整",
        "description": "十四种棋子全部登场，规则最完整，接近桌面原版。",
    },
    "desktop_classic": {
        "shortTitle": "经典",
        "description": "保留射、檑、巡，去掉甲、刺、楯，节奏更接近传统象棋。",
    },
    "web": {
        "shortTitle": "精简",
        "description": "只有射与檑两枚特色棋子，规则最好懂，适合首次上手。",
    },
    "traditional": {
        "shortTitle": "传统",
        "description": "标准 9×10 中国象棋，用来对照手感与验证内核通用性。",
    },
}


def _js(value: object) -> str:
    """紧凑 JSON —— 同时是合法的 JS 对象字面量，`--check` 能 json.loads 读回。"""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def option_keys() -> list[str]:
    """规范键集：`RuleOptions` 的全部字段（排序后）。"""
    return sorted(asdict(RuleOptions()))


def options_digest() -> str:
    """规范键集摘要。profiles.manifest.json 与 fixtures manifest 共用同一口径。"""
    return hashlib.sha256(json.dumps(option_keys(), separators=(",", ":")).encode("utf-8")).hexdigest()


def _names(mapping) -> dict[str, str]:
    return {key.value: value for key, value in mapping.items()}


def profile_data() -> list[dict[str, object]]:
    """每档的 options / pieces / enabledPieceTypes / rows / cols 全部取自 Python。"""
    out: list[dict[str, object]] = []
    for profile in PROFILES.values():
        out.append(
            {
                "id": profile.id,
                "title": profile.title,
                # UI 展示元数据（非规则口径），见 UI_META 注释
                "shortTitle": UI_META[profile.id]["shortTitle"],
                "description": UI_META[profile.id]["description"],
                "rows": profile.rows,
                "cols": profile.cols,
                "options": asdict(profile.options),
                "pieces": [
                    {"type": spec.type.value, "color": spec.color.value, "row": spec.row, "col": spec.col}
                    for spec in profile.pieces
                ],
                "enabledPieceTypes": sorted(kind.value for kind in profile.enabled_piece_types),
            }
        )
    return out


def payload() -> dict[str, object]:
    """全部生成数据 —— 键与 JS 里 `export const <键>` 一一对应。"""
    return {
        "RULE_VERSION": RULE_VERSION,
        "DEFAULT_OPTIONS": asdict(RuleOptions()),
        "COMPLETE_OPTIONS": asdict(COMPLETE_OPTIONS),
        "CLASSIC_OPTIONS": asdict(CLASSIC_OPTIONS),
        "WEB_OPTIONS": asdict(WEB_OPTIONS),
        "OPTION_ALIASES": dict(OPTION_ALIASES),
        "OPTION_DEPENDENCIES": option_dependencies(),
        "UI_ACTION_REQUIRES": action_requirements(),
        "NEGATED_OPTIONS": sorted(NEGATED_OPTIONS),
        "RED_NAMES": _names(RED_NAMES),
        "BLACK_NAMES": _names(BLACK_NAMES),
        "RULE_PROFILE_DATA": profile_data(),
    }


# 手写骨架：这些是 JS 侧的逻辑/便捷函数，Python core 没有对应实现，
# 与 `gen_offline_data.py` 的「规则实现仍是手写代码」同一分界线。
SCAFFOLD = '''
export const PROFILES = Object.fromEntries(RULE_PROFILE_DATA.map((data) => [data.id, data]));

export const PROFILE_ORDER = RULE_PROFILE_DATA.map((data) => data.id);

export function getProfile(id) {
  return PROFILES[id] || PROFILES.desktop_complete;
}

/** 合并规则开关：历史别名 → 当前键名；未知键一律丢弃（不污染引擎 options）。 */
export function mergeOptions(base, values) {
  const result = { ...base };
  if (!values) return result;
  const normalized = {};
  for (const [key, value] of Object.entries(values)) {
    if (['archer_weak_mode', 'sheWeakMode', 'she_weak_mode'].includes(key)) continue;
    normalized[OPTION_ALIASES[key] || key] = value;
  }
  if (!('archer_enhanced_mode' in normalized)) {
    for (const legacy of ['archer_weak_mode', 'sheWeakMode', 'she_weak_mode']) {
      if (legacy in values) {
        normalized.archer_enhanced_mode = !values[legacy];
        break;
      }
    }
  }
  normalized.king_appear = true;
  for (const key of Object.keys(normalized)) {
    if (key in result) result[key] = normalized[key];
  }
  return result;
}

export function pieceEnabled(options, type) {
  if (type === 'king') return true;
  return Boolean(options[`${type}_appear`]);
}

/** 返回某一档案下、按当前开关生效的初始棋子（不含 id，id 在开局时生成）。 */
export function initialPieceSpecs(profile, options) {
  return profile.pieces.filter((spec) => pieceEnabled(options, spec.type));
}

/** 星轨点位：弱化射只能沿对角星轨行走。 */
export function archerStarPoints(profile, options) {
  if (profile.rows !== 13 || profile.cols !== 13) return [];
  if (!profile.enabledPieceTypes.includes('archer')) return [];
  if (!pieceEnabled(options, 'archer')) return [];
  const points = [];
  for (let row = 0; row < profile.rows; row += 3) {
    for (let col = 0; col < profile.cols; col += 3) {
      if ((row / 3 + col / 3) % 2 === 0) points.push({ row, col });
    }
  }
  return points;
}

export function profileToClient(profile) {
  return {
    id: profile.id,
    title: profile.title,
    shortTitle: profile.shortTitle,
    rows: profile.rows,
    cols: profile.cols,
    description: profile.description,
    enabledPieceTypes: profile.enabledPieceTypes.slice(),
    pieceSlots: profile.pieces
      .filter((spec) => spec.color === 'red')
      .map((spec) => ({ id: `${spec.color}:${spec.type}:${spec.row}:${spec.col}`, ...spec })),
    options: { ...profile.options },
  };
}
'''


START = "// <generated:web-profiles>"
END = "// </generated:web-profiles>"


def generated_source() -> str:
    header = (
        "/**\n"
        " * 规则档案与规则开关 —— **由 `scripts/gen_web_profiles.py` 从 Python `core/profiles.py` 生成**。\n"
        " *\n"
        " * 请勿手改本文件：所有规则口径（选项默认值、别名、依赖表、名称表、\n"
        " * 开局摆子、启用兵种）只有 Python core 一份。改规则请改 core，再跑\n"
        " *   python scripts/gen_web_profiles.py --write\n"
        " *\n"
        " * 四套档案共用同一套走法判定，只在棋盘尺寸、初始棋子、可用棋种与\n"
        " * 默认开关上不同 —— 这是本项目「一套内核、多种玩法」的核心设计。\n"
        " */\n"
        "\n"
        # 保留 PIECE_TYPES import 以维持 bundle 的模块依赖图（model.js 先于 profiles.js 装载）；
        # 骨架本身不消费它，但删掉会改变 collect_modules 的顺序。
        "import { PIECE_TYPES } from './model.js';\n"
        "\n"
        f"{START}\n"
    )
    data_lines = "".join(f"export const {key} = {_js(value)};\n" for key, value in payload().items())
    return header + data_lines + f"{END}\n" + SCAFFOLD


def read_back(source: str) -> dict[str, object]:
    """只从 `<generated:web-profiles>` 区块内读回 `export const NAME = <json>;`。

    限定在区块内是必需的：骨架里也有 `export const PROFILES = ...`，
    扫全文会把 `Object.fromEntries(...)` 当 JSON 解析而误报。
    """
    if START not in source or END not in source:
        raise AssertionError("[profile-readback] 生成区标记缺失")
    block = source[source.index(START) + len(START):source.index(END)]
    found: dict[str, object] = {}
    for match in re.finditer(r"^export const (\w+) = (.+);$", block, re.MULTILINE):
        try:
            found[match.group(1)] = json.loads(match.group(2))
        except json.JSONDecodeError as exc:  # pragma: no cover - 产物被手改坏了
            raise AssertionError(f"[profile-readback] {match.group(1)} 不是合法 JSON: {exc}") from exc
    return found


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, object]:
    return {
        "ruleVersion": RULE_VERSION,
        "optionsDigest": options_digest(),
        "profilesHash": sha256(TARGET),
        "rulesHash": sha256(RULES_JS),
        "generatedBy": GENERATED_BY,
    }


def check() -> int:
    """8 条断言，任一不过即 exit 1。全部从**产物文本**读回，防脚本内硬编码第二份。"""
    problems: list[str] = []
    if not TARGET.exists():
        print(f"[profile-missing] {TARGET} 不存在 —— 先跑 --write", file=sys.stderr)
        return 1
    source = TARGET.read_text(encoding="utf-8")

    # ① 产物逐字节 == 生成结果（含行尾符）
    expected = generated_source()
    if source != expected:
        problems.append("[profile-source] 产物与生成结果不一致（含行尾符）—— 跑 --write")

    found = read_back(source)
    expected_payload = payload()

    # ② DEFAULT_OPTIONS 键集合 == set(asdict(RuleOptions()))
    default_js = found.get("DEFAULT_OPTIONS")
    canonical = set(asdict(RuleOptions()))
    if not isinstance(default_js, dict) or set(default_js) != canonical:
        problems.append(
            "[profile-keys] DEFAULT_OPTIONS 键集分叉："
            f"only-py={sorted(canonical - set(default_js or {}))} "
            f"only-js={sorted(set(default_js or {}) - canonical)}"
        )
    elif default_js != expected_payload["DEFAULT_OPTIONS"]:
        problems.append("[profile-values] DEFAULT_OPTIONS 逐值分叉")

    # ③ 三个 OPTIONS 与 Python 逐键值相等
    for name in ("COMPLETE_OPTIONS", "CLASSIC_OPTIONS", "WEB_OPTIONS"):
        if found.get(name) != expected_payload[name]:
            problems.append(f"[profile-values] {name} 与 Python 不逐键值相等")

    # ④ RULE_VERSION 相等
    if found.get("RULE_VERSION") != RULE_VERSION:
        problems.append(f"[rule-version] RULE_VERSION 分叉：js={found.get('RULE_VERSION')} py={RULE_VERSION}")

    # ⑤ OPTION_ALIASES 全表相等
    if found.get("OPTION_ALIASES") != dict(OPTION_ALIASES):
        problems.append("[profile-aliases] OPTION_ALIASES 全表分叉")
    # 附：已删除的兵种别名不得复活（pawn_full_movement_at_base 指向不存在的键）
    aliases = found.get("OPTION_ALIASES") or {}
    if any(key == "pawn_full_movement_at_base" or value == "pawn_full_movement_at_base"
           for key, value in aliases.items()):
        problems.append("[profile-aliases] pawn_full_movement_at_base 别名条目未删除")

    # ⑥ OPTION_DEPENDENCIES / UI_ACTION_REQUIRES / NEGATED_OPTIONS 相等
    for name, py_value in (
        ("OPTION_DEPENDENCIES", option_dependencies()),
        ("UI_ACTION_REQUIRES", action_requirements()),
        ("NEGATED_OPTIONS", sorted(NEGATED_OPTIONS)),
    ):
        if found.get(name) != py_value:
            problems.append(f"[profile-tables] {name} 分叉")

    # ⑦ PROFILES[id].options/pieces/enabledPieceTypes（+rows/cols）相等
    js_profiles = {item["id"]: item for item in (found.get("RULE_PROFILE_DATA") or [])}
    py_profiles = {item["id"]: item for item in profile_data()}
    if set(js_profiles) != set(py_profiles):
        problems.append(f"[profile-set] 档案集合分叉：{sorted(set(js_profiles) ^ set(py_profiles))}")
    else:
        for pid, py in py_profiles.items():
            js = js_profiles[pid]
            for key in ("options", "pieces", "enabledPieceTypes", "rows", "cols"):
                if js.get(key) != py[key]:
                    problems.append(f"[profile-values] PROFILES[{pid}].{key} 分叉")

    # ⑧ RED_NAMES / BLACK_NAMES 相等
    for name, py_value in (("RED_NAMES", _names(RED_NAMES)), ("BLACK_NAMES", _names(BLACK_NAMES))):
        if found.get(name) != py_value:
            problems.append(f"[profile-names] {name} 分叉")

    # manifest 链完整且与当前产物/内核一致
    if not MANIFEST.exists():
        problems.append("[manifest] profiles.manifest.json 缺失 —— 跑 --write")
    else:
        current = json.loads(MANIFEST.read_text(encoding="utf-8"))
        wanted = manifest()
        if current != wanted:
            problems.append("[manifest] 与当前产物/内核 hash 不一致 —— 跑 --write")

    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        print(f"\ngen_web_profiles --check FAILED: {len(problems)} 处；下一步：python {GENERATED_BY} --write",
              file=sys.stderr)
        return 1
    print(f"web profiles ok: {TARGET}")
    print(f"  ruleVersion={RULE_VERSION} optionsDigest={options_digest()[:12]}…")
    print(f"  profilesHash={sha256(TARGET)[:12]}… rulesHash={sha256(RULES_JS)[:12]}…")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.check):
        parser.error("one of --write/--check is required")
    if args.check:
        return check()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(generated_source(), encoding="utf-8", newline="\n")
    # manifest 的 hash 依赖刚写好的产物，必须在写盘之后计算
    MANIFEST.write_text(
        json.dumps(manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"wrote {TARGET}")
    print(f"wrote {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
