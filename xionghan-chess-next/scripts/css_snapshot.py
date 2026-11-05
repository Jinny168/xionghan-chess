"""把 `web/css/app.css` 摊平成**有序的声明快照**，用于令牌化"零视觉变化"验收。

输出每行 `选择器|属性|值`，`var()` 按作用域**展开成字面色**。为什么要展开：
令牌化的本质就是把字面值换成 `var()`，不展开的话快照必然变，验收就退化成文字比对。

## 亮 / 暗 / 棋盘暗三个作用域
同名变量在 `:root`、`body[data-system-theme="dark"]`、`body[data-board-theme="dark"]` 里各有值。
单表会让后者覆盖前者，`var(--red)` 只留一个值 —— 那么"只在 :root 定义、却在暗色里使用"
这类错误就抓不到。

**为什么必须有第三个作用域**：`data-board-theme="dark"` 也覆写了 `--border-panel-soft`
与 `--border-field`，两者取值与 `data-system-theme="dark"` **不同**。只看两个作用域时，
S1 的声明会被按"根值 / S2 值"展开 —— 记下的是**名义值而不是实际渲染值**，
于是最该被守住的那几条 S1 覆写反而没有基线。

三个作用域各自独立展开（不模拟"S1+S2 同时命中"的叠加，那是渲染期行为）：
`light`（无后缀）/ `dark`（`@dark`）/ `board-dark`（`@board-dark`）。

## 口径
- **sha 一律按基线文件字节算**（不是 stdout）：A-1/A-2 的判据是"文件没变"；
- 文件统一 LF 换行，`.gitattributes` 对该路径标 `-text`，防止检出时被转成 CRLF；
- 不排序（保持文件内的出现顺序），剔注释与令牌定义本身。

用法：
    python scripts/css_snapshot.py             # 打到 stdout（亮色段）
    python scripts/css_snapshot.py --write     # 写三份基线
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "web" / "css" / "app.css"
LIGHT = ROOT / "benchmarks" / "css_snapshot_light.txt"
DARK = ROOT / "benchmarks" / "css_snapshot_dark.txt"
BOARD_DARK = ROOT / "benchmarks" / "css_snapshot_board_dark.txt"

SCOPES = {"light": "", "dark": "@dark", "board-dark": "@board-dark"}
BASELINES = {"light": LIGHT, "dark": DARK, "board-dark": BOARD_DARK}

VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^()]*))?\)")


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def split_rules(text: str) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    depth = 0
    selector_start = 0
    body_start = -1
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                body_start = index + 1
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and body_start >= 0:
                rules.append((text[selector_start:body_start - 1].strip(), text[body_start:index]))
                selector_start = index + 1
    return rules


def split_declarations(body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    depth = 0
    start = 0
    for index, char in enumerate(body):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == ";" and depth == 0:
            chunk = body[start:index]
            if ":" in chunk:
                prop, value = chunk.split(":", 1)
                out.append((prop.strip(), value.strip()))
            start = index + 1
    tail = body[start:]
    if ":" in tail:
        prop, value = tail.split(":", 1)
        out.append((prop.strip(), value.strip()))
    return out


def variable_tables(rules) -> dict[str, dict[str, str]]:
    """三个作用域的自定义属性表：`light` / `dark` / `board-dark`。

    每个作用域都继承 `:root` 再被自己的覆写覆盖；**互相之间不叠加** ——
    `data-board-theme="dark"` 与 `data-system-theme="dark"` 同时命中时谁赢是渲染期
    的层叠顺序问题（S2 在文件里更靠后），快照不模拟它，只保证各自的表是真的。
    """
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    board_dark: dict[str, str] = {}
    for selector, body in rules:
        decls = [(p, v) for p, v in split_declarations(body) if p.startswith("--")]
        if not decls:
            continue
        if ":root" in selector:
            light.update(dict(decls))
        elif 'data-system-theme="dark"' in selector:
            dark.update(dict(decls))
        elif 'data-board-theme="dark"' in selector:
            board_dark.update(dict(decls))
    return {
        "light": dict(light),
        "dark": {**light, **dark},
        "board-dark": {**light, **board_dark},
    }


def expand(value: str, table: dict[str, str], depth: int = 0) -> str:
    if depth > 8:
        return value

    def replace(match: re.Match[str]) -> str:
        name, fallback = match.group(1), match.group(2)
        if name in table:
            return expand(table[name], table, depth + 1)
        return (fallback or "").strip() or match.group(0)

    return VAR_RE.sub(replace, value)


def render(rules, table: dict[str, str], suffix: str = "") -> str:
    lines: list[str] = []
    for selector, body in rules:
        selector = " ".join(selector.split()) + suffix
        for prop, value in split_declarations(body):
            if prop.startswith("--"):
                continue
            lines.append(f"{selector}|{prop}|{expand(value, table)}")
    return "\n".join(lines) + "\n"


def snapshots() -> dict[str, str]:
    """三个作用域各展开一份，键为 `light` / `dark` / `board-dark`。"""
    text = strip_comments(CSS.read_text(encoding="utf-8"))
    rules = split_rules(text)
    tables = variable_tables(rules)
    return {name: render(rules, tables[name], SCOPES[name]) for name in SCOPES}


def main() -> None:
    snaps = snapshots()
    if "--write" in sys.argv:
        for name, path in BASELINES.items():
            body = snaps[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8", newline="\n")
            print(f"{path.name}: {len(body.splitlines())} 行")
    else:
        # 走 buffer：Windows 上 sys.stdout 会把 \n 转成 \r\n，手工 diff 会误判"全文件都变了"
        sys.stdout.buffer.write(snaps["light"].encode("utf-8"))


if __name__ == "__main__":
    main()
