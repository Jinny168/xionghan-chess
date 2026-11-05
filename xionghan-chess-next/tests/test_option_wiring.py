"""C-2 开关完整性守卫：`RuleOptions` 的每个字段都必须「被三端 UI 覆盖，或被显式豁免」。

## 为什么需要这个守卫

`RuleOptions` 是规则引擎的唯一开关面板（`core/profiles.py`，当前 32 个字段）。
加一个字段只改 `core/` 是**能跑通全部测试**的——规则引擎会认这个新开关，
AI / 对拍 / 存档全都照常工作——但用户在三个设置界面里根本看不到它，
于是这个功能对玩家来说等于不存在。这是本项目最容易「静默漏接」的一类缺陷：
缺的是 UI，红的却不是测试。

所以这里反向断言：**新字段必须出现在三端分组里，否则必须在豁免表里写明理由。**
豁免表是白名单，不是垃圾桶：每条都要求给出判据（见 `EXEMPT`），
并把理由写进注释与 `reason` 字段，供 review 时逐条质疑。

## 「三端分组」的取法

1. 桌面①：`desktop/ui/piece_atlas.py::PIECE_OPTION_KEYS` —— 直接 import。
2. 桌面②：`desktop/ui/dialogs.py` 里 `SettingsDialog` 的 `piece_definitions` ——
   它是 `__init__` 内的**局部字面量**（跟着界面布局一起写，刻意不抽模块常量），
   无法 import，故用 `ast` 从源码解析出真实的字面量再求值。
   *不硬编码副本*：数据仍只有源码一份，解析只是读它。
3. 网页：`web/js/app.js::pieceRuleKeys` —— 同样只从源码解析，不复制粘贴。

## 「内容完全一致」的含义

三端的分组必须**键集合相同、挂载的棋子分组也相同**（6 组 / 18 键：
king 4 · horse 3 · elephant 2 · advisor 2 · pawn 6 · archer 1）。
只比键集合不够——把「马的别腿」挂到「兵」下面，键集合照样是全的，但界面是错的。

## 加规则开关的代价（故意的）

`EXPECTED_GROUP_KEYS` 是**定稿指纹**：以后新增一个 `RuleOptions` 字段，
除了改三端分组，还必须同时更新这份指纹。这是刻意设计——
它拦的是"三端一起漏"这种连一致性检查都过不了的情形（三端同时删掉某组，
一致性照样通过，但用户丢了功能）。
指纹里写着 19 个键与它们的归属，改它就是一次显式的产品变更声明，不该顺手改。
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import fields
from pathlib import Path

from xionghan_chess.core.model import PieceType
from xionghan_chess.core.profiles import RuleOptions

ROOT = Path(__file__).resolve().parents[1]
DIALOGS_PY = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "dialogs.py"
APP_JS = ROOT / "web" / "js" / "app.js"
LOCALES = ROOT / "locales"


# ---------------------------------------------------------------------------
# 豁免表：出现在 `RuleOptions` 里、但**不属于任何棋子分组**的字段。
#
# 三端都按 `kind.value + "_appear"` 生成登场开关，全局规则在「常规规则」区，
# 数值项在同一个区但用数字输入框 —— 它们不需要（也不该）进棋子分组，
# 所以这里显式登记，避免"漏接"与"本就不该接"混为一谈。
# 加新条目必须写理由：守卫会把理由当断言检查（空理由 = 红）。
# ---------------------------------------------------------------------------

EXEMPT: dict[str, str] = {
    # --- 全局规则：对所有棋子生效，放在「常规规则」区，不属于任何一枚棋子 ---
    "enforce_self_check": "全局规则：禁止送将，作用于所有走法，与具体兵种无关",
    "threefold_draw": "全局规则：三次重复判和，作用于整个对局而非某枚棋子",
    "no_progress_draw_plies": (
        "数值项（非布尔开关）：网页端用下拉框暴露（0/60/120/180/240），"
        "桌面端不提供调整入口（沿用默认 120，服务端限定 10..500）"
    ),
    # --- 登场开关：三端都用 f'{kind.value}_appear' 动态生成，无需手写分组 ---
    "rook_appear": "登场开关：网页/桌面均按 piece type 动态生成，不手写进分组",
    "horse_appear": "登场开关：同 rook_appear",
    "elephant_appear": "登场开关：同 rook_appear",
    "advisor_appear": "登场开关：同 rook_appear",
    "king_appear": "登场开关：恒为 True，界面只读（将/帅不可移除）",
    "cannon_appear": "登场开关：同 rook_appear",
    "pawn_appear": "登场开关：同 rook_appear",
    "guard_appear": "登场开关：同 rook_appear",
    "archer_appear": "登场开关：同 rook_appear",
    "thunder_appear": "登场开关：同 rook_appear",
    "patrol_appear": "登场开关：同 rook_appear",
}

# 三端「棋子分组」的期望形状：6 个非空分组 / 18 个规则键。
# 18（不是 19）是 2.0.0 的产品变更：`pawn_full_movement_at_base` 整项删除
# （它在默认配置下不改变任何走法，见 profiles.py 该处的注释）。
# 这是**当前定稿**的指纹，用来抓"三端一起漏掉某组"这种连一致性检查都过不了的情形
# （例如三端同时把兵的 7 个开关删了，键集合仍三端一致，但用户丢了功能）。
EXPECTED_GROUP_KEYS: dict[str, frozenset[str]] = {
    "king": frozenset({"king_can_leave_palace", "king_diagonal_in_palace",
                       "king_lose_diagonal_outside_palace", "invasion_victory"}),
    "horse": frozenset({"horse_blocked_by_leg", "horse_straight_three",
                        "horse_straight_three_move_only"}),
    "elephant": frozenset({"elephant_can_cross_river",
                           "elephant_gain_jump_two_enemy_territory"}),
    "advisor": frozenset({"advisor_can_leave_palace",
                          "advisor_gain_straight_outside_palace"}),
    "pawn": frozenset({"pawn_fast_move_before_enemy_territory", "pawn_charge",
                       "pawn_three_line_capture", "pawn_backward_at_base",
                       "pawn_resurrection", "pawn_promotion"}),
    "archer": frozenset({"archer_enhanced_mode"}),
}


def _all_fields() -> set[str]:
    return {field.name for field in fields(RuleOptions)}


# --- 三端分组读取 ---------------------------------------------------------


def desktop_atlas_groups() -> dict[str, frozenset[str]]:
    """桌面①：`piece_atlas.py::PIECE_OPTION_KEYS`（import 真身，不复制）。"""
    from xionghan_chess.desktop.ui.piece_atlas import PIECE_OPTION_KEYS

    return {kind.value: frozenset(keys) for kind, keys in PIECE_OPTION_KEYS.items() if keys}


def _eval_dict_node(node: ast.AST):
    """把 `piece_definitions` 的字面量求值成 Python 对象（只支持它用到的四类节点）。"""
    if isinstance(node, ast.Dict):
        return {_eval_dict_node(k): _eval_dict_node(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Tuple):
        return tuple(_eval_dict_node(elt) for elt in node.elts)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
            and node.value.id == "PieceType":
        return getattr(PieceType, node.attr)
    raise AssertionError(f"`piece_definitions` 里出现了守卫不认识的写法：{ast.dump(node)[:120]}"
                         "（若确实需要，请扩展 _eval_dict_node 而不是把副本抄进测试）")


def _find_named_literal(tree: ast.AST, name: str) -> ast.AST | None:
    """找 `name = {...}`（赋值）或 `f(name={...})`（关键字实参）的字面量节点。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == name:
            return node.value
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                return node.value
    return None


def desktop_dialog_groups() -> dict[str, frozenset[str]]:
    """桌面②：`dialogs.py` 里 `SettingsDialog(piece_definitions=...)` 的 rules 元组。

    它是构造函数内的局部字面量，import 不到，所以从源码 AST 里取**同一份数据**求值。
    """
    tree = ast.parse(DIALOGS_PY.read_text(encoding="utf-8"), filename=str(DIALOGS_PY))
    node = _find_named_literal(tree, "piece_definitions")
    assert node is not None, "`dialogs.py` 里找不到 `piece_definitions = {...}` 字面量"
    definitions = _eval_dict_node(node)
    assert isinstance(definitions, dict) and definitions, "`piece_definitions` 解析结果为空"
    groups: dict[str, frozenset[str]] = {}
    for kind, definition in definitions.items():
        assert isinstance(kind, PieceType), f"分组键应为 PieceType，实际是 {kind!r}"
        assert len(definition) == 3, f"{kind.value} 的条目应为 (标题, 说明, rules)，实际 {definition!r}"
        rules = definition[2]
        if rules:
            groups[kind.value] = frozenset(rules)
    return groups


def _js_object_body(source: str, name: str) -> str:
    """取 `const <name>={ ... }` 的花括号内部（按括号配平，不靠 `find(']')`）。"""
    match = re.search(rf"const\s+{re.escape(name)}\s*=\s*\{{", source)
    assert match, f"app.js 里找不到 `const {name}={{`"
    depth = 1
    index = match.end()
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"app.js 里 `{name}` 的花括号没有配平"
    return source[match.end(): index - 1]


def web_groups() -> dict[str, frozenset[str]]:
    """网页：`app.js::pieceRuleKeys`（只解析源码，不复制副本）。"""
    body = _js_object_body(APP_JS.read_text(encoding="utf-8"), "pieceRuleKeys")
    groups: dict[str, frozenset[str]] = {}
    for kind, inner in re.findall(r"([A-Za-z]+)\s*:\s*\[([^\]]*)\]", body):
        keys = frozenset(re.findall(r"'([A-Za-z0-9_]+)'", inner))
        if keys:
            groups[kind] = keys
    assert groups, "app.js 的 pieceRuleKeys 解析结果为空"
    return groups


# --- 断言 ----------------------------------------------------------------


def test_every_rule_option_is_grouped_or_explicitly_exempt() -> None:
    """核心守卫：新加的 `RuleOptions` 字段必须进分组，否则必须进带理由的豁免表。"""
    grouped: set[str] = set()
    for groups in (desktop_atlas_groups(), desktop_dialog_groups(), web_groups()):
        for keys in groups.values():
            grouped |= keys

    exempt = set(EXEMPT)
    unknown = _all_fields() - grouped - exempt
    assert not unknown, (
        "以下规则开关没有被任何一端的设置界面覆盖，也没有登记豁免理由：\n"
        f"  {sorted(unknown)}\n"
        "→ 若它是某枚棋子的规则，请加进三处分组"
        "（piece_atlas.PIECE_OPTION_KEYS / dialogs.piece_definitions / app.js pieceRuleKeys）；\n"
        "→ 若它是全局规则、登场开关或数值项，请在 tests/test_option_wiring.py 的 EXEMPT 里写明判据。"
    )


def test_exemptions_are_not_stale() -> None:
    """豁免表不能留死条目：`RuleOptions` 删了字段，豁免表必须同步删。"""
    stale = set(EXEMPT) - _all_fields()
    assert not stale, f"豁免表里有已不存在的字段：{sorted(stale)}"


def test_exemptions_do_not_overlap_groups() -> None:
    """同一个键不能既是"已覆盖"又是"豁免"——那说明豁免表在掩盖漏接。"""
    grouped: set[str] = set()
    for groups in (desktop_atlas_groups(), desktop_dialog_groups(), web_groups()):
        for keys in groups.values():
            grouped |= keys
    overlap = grouped & set(EXEMPT)
    assert not overlap, f"这些键已在分组里，豁免表应删除：{sorted(overlap)}"


def test_every_exemption_has_a_reason() -> None:
    """豁免必须给判据，否则豁免表会退化成"不想接就加一行"。"""
    empty = sorted(key for key, reason in EXEMPT.items() if len(reason.strip()) < 6)
    assert not empty, f"以下豁免条目缺少理由：{empty}"


def test_all_exemptions_are_accounted_for_by_known_categories() -> None:
    """豁免只允许两类：全局规则（3 个定稿键）+ 登场开关（按 PieceType 生成）。

    这条把豁免表从"任意白名单"收紧成"枚举已知类别"：想豁免第三种，
    必须先在这里说明为什么它天生不该进棋子分组。
    """
    global_rules = {"enforce_self_check", "threefold_draw", "no_progress_draw_plies"}
    appear_keys = {f"{kind.value}_appear" for kind in PieceType}
    assert set(EXEMPT) == global_rules | appear_keys, (
        "豁免表出现了未知类别：" f"{sorted(set(EXEMPT) - global_rules - appear_keys)}"
    )


def test_three_ends_have_identical_grouping() -> None:
    """三端分组必须完全一致（键集合 + 挂载分组），否则某端用户少/多了开关。"""
    atlas = desktop_atlas_groups()
    dialog = desktop_dialog_groups()
    web = web_groups()
    assert atlas == dialog, f"桌面两处分组不一致：仅 atlas {atlas.keys() - dialog.keys()} / " \
                            f"仅 dialog {dialog.keys() - atlas.keys()}"
    assert atlas == web, f"桌面与网页分组不一致：仅桌面 {set(atlas) - set(web)} / 仅网页 {set(web) - set(atlas)}"


def test_grouping_matches_the_frozen_fingerprint() -> None:
    """三端一致还不够：三端一起漏掉某组也能过一致性检查，所以留一份定稿指纹。"""
    atlas = {kind: keys for kind, keys in desktop_atlas_groups().items()}
    assert atlas == EXPECTED_GROUP_KEYS, (
        "三端棋子分组与定稿指纹不符（若是有意的产品变更，请同步更新 EXPECTED_GROUP_KEYS"
        "并说明用户侧的变化）"
    )
    total = sum(len(keys) for keys in atlas.values())
    assert len(atlas) == 6 and total == 18, f"定稿形状应为 6 组 / 18 键，实际 {len(atlas)} 组 / {total} 键"


def test_grouped_keys_are_real_rule_fields() -> None:
    """分组里的键必须是 `RuleOptions` 真字段，防拼错后静默变成死复选框。"""
    known = _all_fields()
    grouped: set[str] = set()
    for groups in (desktop_atlas_groups(), desktop_dialog_groups(), web_groups()):
        for keys in groups.values():
            grouped |= keys
    bogus = sorted(grouped - known)
    assert not bogus, f"分组里出现了不存在的规则键（疑似拼错）：{bogus}"


# --- 文案覆盖 ------------------------------------------------------------

def _rule_section(language: str) -> dict[str, str]:
    data = json.loads((LOCALES / f"{language}.json").read_text(encoding="utf-8"))
    section = data.get("rule")
    assert isinstance(section, dict), f"{language}.json 缺少 rule 段"
    return section


def test_both_locales_cover_every_grouped_key_in_long_and_short_form() -> None:
    """每个进界面的开关都必须有长/短两版文案 —— 缺了用户会直接看到 `rule.xxx` 原文。"""
    grouped: set[str] = set()
    for groups in (desktop_atlas_groups(), desktop_dialog_groups(), web_groups()):
        for keys in groups.values():
            grouped |= keys

    problems: list[str] = []
    for language in ("zh-CN", "en"):
        section = _rule_section(language)
        for key in sorted(grouped):
            for suffix in ("", "_short"):
                if key + suffix not in section:
                    problems.append(f"{language}: rule.{key}{suffix}")
    assert not problems, "以下文案缺失（界面会显示原始 key）：\n  " + "\n  ".join(problems)


# --- 按钮显隐的规则判据（UI_ACTION_REQUIRES） -------------------------------
#
# 与上面的「开关 → 三端分组」是同一类问题：动作的**可达性**也是规则的一部分。
# `pawn_resurrection` 关掉时，「复活兵卒」这个动作在三端都不存在，
# 但三端过去都只把它 `disabled`、从不隐藏 —— 玩家面对一个永远点不动的按钮。
# 这里守两件事：core 这张表本身对，且三端真的读了它（而不是各写一份硬编码）。

def test_action_requirements_mirror_the_engine_guard() -> None:
    from xionghan_chess.core.profiles import UI_ACTION_REQUIRES, action_visible

    assert UI_ACTION_REQUIRES["resurrect"] == ("pawn_resurrection",)
    assert action_visible(RuleOptions(pawn_resurrection=True), "resurrect") is True
    assert action_visible(RuleOptions(pawn_resurrection=False), "resurrect") is False
    # 没登记的动作恒可见（常驻按钮不能被这张表误伤）
    assert action_visible(RuleOptions(pawn_resurrection=False), "resign") is True


def test_three_fronts_read_the_shared_action_table() -> None:
    """桌面直接 import core；网页读 `/api/profiles` 的 `actionRequirements`。

    断言的是"消费方式"而不是"某一行代码"：谁再把 `pawn_resurrection` 硬编码进
    前端判断，这条就会因为不再出现共享表的名字而变红。
    """
    desktop = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")
    assert "action_visible(" in desktop and "UI_ACTION_REQUIRES" in (
        ROOT / "src" / "xionghan_chess" / "core" / "profiles.py").read_text(encoding="utf-8")
    assert "setVisible(visible)" in desktop, "桌面侧没有把复活按钮/菜单项真的隐藏"

    web = APP_JS.read_text(encoding="utf-8")
    assert "actionRequirements" in web, "网页没有消费 /api/profiles 下发的动作依赖表"
    assert "$('#resurrectButton').hidden=" in web, "网页仍然只 disabled、不隐藏"

    service = (ROOT / "src" / "xionghan_chess" / "service" / "app.py").read_text(encoding="utf-8")
    assert '"actionRequirements": action_requirements()' in service, "接口没有下发动作依赖表"
