"""静态检查：桌面端 public 方法的类型标注覆盖率（阶段1 S1-4 的门禁）。

## 为什么需要
`app.py` 从 1197 行拆到 552 行后，方法变多、职责变散 —— 没有注解时
「这个参数到底收 Game 还是 dict」「这个函数返回 None 还是值」只能靠通读实现判断。
S1-4 要求把覆盖率从 6.2% 拉到 ≥85%。**如果不设门，下一次改动会悄悄退回去。**

## 判据
- 只统计**模块级函数**与**类方法**（含嵌套回调，因为它们也是要维护的接口）；
- 每个参数（跳过 self / cls）算 1 项，返回值算 1 项；
- 参数带注解即计分，返回注解存在即计分；
- 默认只查 `src/xionghan_chess/desktop/` 下的模块，可用 `--min` 调门槛。

退出码：0 = 达标；1 = 低于门槛。
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

DEFAULT_ROOT = Path("src/xionghan_chess/desktop")
DEFAULT_MIN = 85.0
SKIP_PARAMS = {"self", "cls"}


def coverage(path: Path) -> tuple[int, int, list[str]]:
    """返回 (已注解项, 总项, 缺失明细)。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    annotated = total = 0
    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        for arg in args:
            if arg.arg in SKIP_PARAMS:
                continue
            total += 1
            if arg.annotation is not None:
                annotated += 1
            else:
                missing.append(f"L{node.lineno} {node.name}({arg.arg})")
        total += 1
        if node.returns is not None:
            annotated += 1
        else:
            missing.append(f"L{node.lineno} {node.name} -> 返回值")
    return annotated, total, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查桌面端类型标注覆盖率")
    parser.add_argument("files", nargs="*", help="要检查的 .py（默认整个 desktop 包）")
    parser.add_argument("--min", type=float, default=DEFAULT_MIN, help="覆盖率门槛（%%）")
    args = parser.parse_args(argv)

    targets = [Path(item) for item in args.files] if args.files else sorted(DEFAULT_ROOT.rglob("*.py"))
    targets = [item for item in targets if item.is_file() and "__pycache__" not in item.parts]
    if not targets:
        print("没有找到要检查的文件", file=sys.stderr)
        return 1

    failures = 0
    grand_annotated = grand_total = 0
    for path in targets:
        annotated, total, missing = coverage(path)
        if total == 0:
            continue
        grand_annotated += annotated
        grand_total += total
        ratio = annotated * 100 / total
        status = "OK  " if ratio >= args.min else "FAIL"
        print(f"{status} {path}  {annotated}/{total} = {ratio:.1f}%")
        if ratio < args.min:
            failures += 1
            for item in missing:
                print(f"       缺注解 {item}")

    if grand_total == 0:
        print("没有任何函数被统计", file=sys.stderr)
        return 1
    overall = grand_annotated * 100 / grand_total
    print(f"\n合计 {grand_annotated}/{grand_total} = {overall:.1f}%（门槛 {args.min:.0f}%）")
    if failures:
        print(f"ANNOTATION_COVERAGE_FAILED（{failures} 个文件未达标）")
        return 1
    print("ANNOTATION_COVERAGE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
