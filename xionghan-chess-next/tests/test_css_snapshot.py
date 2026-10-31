"""令牌化 A 阶段的验收器：`app.css` 的声明快照必须与基线逐行相同。

令牌化的唯一目的是"把字面值换成 var()，**视觉一点不变**"。
所以验收不是"能跑"，而是：展开 `var()` 之后的 `选择器|属性|值` 序列 **与改前完全一致**。

基线文件：`benchmarks/css_snapshot_baseline.txt`（由 `scripts/css_snapshot.py --write` 生成）。
A-1/A-2 每改一批，跑这条；红就说明"颜色真的变了"，不是"格式变了"。
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "benchmarks" / "css_snapshot_baseline.txt"


def test_css_snapshot_matches_baseline() -> None:
    assert BASELINE.is_file(), "缺少基线文件，先跑 python scripts/css_snapshot.py --write"
    current = subprocess.run([sys.executable, str(ROOT / "scripts" / "css_snapshot.py")],
                             check=True, capture_output=True, text=True).stdout
    baseline = BASELINE.read_text(encoding="utf-8")
    if current != baseline:
        diff = [
            f"  基线 {a!r}\n  现在 {b!r}"
            for a, b in zip(baseline.splitlines(), current.splitlines()) if a != b
        ][:5]
        raise AssertionError(
            "CSS 声明快照变了（说明视觉可能变了）：\n" + "\n".join(diff) +
            f"\n行数 基线 {len(baseline.splitlines())} / 现在 {len(current.splitlines())}")


def test_snapshot_is_stable_across_runs() -> None:
    """同一输入两次运行必须逐字节一致 —— 否则这条验收器天天假红。"""
    def run() -> str:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "css_snapshot.py")],
                              check=True, capture_output=True, text=True).stdout

    first, second = run(), run()
    assert first == second, "快照不稳定"
    print("基线 sha256:", hashlib.sha256(first.encode()).hexdigest()[:16])
