"""生成"裸色 allowlist"：`benchmarks/color_allowlist.txt`。

**必须生成、不许手写** —— 手写的白名单会变成"永远不缩的垃圾桶".
B 阶段每收编一批颜色就重跑一次，条目数应当**单调下降**。

口径（与 `tests/test_no_raw_colors.py` 完全一致）：
- 扫描面：`web/css/app.css`、`src/**/desktop/app.py`、`src/**/desktop/ui/*.py`；
- 统计所有 `#rgb` / `#rrggbb` / `#rrggbbaa`；
- **豁免**：`--name: #hex` 的令牌定义、以及注释（`/* … */` 与 `# …` 行）——注释里的 hex 单独计数，
  不进 allowlist（防止把颜色藏进注释绕过检查）；
- 输出 `文件:值:出现次数`，按文件与值排序，保证同状态两次输出**逐字节一致**。

用法：
    python scripts/gen_color_allowlist.py          # 打到 stdout
    python scripts/gen_color_allowlist.py --write  # 覆盖 allowlist 文件
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "color_allowlist.txt"
HEX_RE = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"(?m)^\s*#.*$")


def targets() -> list[Path]:
    files = [ROOT / "web" / "css" / "app.css"]
    desktop = ROOT / "src" / "xionghan_chess" / "desktop"
    files.append(desktop / "app.py")
    files.extend(sorted((desktop / "ui").glob("*.py")))
    return [p for p in files if p.is_file()]


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    """把指定区间替换成等长空格，保持偏移不变。"""
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def scan() -> tuple[Counter, Counter, Counter]:
    """返回 (raw 计数, 令牌定义计数, 注释计数)。"""
    raw: Counter = Counter()
    tokens: Counter = Counter()
    comments: Counter = Counter()
    for path in targets():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()

        comment_spans = [(m.start(), m.end()) for m in BLOCK_COMMENT.finditer(text)]
        comment_spans += [(m.start(), m.end()) for m in LINE_COMMENT.finditer(text)]
        for match in HEX_RE.finditer(text):
            if any(a <= match.start() < b for a, b in comment_spans):
                comments[f"{rel}:{match.group(0).lower()}"] += 1

        masked = _mask(text, comment_spans)
        # 令牌定义：`--name: #hex`
        for match in re.finditer(r"--[A-Za-z0-9_-]+\s*:\s*(#[0-9a-fA-F]{3,8})", masked):
            tokens[f"{rel}:{match.group(1).lower()}"] += 1
        # 其余 hex 都算裸值
        for match in HEX_RE.finditer(masked):
            span_start = max(masked.rfind(";", 0, match.start()), masked.rfind("{", 0, match.start()))
            prefix = masked[span_start + 1:match.start()]
            if re.match(r"\s*--[A-Za-z0-9_-]+\s*:\s*$", prefix):
                continue          # 已在令牌统计里
            raw[f"{rel}:{match.group(0).lower()}"] += 1
    return raw, tokens, comments


def render(raw: Counter) -> str:
    lines = [f"{key}:{count}" for key, count in sorted(raw.items())]
    return "\n".join(lines) + ("\n" if lines else "")


def main() -> None:
    raw, tokens, comments = scan()
    text = render(raw)
    if "--write" in sys.argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"allowlist 已写入 {OUT.name}：{len(raw)} 条 / {sum(raw.values())} 处")
        print(f"令牌定义 {sum(tokens.values())} 处；注释内 hex {sum(comments.values())} 处（不进 allowlist）")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
