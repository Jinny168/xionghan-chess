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

## 「棋子分组」的取法

唯一源是 `core/profiles.py::PIECE_OPTION_GROUPS`（`piece_option_groups()` 是它的
JSON 友好视图）。三端不再各自携带分组字面量：
1. 桌面两处直接 import core 的 `PIECE_OPTION_GROUPS`；
2. 网页读 `/api/profiles` 下发的 `pieceOptionGroups`（老服务端降级为扁平规则区，
   **不复制硬编码 fallback**）；
3. 服务端下发该字段。

因此本文件只从 core 读分组（`core_groups()`），另用源码门禁守"三端不再出现分组字面量"。
反向验证也依赖这一点：往任一端抄回一份硬编码，源码门禁立刻红。

## 「分组形状」的含义

共享分组必须是**键集合相同、挂载的棋子分组也相同**（6 组 / 18 键：
king 4 · horse 3 · elephant 2 · advisor 2 · pawn 6 · archer 1）。
只比键集合不够——把「马的别腿」挂到「兵」下面，键集合照样是全的，但界面是错的。
一致性不再靠"三端各读一份再比对"，而靠"只有一份 + 源码门禁禁止抄回第二份"。

## 加规则开关的代价（故意的）

`EXPECTED_GROUP_KEYS` 是**定稿指纹**：以后新增一个 `RuleOptions` 字段，
除了改 core 分组，还必须同时更新这份指纹。这是刻意设计——
它拦的是"三端一起漏"这种连一致性检查都过不了的情形（三端同时删掉某组，
一致性照样通过，但用户丢了功能）。
指纹里写着 18 个键与它们的归属，改它就是一次显式的产品变更声明，不该顺手改。
"""

from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path

from xionghan_chess.core.model import PieceType
from xionghan_chess.core.profiles import RuleOptions

ROOT = Path(__file__).resolve().parents[1]
ATLAS_PY = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "piece_atlas.py"
DIALOGS_PY = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "dialogs.py"
CORE_PY = ROOT / "src" / "xionghan_chess" / "core" / "profiles.py"
SERVICE_PY = ROOT / "src" / "xionghan_chess" / "service" / "app.py"
APP_JS = ROOT / "web" / "js" / "app.js"
WEBAPP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"
OFFLINE_JS = ROOT / "android" / "Resources" / "assets" / "offline" / "offline.js"
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
    "king": frozenset(
        {"king_can_leave_palace", "king_diagonal_in_palace", "king_lose_diagonal_outside_palace", "invasion_victory"}
    ),
    "horse": frozenset({"horse_blocked_by_leg", "horse_straight_three", "horse_straight_three_move_only"}),
    "elephant": frozenset({"elephant_can_cross_river", "elephant_gain_jump_two_enemy_territory"}),
    "advisor": frozenset({"advisor_can_leave_palace", "advisor_gain_straight_outside_palace"}),
    "pawn": frozenset(
        {
            "pawn_fast_move_before_enemy_territory",
            "pawn_charge",
            "pawn_three_line_capture",
            "pawn_backward_at_base",
            "pawn_resurrection",
            "pawn_promotion",
        }
    ),
    "archer": frozenset({"archer_enhanced_mode"}),
}


def _all_fields() -> set[str]:
    return {field.name for field in fields(RuleOptions)}


# --- 分组读取（core 是唯一源）---------------------------------------------


def core_groups() -> dict[str, frozenset[str]]:
    """棋子分组的唯一源：`core/profiles.py::piece_option_groups()`。

    Step 1 守卫先行时 core 里还没有这个函数 ⇒ 调用即 ImportError，所有依赖分组的
    断言全红。这正是「守卫有效」的证明：产品代码未动，守卫就已经不答应了。
    """
    from xionghan_chess.core.profiles import piece_option_groups

    return {kind: frozenset(keys) for kind, keys in piece_option_groups().items() if keys}


def grouped_keys() -> set[str]:
    """所有非空分组里的键全集（仍按棋子逐组比的地方用 `core_groups()`）。"""
    return {key for keys in core_groups().values() for key in keys}


# --- 断言 ----------------------------------------------------------------


def test_every_rule_option_is_grouped_or_explicitly_exempt() -> None:
    """核心守卫：新加的 `RuleOptions` 字段必须进分组，否则必须进带理由的豁免表。"""
    grouped = grouped_keys()

    exempt = set(EXEMPT)
    unknown = _all_fields() - grouped - exempt
    assert not unknown, (
        "以下规则开关没有被任何一端的设置界面覆盖，也没有登记豁免理由：\n"
        f"  {sorted(unknown)}\n"
        "→ 若它是某枚棋子的规则，请加进 core/profiles.py 的 PIECE_OPTION_GROUPS；\n"
        "→ 若它是全局规则、登场开关或数值项，请在 tests/test_option_wiring.py 的 EXEMPT 里写明判据。"
    )


def test_exemptions_are_not_stale() -> None:
    """豁免表不能留死条目：`RuleOptions` 删了字段，豁免表必须同步删。"""
    stale = set(EXEMPT) - _all_fields()
    assert not stale, f"豁免表里有已不存在的字段：{sorted(stale)}"


def test_exemptions_do_not_overlap_groups() -> None:
    """同一个键不能既是"已覆盖"又是"豁免"——那说明豁免表在掩盖漏接。"""
    grouped = grouped_keys()
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
        f"豁免表出现了未知类别：{sorted(set(EXEMPT) - global_rules - appear_keys)}"
    )


def test_three_ends_read_shared_grouping_without_local_literals() -> None:
    """三端不再各持一份分组字面量，而是引用 core 的共享表。

    断言"消费方式"而非"某行代码长什么样"：谁把分组抄回任一端，这条立刻红。
    - 桌面图谱 / 桌面设置：import `PIECE_OPTION_GROUPS`；
    - Web：读 `/api/profiles` 下发的 `pieceOptionGroups`；
    - 服务端：下发该字段。
    """
    atlas = ATLAS_PY.read_text(encoding="utf-8")
    assert "PIECE_OPTION_KEYS" not in atlas, "桌面图谱仍带着 PIECE_OPTION_KEYS 硬编码分组"
    assert "PIECE_OPTION_GROUPS" in atlas, "桌面图谱没有引用 core 的共享分组表"

    dialog = DIALOGS_PY.read_text(encoding="utf-8")
    assert "piece_definitions = {" not in dialog, "桌面设置仍带着 piece_definitions 分组字面量"
    assert "PIECE_OPTION_GROUPS" in dialog, "桌面设置没有引用 core 的共享分组表"

    web = APP_JS.read_text(encoding="utf-8")
    assert "const pieceRuleKeys" not in web, "Web 不得再出现 `const pieceRuleKeys` 硬编码分组"
    assert "pieceOptionGroups" in web, "Web 没有消费 /api/profiles 下发的分组表"

    service = SERVICE_PY.read_text(encoding="utf-8")
    assert '"pieceOptionGroups": piece_option_groups()' in service, "接口没有下发棋子分组表"

    core = CORE_PY.read_text(encoding="utf-8")
    assert "PIECE_OPTION_GROUPS" in core and "def piece_option_groups(" in core, "core 没有定义共享分组表"


def test_offline_ends_have_no_grouping_names() -> None:
    """离线端（Android offline.js / webapp UI）只做扁平规则区，不得出现分组名。

    防止有人"顺手补一份"让离线端成为第四份真相 —— 那正是 C-1 要消灭的东西。
    """
    for path in (OFFLINE_JS, WEBAPP_JS):
        source = path.read_text(encoding="utf-8")
        for name in ("pieceOptionGroups", "PIECE_OPTION_GROUPS", "pieceRuleKeys", "PIECE_OPTION_KEYS"):
            assert name not in source, f"离线端 {path.relative_to(ROOT)} 不应出现分组名 {name}"


def test_grouping_matches_the_frozen_fingerprint() -> None:
    """三端一致还不够：三端一起漏掉某组也能过一致性检查，所以留一份定稿指纹。"""
    shared = core_groups()
    assert shared == EXPECTED_GROUP_KEYS, (
        "core 共享分组与定稿指纹不符（若是有意的产品变更，请同步更新 EXPECTED_GROUP_KEYS并说明用户侧的变化）"
    )
    total = sum(len(keys) for keys in shared.values())
    assert len(shared) == 6 and total == 18, f"定稿形状应为 6 组 / 18 键，实际 {len(shared)} 组 / {total} 键"


def test_grouped_keys_are_real_rule_fields() -> None:
    """分组里的键必须是 `RuleOptions` 真字段，防拼错后静默变成死复选框。"""
    known = _all_fields()
    grouped = grouped_keys()
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
    grouped = grouped_keys()

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
        ROOT / "src" / "xionghan_chess" / "core" / "profiles.py"
    ).read_text(encoding="utf-8")
    assert "setVisible(visible)" in desktop, "桌面侧没有把复活按钮/菜单项真的隐藏"

    web = APP_JS.read_text(encoding="utf-8")
    assert "actionRequirements" in web, "网页没有消费 /api/profiles 下发的动作依赖表"
    assert "$('#resurrectButton').hidden=" in web, "网页仍然只 disabled、不隐藏"

    service = (ROOT / "src" / "xionghan_chess" / "service" / "app.py").read_text(encoding="utf-8")
    assert '"actionRequirements": action_requirements()' in service, "接口没有下发动作依赖表"


# --- 文档里的字段数（防「33 字段」这类数字再漂）------------------------------
#
# 只守**一种**表述：同一行里 `RuleOptions` 之后紧跟的「N 字段 / N 个字段」。
# 刻意不泛化成「文档里所有数字」——人日、行号、「8 项投稿字段」这类数字
# 各有各的语境，全判红只会让门禁变成噪声，红了没人信、也没人修。
#
# 扫描范围：docs/**/*.md + README.md。本文件不扫（否则就是自己守自己）。

_FIELD_COUNT_RE = re.compile(r"RuleOptions[^\n]{0,40}?(\d+)\s*个?\s*字段")

# 显式豁免：历史实测记录。数字是**当时的证据**，改成现值等于篡改历史，
# 所以保留原数字，由正文的更正注记指明现值。
# 按 (路径, 数字) 登记：那句要是被改成别的数字，门禁照样红 ——
# 不靠"正则恰好没匹配到"来静默放行；反过来，条目再也命中不到也会红（见下面的 stale 断言）。
_FIELD_COUNT_EXEMPT: dict[tuple[str, int], str] = {
    ("docs/IMPROVEMENT_PLAN.md", 33): (
        "C-2 立项时的手测证据，原文已注明「后续删至 32」；改数字等于篡改历史证据"
    ),
}


def test_doc_rule_options_field_counts_match_code() -> None:
    """文档里描述 `RuleOptions` 字段数的地方必须等于真实字段数。"""
    actual = len(fields(RuleOptions))
    paths = sorted((ROOT / "docs").rglob("*.md")) + [ROOT / "README.md"]

    problems: list[str] = []
    seen = 0
    hit_exempt: set[tuple[str, int]] = set()
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in _FIELD_COUNT_RE.finditer(line):
                number = int(match.group(1))
                seen += 1
                if (rel, number) in _FIELD_COUNT_EXEMPT:
                    hit_exempt.add((rel, number))
                    continue
                if number != actual:
                    problems.append(f"{rel}:{lineno} 写着 {number} 字段（实际 {actual}）：{match.group(0)}")

    assert not problems, (
        "文档里的 RuleOptions 字段数与代码不一致：\n  "
        + "\n  ".join(problems)
        + f"\n→ 描述当前实现的，改成 {actual}；历史实测记录的，在正文加更正注记后"
        "登记进 _FIELD_COUNT_EXEMPT（必须写理由）。"
    )
    # 门禁自检：正则一条都匹配不到 = 表述全变了、门禁已失效，必须红。
    assert seen, "没有匹配到任何「RuleOptions…N 字段」表述，门禁已失效，请检查正则"
    # 豁免表不能留死条目：那句被删/被改写后，豁免必须跟着删，否则是静默漏网的温床。
    stale = set(_FIELD_COUNT_EXEMPT) - hit_exempt
    assert not stale, f"以下豁免条目已不再命中，应删除：{sorted(stale)}"
