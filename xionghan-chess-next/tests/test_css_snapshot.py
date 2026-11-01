"""令牌化 A 阶段的验收器：`app.css` 的声明快照必须与基线**逐字节**相同。

令牌化的唯一目的是"把字面值换成 var()，**视觉一点不变**"。所以验收不是"能跑"，
而是：展开 `var()` 之后的 `选择器|属性|值` 序列与改前完全一致。

三份基线（亮 / 系统暗 / 棋盘暗），作用域后缀分别为 无 / `@dark` / `@board-dark`：
单表会让同名变量互相覆盖，"只在 :root 定义、却在暗色里使用"这类错误就抓不到；
而 `data-board-theme="dark"` 的覆写与 `data-system-theme="dark"` **取值不同**，
少了第三份，S1 的声明就只能按"根值 / S2 值"展开 —— 记下的是名义值而不是实际渲染值。

比较对象是**文件字节**，不是 stdout —— A-1/A-2 的判据就是"基线文件没变"；
`.gitattributes` 给 `benchmarks/*.txt` 标了 `-text`，防检出时被 CRLF 化。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINES = {
    "light": ROOT / "benchmarks" / "css_snapshot_light.txt",
    "dark": ROOT / "benchmarks" / "css_snapshot_dark.txt",
    "board-dark": ROOT / "benchmarks" / "css_snapshot_board_dark.txt",
}
SCOPES = ("light", "dark", "board-dark")


def _snapshots() -> dict[str, bytes]:
    code = (
        "import sys; sys.path.insert(0, r'%s');"
        "import importlib.util as u;"
        "spec=u.spec_from_file_location('snap', r'%s');"
        "m=u.module_from_spec(spec); spec.loader.exec_module(m);"
        "s=m.snapshots();"
        "sys.stdout.buffer.write(b'\\x00'.join(s[k].encode('utf-8') for k in ('light','dark','board-dark')))"
    ) % (str(ROOT / "scripts"), str(ROOT / "scripts" / "css_snapshot.py"))
    out = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True).stdout
    parts = out.split(b"\x00")
    assert len(parts) == 3, f"期望 3 份快照，实际 {len(parts)} 份"
    return dict(zip(SCOPES, parts))


def _tables() -> dict[str, dict[str, str]]:
    """取三个作用域的变量表（与 `--write` 走同一条代码路径）。"""
    spec = importlib.util.spec_from_file_location(
        "css_snapshot_for_tests", ROOT / "scripts" / "css_snapshot.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = module.strip_comments(module.CSS.read_text(encoding="utf-8"))
    tables = module.variable_tables(module.split_rules(text))
    tables["_expand"] = module.expand  # type: ignore[assignment]
    return tables


def _first_mismatch(got: bytes, want: bytes) -> str:
    """定位第一处差异（行号 + 两侧内容）。

    只报字节数不够用：改动恰好等长时会出现"变了，但两边都是 45,198 字节"这种
    等于没说过的信息 —— 红证时我自己就撞上了。
    """
    got_lines, want_lines = got.split(b"\n"), want.split(b"\n")
    for index, (a, b) in enumerate(zip(got_lines, want_lines), 1):
        if a != b:
            return (f"首个差异在第 {index} 行\n"
                    f"  基线：{b.decode('utf-8', 'replace')[:200]}\n"
                    f"  现在：{a.decode('utf-8', 'replace')[:200]}")
    if len(got_lines) != len(want_lines):
        return f"行数不同：基线 {len(want_lines)} 行 / 现在 {len(got_lines)} 行"
    return "内容完全相同（不该走到这条断言）"


def _assert_matches_baseline(name: str, label: str) -> None:
    body = _snapshots()[name]
    expected = BASELINES[name]
    assert expected.is_file(), f"缺少{label}基线，先跑 python scripts/css_snapshot.py --write"
    want = expected.read_bytes()
    assert body == want, (
        f"{label}快照变了（视觉可能变了）：基线 {len(want)} 字节 / 现在 {len(body)} 字节\n"
        + _first_mismatch(body, want))


def test_light_snapshot_matches_baseline_bytes() -> None:
    _assert_matches_baseline("light", "亮色")


def test_dark_snapshot_matches_baseline_bytes() -> None:
    _assert_matches_baseline("dark", "暗色")


def test_board_dark_snapshot_is_its_own_scope() -> None:
    """第三份基线：S1（棋盘暗色）作用域，既要字节可比，也要**按 S1 自己的覆写**展开。

    两件事合一，因为它们验的是同一个命题"这份基线是真的"：
    ① 字节比对 —— 否则 `css_snapshot_board_dark.txt` 是没人比的死文件，S1 覆写改回去也没人发现；
    ② 证伪断言 —— 把 `variable_tables()` 里收集 `data-board-theme="dark"` 的那一步删掉，
    `board-dark` 表就退回根值（`#a38b66` / `#b5935e`），本条立刻红；也就是
    "名义值冒充实际值"这种错会被抓到。
    """
    _assert_matches_baseline("board-dark", "棋盘暗色")

    tables = _tables()
    expand = tables["_expand"]  # type: ignore[assignment]
    assert expand("var(--border-field)", tables["board-dark"]) == "#8c7d6a", (
        "board-dark 的 --border-field 没按 S1 覆写展开（拿到的是根值或 S2 值）")
    assert expand("var(--border-panel-soft)", tables["board-dark"]) == "#75624b", (
        "board-dark 的 --border-panel-soft 没按 S1 覆写展开（拿到的是根值或 S2 值）")


def test_border_field_differs_across_scopes() -> None:
    """三个作用域的 `--border-field` 两两不同 —— 证明作用域真的被区分开了。

    三者相同说明收集逻辑退化成"谁后写谁赢"（S2 在文件里更靠后，会把 S1 盖掉）。
    """
    tables = _tables()
    expand = tables["_expand"]  # type: ignore[assignment]
    values = {name: expand("var(--border-field)", tables[name]) for name in SCOPES}
    assert values == {"light": "#a38b66", "dark": "#86837d", "board-dark": "#8c7d6a"}, (
        f"三个作用域的 --border-field 不全是各自的值：{values}")
    assert len(set(values.values())) == 3, f"作用域没有区分开：{values}"


def test_snapshot_is_stable_across_runs() -> None:
    """同一输入两次运行逐字节一致 —— 否则这条验收器天天假红。"""
    assert _snapshots() == _snapshots()


def test_dark_snapshot_differs_from_light() -> None:
    """两份必须**内容不同**：完全相同说明暗色变量没被收集到（脚本静默退化成单表）。"""
    snaps = _snapshots()
    assert snaps["light"] != snaps["dark"], "亮/暗两份一样 —— 暗色作用域的变量没被展开"


def test_snapshot_has_no_cr() -> None:
    """快照文本里不得出现 `\\r`。

    这是**接口形态**的断言：`print`/`sys.stdout.write` 在 Windows 上会把 LF 转成 CRLF，
    于是"脚本输出 vs LF 基线"的 diff 会报"全文件都不同"（其实一行内容都没变）。
    把"比较双方必须是同一形态"写成断言，比每次人工 `tr -d '\\r'` 可靠。
    """
    for name, body in _snapshots().items():
        assert b"\r\n" not in body and b"\r" not in body, f"{name} 快照含 CR"
