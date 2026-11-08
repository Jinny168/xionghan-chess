"""把 `web/css/app.css` 摊平成**有序的声明快照**，用于令牌化"零视觉变化"验收。

输出每行 `选择器|属性|值`，`var()` 按作用域**展开成字面色**。为什么要展开：
令牌化的本质就是把字面值换成 `var()`，不展开的话快照必然变，验收就退化成文字比对。

## 亮 / 暗两份
同名变量在 `:root` 与 `body[data-system-theme="dark"]` 里各有一份值。
单表会让后者覆盖前者，`var(--red)` 只留一个值 —— 那么"只在 :root 定义、却在暗色里使用"
这类错误就抓不到。所以生成两份：暗色那份的键带作用域后缀 `@dark`。

## 口径
- **sha 一律按基线文件字节算**（不是 stdout）：A-1/A-2 的判据是"文件没变"；
- 文件统一 LF 换行，`.gitattributes` 对该路径标 `-text`，防止检出时被转成 CRLF；
- 不排序（保持文件内的出现顺序），剔注释与令牌定义本身。

用法：
    python scripts/css_snapshot.py             # 打到 stdout（亮色段）
    python scripts/css_snapshot.py --write     # 写两份基线
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "web" / "css" / "app.css"
LIGHT = ROOT / "benchmarks" / "css_snapshot_light.txt"
DARK = ROOT / "benchmarks" / "css_snapshot_dark.txt"

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


def variable_tables(rules):
    """分别收集亮色（:root）与暗色（含 data-system-theme="dark"）的变量表。"""
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for selector, body in rules:
        decls = [(p, v) for p, v in split_declarations(body) if p.startswith("--")]
        if not decls:
            continue
        if ":root" in selector:
            light.update(dict(decls))
        if "data-system-theme" in selector:
            dark.update(dict(decls))
    merged_dark = {**light, **dark}     # 暗色作用域继承亮色再覆盖
    return light, merged_dark


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


def snapshots() -> tuple[str, str]:
    text = strip_comments(CSS.read_text(encoding="utf-8"))
    rules = split_rules(text)
    light_table, dark_table = variable_tables(rules)
    return render(rules, light_table), render(rules, dark_table, "@dark")


def main() -> None:
    light, dark = snapshots()
    if "--write" in sys.argv:
        for path, body in ((LIGHT, light), (DARK, dark)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8", newline="\n")
            print(f"{path.name}: {len(body.splitlines())} 行")
    else:
        # 走 buffer：Windows 上 sys.stdout 会把 \n 转成 \r\n，手工 diff 会误判"全文件都变了"
        sys.stdout.buffer.write(light.encode("utf-8"))


if __name__ == "__main__":
    main()
