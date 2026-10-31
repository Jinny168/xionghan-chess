"""裸色禁令（A-3）：除令牌定义与 allowlist 之外，出现 hex 就红。

**allowlist 必须由 `scripts/gen_color_allowlist.py` 生成**，不得手写 ——
手写白名单会变成"永远不缩的垃圾桶"。B 阶段每收编一批颜色就重跑一次，条目应**单调下降**。

豁免三条（缺一不可）：
1. `--name: #hex` 令牌定义（它只是常量，不渲染）；
2. `benchmarks/color_allowlist.txt` 里登记的值；
3. 注释里的 hex —— **单独计数**，不进 allowlist（防止把颜色藏进注释绕过检查）。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "benchmarks" / "color_allowlist.txt"
SCRIPT = ROOT / "scripts" / "gen_color_allowlist.py"


def _load():
    spec = importlib.util.spec_from_file_location("gen_color_allowlist", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _allowlist() -> dict[str, int]:
    entries: dict[str, int] = {}
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, count = line.rsplit(":", 1)
        entries[key] = int(count)
    return entries


def test_no_raw_colors_outside_the_allowlist() -> None:
    module = _load()
    raw, tokens, comments = module.scan()
    allowed = _allowlist()

    unexpected = [f"{key}（{count} 处）" for key, count in sorted(raw.items()) if key not in allowed]
    assert not unexpected, "出现未登记的裸色：\n" + "\n".join(unexpected)

    covered = sum(count for key, count in raw.items() if key in allowed)
    print(
        f"allowlist 覆盖 {len(allowed)} 条 / 当前实际 {len(raw)} 条（{sum(raw.values())} 处）"
        f"；已登记处数 {covered}；令牌定义 {sum(tokens.values())} 处；注释内 {sum(comments.values())} 处"
    )
    assert len(raw) <= len(allowed), "实际条目多于 allowlist —— allowlist 该重生成（应收紧，不该变长）"


def test_allowlist_is_generated_and_idempotent() -> None:
    """allowlist 必须与生成结果**逐字节一致**，且两次生成相同（防手改、防不幂等）。"""
    assert ALLOWLIST.is_file(), "缺少 allowlist，先跑 scripts/gen_color_allowlist.py --write"
    first = subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True).stdout
    second = subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True).stdout
    assert first == second, "生成结果不稳定"
    # 比较前统一行尾：Windows 上 `subprocess` 拿到的 stdout 与磁盘文件可能一处 CRLF 一处 LF，
    # 那是**载体差异不是内容差异**（这一轮已经被同样的坑坑过一次）。
    normalise = lambda blob: blob.replace(b"\r\n", b"\n")
    assert normalise(first) == normalise(ALLOWLIST.read_bytes()), \
        "allowlist 与生成结果不一致（可能被手改）"
