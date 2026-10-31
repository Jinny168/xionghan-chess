"""把 `web/css/app.css` 摊平成**有序的声明快照**，用于令牌化"零视觉变化"验收。

输出每行 `选择器|属性|值`，其中值里的 `var(--x)` 已按 `:root`（及暗色作用域）展开成字面色。
为什么必须展开：令牌化的本质就是把字面值换成 `var()`，不展开的话快照必然变，
验收就退化成"文字比对"，反而看不出颜色有没有真的变。

稳定性要求：同输入两次运行输出逐字节一致 —— 不排序（保持文件里的出现顺序），
不输出注释，不做格式化猜测，只做"选择器 + 声明"的忠实摊平。

用法：
    python scripts/css_snapshot.py            # 打到 stdout
    python scripts/css_snapshot.py --write    # 覆盖基线文件
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "web" / "css" / "app.css"
BASELINE = ROOT / "benchmarks" / "css_snapshot_baseline.txt"

VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^()]*))?\)")


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def split_rules(text: str) -> list[tuple[str, str]]:
    """按最外层 `{}` 切规则，返回 [(selector, body)]。"""
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


def collect_vars(rules: list[tuple[str, str]]) -> dict[str, str]:
    """收集 `:root` 与暗色作用域的变量；后者只在带 `data-system-theme` 的规则里出现。"""
    table: dict[str, str] = {}
    for selector, body in rules:
        if ":root" in selector or "data-system-theme" in selector:
            for prop, value in split_declarations(body):
                if prop.startswith("--"):
                    table[prop] = value
    return table


def expand(value: str, table: dict[str, str], depth: int = 0) -> str:
    if depth > 8:
        return value

    def replace(match: re.Match[str]) -> str:
        name, fallback = match.group(1), match.group(2)
        if name in table:
            return expand(table[name], table, depth + 1)
        return (fallback or "").strip() or match.group(0)

    return VAR_RE.sub(replace, value)


def snapshot() -> str:
    text = strip_comments(CSS.read_text(encoding="utf-8"))
    rules = split_rules(text)
    table = collect_vars(rules)
    lines: list[str] = []
    for selector, body in rules:
        selector = " ".join(selector.split())
        for prop, value in split_declarations(body):
            if prop.startswith("--"):          # 令牌定义本身不属于"声明快照"
                continue
            lines.append(f"{selector}|{prop}|{expand(value, table)}")
    return "\n".join(lines) + "\n"


def main() -> None:
    text = snapshot()
    if "--write" in sys.argv:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(text, encoding="utf-8", newline="\n")
        print(f"基线已写入 {BASELINE}（{len(text.splitlines())} 行）")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
