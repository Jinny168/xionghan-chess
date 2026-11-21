"""连对结束页文案的**行为**测试（批次 A / D2）。

旧守卫只查 locale 键存在（test_batch_a_naming_and_privacy.py），抓不到逻辑错：
桌面曾在破纪录时仍补一句"还差 1 题破纪录"、count=0 时漏掉"下一次从第一题
重新开始"。这里把三端（桌面 / webapp / web）的结束页口径一起钉住：

- 桌面直接测纯函数 `desktop.training.streak_end_lines`；
- webapp / web 由 `streak_banner_probe.mjs` 抽取**真实** showStreakBanner
  函数体执行（桩掉 t()/$()，不复制逻辑），归一成同样的 [键名后缀, count]；
- 两端逐项与桌面比对，任一端漂移立即红。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from _node_guard import NODE, module_skip_mark, require_node

from xionghan_chess.desktop import training

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "streak_banner_probe.mjs"

if (mark := module_skip_mark()) is not None:
    pytestmark = mark

CASES = [(3, 2), (1, 2), (0, 0), (0, 2), (3, 0)]


def test_desktop_record_has_no_gap() -> None:
    """破纪录只出 streakRecord，绝不再出 streakGap（D2 的矛盾句）。"""
    lines = training.streak_end_lines(3, 2)
    assert lines == [
        ("streakRound", 3),
        ("streakRecord", 1),
        ("streakKept", None),
        ("streakPractice", None),
    ]
    assert all(key != "streakGap" for key, _ in lines)


def test_desktop_no_record_uses_max_gap() -> None:
    """未破纪录：gap = max(1, prev_best - count + 1)。"""
    assert ("streakGap", 2) in training.streak_end_lines(1, 2)
    # prev_best=count 时 max(1, 1) 仍是 1，不会出现 "还差 0 题"
    assert ("streakGap", 1) in training.streak_end_lines(2, 2)


def test_desktop_zero_count_still_shows_no_record() -> None:
    """count=0 也必须出 streakNoRecord（与 web / webapp 一致）。"""
    lines = training.streak_end_lines(0, 2)
    assert ("streakNoRecord", None) in lines
    assert ("streakGap", 3) in lines
    assert ("streakNoRecord", None) in training.streak_end_lines(0, 0)


def test_web_and_webapp_banner_match_desktop() -> None:
    """真跑 webapp / web 的 showStreakBanner，逐项对拍桌面口径。"""
    require_node()
    proc = subprocess.run(
        [NODE, str(PROBE), str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    js = json.loads(proc.stdout)
    expected = [
        [[key, count] for key, count in training.streak_end_lines(count, prev)]
        for count, prev in CASES
    ]
    assert js["webapp"] == expected, "webapp 结束页文案与桌面口径漂移"
    assert js["web"] == expected, "web 旧树结束页文案与桌面口径漂移"
