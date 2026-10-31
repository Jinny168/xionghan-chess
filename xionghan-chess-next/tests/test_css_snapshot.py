"""令牌化 A 阶段的验收器：`app.css` 的声明快照必须与基线**逐字节**相同。

令牌化的唯一目的是"把字面值换成 var()，**视觉一点不变**"。所以验收不是"能跑"，
而是：展开 `var()` 之后的 `选择器|属性|值` 序列与改前完全一致。

两份基线（亮 / 暗各一，暗色键带 `@dark` 后缀）：单表会让同名变量互相覆盖，
"只在 :root 定义、却在暗色里使用"这类错误就抓不到。

比较对象是**文件字节**，不是 stdout —— A-1/A-2 的判据就是"基线文件没变"；
`.gitattributes` 给 `benchmarks/*.txt` 标了 `-text`，防检出时被 CRLF 化。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIGHT = ROOT / "benchmarks" / "css_snapshot_light.txt"
DARK = ROOT / "benchmarks" / "css_snapshot_dark.txt"


def _snapshots() -> tuple[bytes, bytes]:
    code = (
        "import sys; sys.path.insert(0, r'%s');"
        "import importlib.util as u;"
        "spec=u.spec_from_file_location('snap', r'%s');"
        "m=u.module_from_spec(spec); spec.loader.exec_module(m);"
        "l,d=m.snapshots();"
        "sys.stdout.buffer.write(l.encode('utf-8'));"
        "sys.stdout.buffer.write(b'\\x00');"
        "sys.stdout.buffer.write(d.encode('utf-8'))"
    ) % (str(ROOT / "scripts"), str(ROOT / "scripts" / "css_snapshot.py"))
    out = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True).stdout
    light, dark = out.split(b"\x00", 1)
    return light, dark


def test_light_snapshot_matches_baseline_bytes() -> None:
    light, _ = _snapshots()
    assert LIGHT.is_file(), "缺少亮色基线，先跑 python scripts/css_snapshot.py --write"
    expected = LIGHT.read_bytes()
    assert light == expected, (
        f"亮色快照变了（视觉可能变了）：基线 {len(expected)} 字节 / 现在 {len(light)} 字节")


def test_dark_snapshot_matches_baseline_bytes() -> None:
    _, dark = _snapshots()
    assert DARK.is_file(), "缺少暗色基线，先跑 python scripts/css_snapshot.py --write"
    expected = DARK.read_bytes()
    assert dark == expected, (
        f"暗色快照变了（视觉可能变了）：基线 {len(expected)} 字节 / 现在 {len(dark)} 字节")


def test_snapshot_is_stable_across_runs() -> None:
    """同一输入两次运行逐字节一致 —— 否则这条验收器天天假红。"""
    assert _snapshots() == _snapshots()


def test_dark_snapshot_differs_from_light() -> None:
    """两份必须**内容不同**：完全相同说明暗色变量没被收集到（脚本静默退化成单表）。"""
    light, dark = _snapshots()
    assert light != dark, "亮/暗两份一样 —— 暗色作用域的变量没被展开"
