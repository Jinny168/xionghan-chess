"""将军态静态双线环契约（VA-18，第二批第 3 项）。

守什么
------
1. web 旧树与 webapp 的被将方王格外画的是**静态双线环**：外环 1.1 r + 内细环 1.22 r，
   间隙留白；两环共用既有红令牌，零新增色值。
2. 系统「减少动态」下脉冲消失、**静态双环仍在**；脉冲只是双环的次要动效，
   不是与双线环并列的第二套环（用 arc 次数钉住）。
3. 三端渲染源码都保留层级顺序的可核对记录：上一步 < 可吃 < 选择 < 将军；
   桌面三重线索（外框脉冲 + 王格环 + 「将军」描边字）本轮不改。

为什么读源码而不是截图
----------------------
像素基线在本项目明确不做（字体/DPR/抗锯齿非确定，见 VISUAL_ALIGNMENT_TRIAD §3）。
这里只钉「自动门禁可达」的规格：环参数、绘制结构、层级文本。
「玩家是否更快发现被将」属人工判断，本轮不做 —— 本文件不声称它。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "board_widget.py"
WEB = ROOT / "web" / "js" / "app.js"
WEBAPP = ROOT / "webapp" / "js" / "ui" / "board.js"

LAYER_ORDER = "上一步 < 可吃 < 选择 < 将军"
BLOCK_BEGIN = "// CHECK_RING_BEGIN"
BLOCK_END = "// CHECK_RING_END"


def _src(path: Path) -> str:
    assert path.exists(), f"渲染器不存在：{path}"
    return path.read_text(encoding="utf-8")


def _ring_block(path: Path) -> str:
    """只取将军环绘制块，避免同文件其它 `ctx.arc` 干扰计数。"""
    match = re.search(re.escape(BLOCK_BEGIN) + r"(.*?)" + re.escape(BLOCK_END), _src(path), re.S)
    assert match, f"{path.name} 缺少 {BLOCK_BEGIN}/{BLOCK_END} 包围的将军环绘制块"
    return match.group(1)


def test_both_web_trees_declare_ring_radii() -> None:
    """两棵 web 树都以常量声明外环 1.1 / 内细环 1.22，和清单 VA-18 同源。"""
    for path in (WEB, WEBAPP):
        source = _src(path)
        assert re.search(r"CHECK_RING_OUTER\s*=\s*1\.1", source), f"{path.name} 外环不是 1.1 r"
        assert re.search(r"CHECK_RING_INNER\s*=\s*1\.22", source), f"{path.name} 内细环不是 1.22 r"


def test_web_static_double_ring_is_always_drawn() -> None:
    """web 旧树无脉冲：将军态恒画两道静态同心环，沿用既有红令牌、零新增色值。"""
    block = _ring_block(WEB)
    assert block.count("ctx.arc") == 2, (
        f"web 将军环应恰好两道同心环，实际 {block.count('ctx.arc')} 道"
        "（多出来的是与双线环并列的第二套环，少的是没画齐双线）"
    )
    assert "CHECK_RING_OUTER" in block and "CHECK_RING_INNER" in block, "两道环必须分别引用外环与内细环常量"
    assert "performance.now()" not in block, "web 旧树将军环应保持静态，不得引入计时脉冲"
    assert "rgba(196,35,35,.35)" in block, "未沿用 web 旧树既有将军红令牌"
    assert "#" not in block, "将军环不得出现新色值"


def test_webapp_static_double_ring_survives_reduced_motion() -> None:
    """webapp：reducedMotion 下静态双环仍在；脉冲只是双环的同步次要动效。"""
    block = _ring_block(WEBAPP)
    branches = re.search(
        r"if \(view\.reducedMotion\) \{(.*?)\} else \{(.*?)\}\s*ctx\.restore\(\);", block, re.S
    )
    assert branches, "webapp 将军绘制块应保留显式 reducedMotion / 脉冲两个分支"
    static, pulse = branches.group(1), branches.group(2)
    for label, branch in (("reducedMotion", static), ("脉冲", pulse)):
        assert branch.count("ctx.arc") == 2, (
            f"{label}分支应画两道同心环，实际 {branch.count('ctx.arc')} 道"
        )
        assert "CHECK_RING_OUTER" in branch and "CHECK_RING_INNER" in branch, f"{label}分支未画齐双线环"
    assert "performance.now()" not in static, "reducedMotion 分支不得读取脉冲计时"
    assert "performance.now()" in pulse, "非 reducedMotion 分支应保留脉冲次要动效"
    assert block.count("ctx.arc") == 4, (
        f"整个将军块应恰好 4 次 arc（两分支各两道环），实际 {block.count('ctx.arc')} 次 —— "
        "出现第三道环即是与双线环并列的第二套"
    )
    assert "rgba(200,40,30" in block, "未沿用 webapp 既有将军红令牌"
    assert "#" not in block, "将军环不得出现新色值"


def test_layer_order_is_recorded_in_all_three_renderers() -> None:
    """三端源码都要留下层级顺序的可核对文本（不是人工目检）。"""
    for path in (WEB, WEBAPP):
        assert LAYER_ORDER in _src(path), f"{path.name} 未记录层级契约「{LAYER_ORDER}」"
    desktop = _src(DESKTOP)
    # 桌面本轮不改，沿用其既有措辞；「将军优先级最高」与 order 文本共同锁定层级。
    assert "上一步 < 吃子提示 < 选择态" in desktop, "桌面既有层级文本被改动"
    assert "将军优先级最高" in desktop, "桌面「将军最高」的层级说明被改动"


def test_desktop_triple_cues_untouched() -> None:
    """桌面三重线索保持不变：外框脉冲 + 王格环 + 「将军」描边字。"""
    source = _src(DESKTOP)
    assert "_draw_check_pulse_overlay" in source, "桌面外框脉冲线索丢失"
    assert "painter.drawEllipse(center, cw * 0.42, ch * 0.42)" in source, "桌面王格环半径被改动"
    assert "_draw_check_label" in source, "桌面「将军」描边字线索丢失"
