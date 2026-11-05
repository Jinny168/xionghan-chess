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
    """第三份基线：S1（棋盘暗色）作用域，既要字节可比，也要**只染棋盘**。

    2026-11-02 收窄了棋盘轴：`data-board-theme="dark"` 只保留 `--board-*`，
    面板/弹窗/按钮的暗色一律由 `data-system-theme` 负责。所以这里断言的是**相反的**事：
    棋盘轴**不再**覆写边框令牌（拿到的是根值），但棋盘底色确实变了。
    这条比"三个值互不相同"更有意义 —— 它验的是职责边界，不是"作用域有没有被收集到"。
    """
    _assert_matches_baseline("board-dark", "棋盘暗色")

    tables = _tables()
    expand = tables["_expand"]  # type: ignore[assignment]
    assert expand("var(--board-bg)", tables["board-dark"]) == "#2c2c2c", \
        "棋盘对角色的覆写丢了（board-dark 的 --board-bg 应仍是 #2c2c2c）"
    assert expand("var(--border-field)", tables["board-dark"]) == "#a38b66", \
        "棋盘轴不该再覆写 --border-field（面板边框归界面轴管）"
    assert expand("var(--border-panel-soft)", tables["board-dark"]) == "#b5935e", \
        "棋盘轴不该再覆写 --border-panel-soft"


def test_board_theme_only_touches_the_board() -> None:
    """棋盘暗色的选择器只允许命中棋盘相关元素。

    这是收窄后的**核心契约**：选"深木棋盘"不该把面板、对话框、按钮、聊天一起变黑。
    直接扫 CSS 源码，比看截图可靠 —— 截图只能证明"这一套主题这一屏没问题"。
    """
    import re
    raw = (ROOT / "web" / "css" / "app.css").read_text(encoding="utf-8")
    # 先剥注释：否则捕获到的"选择器"会把前面的注释一起带进来，匹配必然失败
    css = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    # 允许的形态：`body[data-board-theme="dark"]` 本身，或其后接棋盘容器
    allowed = re.compile(
        r'^body\[data-board-theme="dark"\]'
        r'(?:\.board-shell|\.board-stage|canvas|\.board-|:before)?')
    offenders = []
    for match in re.finditer(r'([^{}]+)\{', css):
        selector_text = match.group(1).strip()
        if 'data-board-theme="dark"' not in selector_text:
            continue
        for one in selector_text.split(","):
            one = one.strip()
            if 'data-board-theme="dark"' not in one:
                continue
            if not allowed.match(one):
                offenders.append(one)
    assert not offenders, ("棋盘暗色越界到非棋盘元素了：" + "；".join(offenders[:5]))


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
