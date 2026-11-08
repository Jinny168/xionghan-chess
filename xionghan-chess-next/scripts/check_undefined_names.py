"""静态检查：模块里有没有用到「文件内从未绑定过、也不是内置」的名字。

## 为什么需要这个（实测教训）
阶段1 把 `BoardWidget` 从 app.py 搬到 ui/ 后，冒烟测试抓到 `t` 未导入；
但 `math`（动画才用到）和 `Path`（背景路径才用到）**冒烟完全覆盖不到** ——
Qt 只在走到那行时才抛，而动画/背景加载在 offscreen 冒烟里不一定被触发。
这个脚本把它们静态挖了出来。

## 判据（刻意做得"宽"）
收集**文件内任何作用域**绑定过的名字（import / 赋值 / 参数 / def / class / 推导式 /
except-as / with-as / global），再加上内置名与 `__file__` 等模块级魔法名。
只要一个 Load 的名字不在这个集合里就报 —— 宁可漏报，不要噪声。
（它**不是** pyflakes，不做作用域分析；目的是"抓拼错/漏 import 的裸名字"。）

用法：
    python scripts/check_undefined_names.py [文件...]
    # 不传文件名则检查 src/xionghan_chess/desktop/ 下所有 .py

退出码：0 = 干净；1 = 有未定义引用。
"""
from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path

MAGIC = {"__file__", "__name__", "__doc__", "__package__", "__spec__", "__loader__",
         "__builtins__", "__annotations__", "self", "cls"}
BUILTINS = set(dir(builtins)) | MAGIC


def bound_names(tree: ast.AST) -> set[str]:
    """文件内任何作用域绑定过的名字（过近似，刻意低噪声）。"""
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.arg):
            out.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            out.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                out.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            out.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            out |= set(node.names)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
    return out


def check(path: Path) -> list[tuple[str, int, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    bound = bound_names(tree)
    problems: list[tuple[str, int, str, str]] = []

    def scope_of(node: ast.AST) -> str:
        return getattr(node, "name", "<module>")

    # 用父链推"最近的函数名"，只为报错定位好用
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in bound or node.id in BUILTINS:
                continue
            where, cur = "<module>", parents.get(node)
            while cur is not None:
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    where = cur.name
                    break
                cur = parents.get(cur)
            problems.append((path.name, node.lineno, where, node.id))
    return problems


def main(argv: list[str]) -> int:
    if argv:
        targets = [Path(a) for a in argv]
    else:
        root = Path("src/xionghan_chess/desktop")
        targets = sorted(root.rglob("*.py"))

    total = 0
    for path in targets:
        problems = check(path)
        if problems:
            total += len(problems)
            print(f"  FAIL {path}")
            for name, line, where, ident in sorted(set(problems)):
                print(f"       {name}:{line}  {where}()  ->  {ident}")
        else:
            print(f"  OK   {path}")

    if total:
        print(f"UNDEFINED_NAMES_FAIL: {total} 处")
        return 1
    print("UNDEFINED_NAMES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
