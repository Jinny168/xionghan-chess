"""星轨几何层的**训练态防回退守卫**（裁决 1 / 批次 A）。

## 两条线，别混

* **星轨几何层**（射 → 四斜向星位锚点的放射线 + 空心环）：
  **训练态一律屏蔽** —— 章节闯关、每日一题、连对挑战全都屏蔽。
  判据是"有没有在答题"，**不看 scored**。
* **文字提示层**（指子 / 指招的文字提示）：
  章节闯关（scored=false）可用**且计入星级**；每日一题 / 连对挑战（scored=true）
  屏蔽一切提示。

所以训练态**只放开文字提示层**，星轨层永远不放。
有人看到"章节闯关里也有星点"就顺手把星轨按 scored 放行，
或者看到"训练态要放行"就顺手把星轨也一起放出来 —— 正是本守卫要抓住的回退。

## 本文件守什么

1. **静态字面量**：三端星轨守卫的**形态**保持不变（web 认 `app.puzzleSession`；
   webapp 认 `!app.puzzle`；桌面认 `puzzle_session is None`），
   且**都不许出现 scored** —— 星轨层一旦开始按 scored 分流，就是回退的开始。
2. **行为**：用 Node 探针把 webapp 产物里的 `showStarHints` 判定**原样求值**，
   断言章节闯关（scored=false）时星轨仍然不显形、常规对局时显形（防空门禁）。
3. **对照**：文字提示层三端**都**有 scored 守卫 —— 与星轨层形成对照，
   免得有人把两条线搞反（把 scored 守卫加到星轨层，或从文字层删掉）。

桌面端的判据同样要看**赋值时序**：星轨开关在 `configure_board()` 里按
`puzzle_session` 是否为空求值，而两个训练入口都必须在 `configure_board()`
**之前**置位 `puzzle_session` —— 否则守卫写着"训练态屏蔽"、实际却带提示进考场。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from _node_guard import NODE, module_skip_mark, require_node

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "star_hints_guard_probe.mjs"

WEB_APP = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
WEBAPP_APP = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
DESKTOP_APP = (ROOT / "src" / "xionghan_chess" / "desktop" / "app.py").read_text(encoding="utf-8")

if (mark := module_skip_mark()) is not None:
    pytestmark = mark


# ── 抠取helper ────────────────────────────────────────────────────────────────
def _balanced(source: str, header: str, opener: str = "(") -> str:
    """从 `header` 起抠出括号配平的片段（含 header 与收尾的右括号）。

    用括号配平而不是正则：源码里有嵌套调用（`Boolean(...)`、`set_assists(...)`），
    正则要么截断要么漏配平；配平扫描对"改一行就变形态"这种守卫最耐用。
    """
    start = source.index(header)
    open_idx = source.index(opener, start + len(header) - 1)
    depth = 0
    for i in range(open_idx, len(source)):
        if source[i] == opener:
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError(f"{header!r} 的括号没配平，源码结构变了")


def _function_body(source: str, signature: str) -> str:
    """抠出 `function xxx(...){ ... }` 的函数体（到列 0 的 `}` 为止）。"""
    start = source.index(signature)
    end = source.index("\n}", start)
    return source[start:end]


def _web_star_guard() -> str:
    return _function_body(WEB_APP, "function drawStarHints(g){")


def _webapp_star_guard() -> str:
    return _balanced(WEBAPP_APP, "const showStarHints = Boolean(")


def _desktop_star_guard() -> str:
    return _balanced(DESKTOP_APP, "self.board.set_assists(")


# ── 1. 星轨几何层：形态守卫（三端）──────────────────────────────────────────
def test_web_star_hints_guard_blocks_every_training_state() -> None:
    """web 旧树：星轨守卫认 `app.puzzleSession`（训练态在场就屏蔽），不看 scored。"""
    guard = _web_star_guard()
    assert "app.puzzleSession" in guard, "web 星轨守卫丢了 app.puzzleSession，训练态不再屏蔽"
    assert "scored" not in guard, (
        "web 星轨守卫出现了 scored：星轨几何层必须按'是否在答题'屏蔽，"
        "不能按 scored 分流（否则章节闯关会显形）"
    )


def test_webapp_star_hints_guard_blocks_every_training_state() -> None:
    """webapp：星轨守卫认 `!app.puzzle`（任何题态都屏蔽），不看 scored。"""
    guard = _webapp_star_guard()
    assert "!app.puzzle" in guard, "webapp 星轨守卫丢了 !app.puzzle，训练态不再屏蔽"
    assert "scored" not in guard, (
        "webapp 星轨守卫出现了 scored：星轨几何层必须按'是否在答题'屏蔽，"
        "不能按 scored 分流（否则章节闯关会显形）"
    )


def test_desktop_star_hints_guard_blocks_every_training_state() -> None:
    """桌面：星轨开关按 `puzzle_session is None` 求值，不按 scored 放行。"""
    block = _desktop_star_guard()
    assert "archer_star_hints" in block, "桌面 set_assists 里没有 archer_star_hints 传参"
    assert "puzzle_session" in block, (
        "桌面星轨守卫丢了 puzzle_session 判据：训练态在盘时不得带星轨进考场"
    )
    assert "is None" in block, "桌面星轨守卫应写成 `puzzle_session is None`（无会话才放行）"
    assert "scored" not in block, (
        "桌面星轨守卫出现了 scored：一旦按 scored 放行，章节闯关（scored=false）"
        "就会带着星轨进考场"
    )


def test_desktop_puzzle_session_is_set_before_configure_board() -> None:
    """桌面守卫的**时序**：训练入口必须先置 `puzzle_session` 再 `configure_board()`。

    顺序反了的话，`configure_board()` 读到的还是 None，星轨会带着进考场 ——
    这是守卫写法对了、实际却没生效的典型坑。
    """
    # 入口一：训练对话框（章节闯关 / 每日一题）
    show_training = DESKTOP_APP[DESKTOP_APP.index("def show_training") : DESKTOP_APP.index("def show_training") + 4000]
    assert "self.puzzle_session = puzzle_judge.session_for(" in show_training, "训练入口未置 puzzle_session"
    assert show_training.index("self.puzzle_session = puzzle_judge.session_for(") < show_training.index(
        "self.configure_board()"
    ), "puzzle_session 必须在 configure_board() 之前置位，否则星轨会带着进考场"

    # 入口二：连对挑战 / 每日一题共用的载入函数
    load_block = DESKTOP_APP[
        DESKTOP_APP.index("def _load_puzzle_into_board") : DESKTOP_APP.index("def _load_puzzle_into_board") + 2000
    ]
    assert "self.puzzle_session = puzzle_judge.session_for(" in load_block, "载入函数未置 puzzle_session"
    assert load_block.index("self.puzzle_session = puzzle_judge.session_for(") < load_block.index(
        "self.configure_board()"
    ), "puzzle_session 必须在 configure_board() 之前置位，否则星轨会带着进考场"


def test_web_chapter_mode_has_puzzle_session_but_not_scored() -> None:
    """web 章节闯关：`puzzleSession` 在场（星轨屏蔽）且 `scored:false`（文字提示放行）。

    这条断言是"两条线"的**行为证据**：同一个题态里，
    星轨看 `puzzleSession`（在场 → 屏蔽）、文字提示看 `scored`（false → 放行）。
    """
    start = WEB_APP.index("app.puzzleSession={")
    statement = WEB_APP[start : WEB_APP.index("}", start) + 1]
    assert "scored:false" in statement, "章节闯关应是 scored:false（文字提示可用且计星）"
    assert "streak:false" in statement, "章节闯关不是连对挑战"


# ── 2. 行为守卫：webapp 产物原样求值（章节闯关时星轨必须不显形）─────────────
def test_webapp_star_hints_hidden_in_chapter_mode() -> None:
    """求值 webapp 产物里的星轨判定：章节闯关（scored=false）时星轨**不得**显形。

    这是本守卫的**行为核心**：静态字面量守卫只证明"没被改坏"，
    这条才证明"章节闯关时星轨真的不显形"——也就是裁决里点名的那个回退。
    """
    require_node()
    result = subprocess.run(
        [NODE or "node", str(PROBE), str(ROOT / "webapp" / "js" / "ui" / "app.js")],
        capture_output=True,
        text=True,
        check=True,
    )
    observed = json.loads(result.stdout)
    assert observed["normal"] is True, (
        "常规对局时星轨本该显形；探针返回 false 说明求值片段抠错了（防空门禁）"
    )
    for mode in ("chapter", "daily", "streak"):
        assert observed[mode] is False, (
            f"{mode} 态星轨显形了 —— 星轨几何层在训练态必须一律屏蔽"
            "（训练态只放开**文字提示层**，不放星轨层）"
        )


# ── 3. 对照：文字提示层三端都有 scored 守卫（与星轨层形成对照）──────────────
def test_text_hint_layer_uses_scored_guard_in_all_three_ends() -> None:
    """文字提示层三端都按 scored 分流：章节闯关可用、计分态屏蔽。

    与上面的星轨守卫构成对照 —— 两条线各走各的判据，谁都别串。
    """
    assert "if(session&&session.scored)return;" in WEB_APP, "web 文字提示缺 scored 守卫"
    assert "if (app.puzzle.scored) return;" in WEBAPP_APP, "webapp 文字提示缺 scored 守卫"
    assert "if self.puzzle_scored:" in DESKTOP_APP, "桌面文字提示缺 scored 守卫"


def test_star_and_text_hint_guards_use_different_keys() -> None:
    """星轨层与文字提示层的判据**必须不同**，避免有人把两条线合并成一条。

    合并的两种典型形态，各打各的：
      · 把 scored 守卫加到星轨层 → 章节闯关时星轨显形；
      · 从文字提示层删掉 scored → 计分态给提示，替玩家答题。
    """
    # 星轨层：判据是"有没有在答题"，层内**不含** scored。
    for guard in (_web_star_guard(), _webapp_star_guard(), _desktop_star_guard()):
        assert "scored" not in guard, "星轨层出现了 scored，两条线被合并成一条了"

    # 文字提示层：判据是 scored，三端都在。
    assert "session.scored" in WEB_APP, "web 文字提示应按 session.scored 分流"
    assert "app.puzzle.scored" in WEBAPP_APP, "webapp 文字提示应按 app.puzzle.scored 分流"
    assert "self.puzzle_scored" in DESKTOP_APP, "桌面文字提示应按 self.puzzle_scored 分流"
