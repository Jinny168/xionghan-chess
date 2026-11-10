"""门禁自检：node 依赖型门禁不许静默蒸发（P0-1 防回潮）。

本文件**不测棋规**，测的是「门禁本身到底跑没跑」。背景：三处 node 依赖用例原先各自写

    if not shutil.which("node"): pytest.skip(...)

于是没有 node 的机器上 pytest 全绿而整批对拍一条没跑（docs/AUDIT_TESTABILITY_1.7.0.md
§5 表格 + §6 P0-1，横跨两个版本未修）。守卫现已收到 `tests/_node_guard.py` 一份，
本文件既验行为、也验"没人偷偷复制第二份守卫或重新引入 skip"。

断言分六组，各自防一种"绿着但没证明"：

1. **源码 lint**：三个 node 依赖模块里不得再出现用例级 skip 退化；
2. **唯一 skip 入口**：每个模块只允许 `pytestmark = mark` 这一行，且 `mark` 来自
   `_node_guard.module_skip_mark()`；env 判定只允许出现在 `_node_guard.py`。
3. **无重复守卫**：三个模块不得自带 `shutil.which("node")` / `XH_ALLOW_NO_NODE` /
   `NO_NODE_REASON =`（防"12 处隐性同步点"再添第 13 处）。
4. **结构 lint**：凡起 node 子进程的函数都必须先过 `require_node()`。
5. **运行时正向**：node 可用时，对拍必须真的**执行**（通过数 > 0、skip 数 = 0）。
6. **运行时反向**：node 缺失且未放宽时，三处门禁都必须**变红**——对拍模块连
   `--noconftest` 也红（失败写在模块内）；设了 `XH_ALLOW_NO_NODE=1` 才回到 skip，
   且 skip 在输出里可见。

第 5/6 组跑的是真子进程 pytest（不是 mock），所以它们同时是"门禁可执行、可红"的运行时证据。
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
GUARD = TESTS / "_node_guard.py"

# 三个 node 依赖模块（守卫的唯一消费者）。
NODE_DEPENDENT = (
    ("test_cross_engine.py", "跨引擎镜像对拍"),
    ("test_offline_puzzles.py", "离线题库 ↔ 离线引擎"),
    ("test_p0_rules.py", "黄金值经 rules probe 复核"),
)

# 参数化 id 故意不带 ".py"：conftest 的对拍归属判定以前是**子串匹配**，形如
# `…::test_x[test_cross_engine.py]` 的 id 会被误计成对拍用例（实测把汇总行从
# 「收集 81 | 通过 81」污染成「通过 84」）。现在 conftest 改成文件名精确比对，
# id 这里再做一层：不让本文件自己再制造同类形状。
NODE_DEPENDENT_IDS = [name.removesuffix(".py") for name, _ in NODE_DEPENDENT]

GATE_SUMMARY = re.compile(r"通过 (\d+) \| 失败 (\d+) \| 跳过 (\d+)")

# 子进程实测用的对拍子集：三条覆盖 node 的三条不同支路（legalAll / positionKey /
# resurrect），又小到能在主门禁里跑完（4 条全参数化太重，这里只取 traditional 一档，
# 因为本文件证明的是"门禁真的执行"，不是"每一档都对"）。
PARITY_SUBSET = " or ".join(
    (
        "(test_initial_legal_moves_and_check_match_android_offline and traditional)",
        "test_position_key_matches_offline_byte_for_byte",
        "test_resurrect_pawn_parity_between_python_and_offline",
    )
)

# --- 1. 源码 lint -----------------------------------------------------------
#
# 只禁"逐条退化"的写法。`pytest.mark.skip` 不在名单里：它是逃生阀唯一允许的形态
# （且只允许出现在 `_node_guard.module_skip_mark()` 内），由第 2/3 组单独管。
_SKIP_TOKENS = (
    (re.compile(r"\bpytest\.skip\b"), "pytest.skip（用例级静默跳过）"),
    (re.compile(r"\bpytest\.importorskip\b"), "pytest.importorskip（缺依赖即静默跳过）"),
    (re.compile(r"\bSkipTest\b|\bself\.skipTest\b"), "unittest SkipTest"),
    (re.compile(r"\bpytest\.xfail\b"), "pytest.xfail（把未执行伪装成已知问题）"),
)


def _skip_offences(source: str, name: str = "<source>") -> list[str]:
    """Return one line per case-level skip construct found in `source`."""
    offences: list[str] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for pattern, label in _SKIP_TOKENS:
            if pattern.search(line):
                offences.append(f"{name}:{lineno}: {label} -> {line.strip()}")
    return offences


def test_skip_lint_is_self_validated_before_it_judges_anything():
    """先证明这把尺子会命中也会不命中，再用它去判三个模块。

    构造了 4 条**应命中**样本（含修复前那行原文）和 4 条**应不命中**样本（含修复后
    的写法），逐条比对后报数；尺子自身不灵时本用例先红，避免"跑不崩=跑得对"。
    """
    samples: list[tuple[str, str, bool]] = [
        (
            "修复前原文（helper 里 shutil.which 判空后跳过）",
            '    if not shutil.which("node"):\n'
            '        pytest.skip("Node.js is required for cross-engine parity tests")\n',
            True,
        ),
        ("裸 skip（无理由）", "def test_x():\n    pytest.skip()\n", True),
        ("缺依赖 importorskip", 'node = pytest.importorskip("node")\n', True),
        ("unittest SkipTest", "raise unittest.SkipTest('no node')\n", True),
        ("修复后写法：只调硬失败守卫", "def helper():\n    require_node()\n", False),
        ("等价但不跳过：断言 node 存在", 'assert shutil.which("node"), "need node"\n', False),
        ("pytest.fail 硬失败", 'pytest.fail("node missing", pytrace=False)\n', False),
        ("注释里提到跳过也算不命中（不误报注释行）", "# 这里以前是 pytest.skip，已改为 pytest.fail\n", False),
    ]
    wrong = [(name, expected) for name, source, expected in samples if bool(_skip_offences(source)) != expected]
    print(
        f"[GATE-LINT] 自验 {len(samples) - len(wrong)}/{len(samples)} 通过"
        f"（应命中 4 条 / 应不命中 4 条；实际命中 "
        f"{sum(1 for _, s, _ in samples if _skip_offences(s))} 条）"
    )
    assert not wrong, f"skip lint 自验失败：{wrong}"


@pytest.mark.parametrize("filename,label", NODE_DEPENDENT, ids=NODE_DEPENDENT_IDS)
def test_node_dependent_module_has_no_case_level_skip(filename: str, label: str):
    """防回潮：三个 node 依赖模块里不许再出现用例级 skip。"""
    source = (TESTS / filename).read_text(encoding="utf-8")
    offences = _skip_offences(source, filename)
    assert not offences, (
        f"{label}（{filename}）又出现用例级 skip —— 缺 node 时门禁会静默蒸发：\n"
        + "\n".join(offences)
        + "\n改用 `_node_guard.require_node()`（缺 node 直接 pytest.fail，"
        "逃生阀 XH_ALLOW_NO_NODE=1）。"
    )


# --- 2. 唯一 skip 入口 ------------------------------------------------------


@pytest.mark.parametrize("filename,label", NODE_DEPENDENT, ids=NODE_DEPENDENT_IDS)
def test_only_the_escape_valve_may_skip_module(filename: str, label: str):
    """模块级 skip 只允许一行，且必须由 `module_skip_mark()` 提供。"""
    source = (TESTS / filename).read_text(encoding="utf-8")
    marks = [line.strip() for line in source.splitlines() if "pytestmark" in line or "pytest.mark.skip" in line]
    assert marks == ["pytestmark = mark"], (
        f"{label}（{filename}）的模块级 skip 入口应恰好是 `pytestmark = mark` 一行，实际：{marks}"
    )
    assert "if (mark := module_skip_mark()) is not None:" in source, (
        f"{label}（{filename}）的 skip 没走 `module_skip_mark()` 的 env 门控"
    )


def test_escape_valve_condition_lives_in_the_guard_module_only():
    """env 判定（`XH_ALLOW_NO_NODE == "1"`）只允许出现在 `_node_guard.py` 一处。"""
    guard = GUARD.read_text(encoding="utf-8")
    assert guard.count('os.environ.get("XH_ALLOW_NO_NODE") == "1"') == 1, "_node_guard.py 里 env 判定必须只有一处"
    assert "def module_skip_mark()" in guard and "if NODE is None and ALLOW_NO_NODE:" in guard
    assert guard.count("pytest.mark.skip") == 1, "整模块 skip 只允许 module_skip_mark 里那一次"
    assert "def require_node()" in guard and "pytest.fail(NO_NODE_REASON" in guard


@pytest.mark.parametrize("filename,label", NODE_DEPENDENT, ids=NODE_DEPENDENT_IDS)
def test_modules_do_not_carry_a_second_copy_of_the_guard(filename: str, label: str):
    """三个模块只能 import 守卫，不得自带第二份（新增同步点的味道）。"""
    source = (TESTS / filename).read_text(encoding="utf-8")
    for token in ('shutil.which("node")', "XH_ALLOW_NO_NODE", "NO_NODE_REASON ="):
        assert token not in source, (
            f"{label}（{filename}）自带了守卫片段 {token!r} —— 请 import `_node_guard`，"
            "不要复制第二份守卫（那正是本项目『隐性同步点』的老毛病）"
        )
    assert "from _node_guard import" in source, f"{label}（{filename}）没有接上共享守卫"


# --- 3. 汇总行的归属判定 -----------------------------------------------------


def _load_conftest():
    """把 `tests/conftest.py` 当普通模块加载，只为了单测它的两个纯函数。"""
    spec = importlib.util.spec_from_file_location("xh_tests_conftest", TESTS / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_counter_counts_only_the_parity_file_not_lookalikes():
    """汇总行必须按**文件名精确**归属，子串匹配会把本文件的参数化 id 数进去。

    实测过的事故：`…::test_x[test_cross_engine.py]` 这种 id 里含 `test_cross_engine.py`
    这串字，旧实现 `PARITY_MODULE in nodeid` 把它当对拍用例，于是汇总行从
    「收集 81 | 通过 81」变成「**通过 84**」——CI 里那条 `通过 == 收集` 断言会因此
    假红，而人看到的是"门禁自己算错了"。
    """
    conf = _load_conftest()
    samples = [
        ("tests/test_cross_engine.py::test_x[traditional]", True),
        ("xionghan-chess-next/tests/test_cross_engine.py::test_w", True),
        ("tests/test_gate_integrity.py::test_y[test_cross_engine.py]", False),
        ("tests/test_cross_engine_extra.py::test_z", False),
        ("tests/test_cross_engine.py", True),
    ]
    wrong = [(nodeid, expected) for nodeid, expected in samples if conf._is_parity_nodeid(nodeid) is not expected]
    hits = sum(1 for _, expected in samples if expected)
    print(
        f"[GATE-COUNTER] 归属判定自验 {len(samples) - len(wrong)}/{len(samples)} 通过"
        f"（应命中 {hits} 条 / 应不命中 {len(samples) - hits} 条）"
    )
    assert not wrong, f"对拍用例归属判定错误：{wrong}"
    # 子串法对第 3 条会判成 True —— 这正是本用例存在的理由。
    assert "test_cross_engine.py" in samples[2][0], "样本 3 已不含形近子串，本用例失去意义"


# --- 4. 结构 lint -----------------------------------------------------------

_NODE_LAUNCHERS = (
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
)


def _dotted(node: ast.AST) -> str:
    func, parts = node, []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))


def _callee_names(node: ast.AST) -> set[str]:
    """Dotted names of every call inside `node` (`subprocess.run` -> 'subprocess.run')."""
    return {_dotted(sub.func) for sub in ast.walk(node) if isinstance(sub, ast.Call)}


def _node_launchers(node: ast.AST) -> list[ast.Call]:
    """`subprocess.*` calls in this subtree whose argument literals name `node`."""
    found: list[ast.Call] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call) or _dotted(sub.func) not in _NODE_LAUNCHERS:
            continue
        literals = {
            item.value for item in ast.walk(sub) if isinstance(item, ast.Constant) and isinstance(item.value, str)
        }
        if any(word.strip().lower() in ("node", "node.exe") for word in literals):
            found.append(sub)
    return found


def test_every_node_launching_helper_calls_the_hard_guard():
    """任何起 `node` 子进程的函数都必须先过 `require_node()`（不看函数名，看实参）。"""
    guarded: list[str] = []
    unguarded: list[str] = []
    for filename, _ in NODE_DEPENDENT:
        tree = ast.parse((TESTS / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _node_launchers(node):
                continue
            (guarded if "require_node" in _callee_names(node) else unguarded).append(f"{filename}::{node.name}")
    print(f"[GATE-AST] node 子进程支路 {len(guarded)} 条已过守卫：" + ", ".join(guarded))
    assert len(guarded) >= 9, (
        f"只找到 {len(guarded)} 条带守卫的 node 支路（预期 ≥9：对拍 7 + 题库 1 + p0 1），守卫被删了？"
    )
    assert not unguarded, f"这些函数起 node 子进程却没调 require_node()：{unguarded}"


# --- 5/6. 运行时实测（真子进程 pytest）--------------------------------------


def _path_without_node(path: str) -> str:
    """Drop every PATH entry that provides a `node` binary."""

    def provides_node(entry: str) -> bool:
        return any((Path(entry) / name).exists() for name in ("node.exe", "node", "node.cmd", "node.bat"))

    kept = [entry for entry in path.split(os.pathsep) if entry and not provides_node(entry)]
    return os.pathsep.join(kept)


def _run_child(
    targets: list[str], *, node_available: bool, allow_no_node: bool, noconftest: bool = False, k: str | None = None
) -> subprocess.CompletedProcess:
    """Run `targets` in a child pytest, optionally with `node` hidden."""
    env = dict(os.environ)
    env.pop("XH_ALLOW_NO_NODE", None)
    if allow_no_node:
        env["XH_ALLOW_NO_NODE"] = "1"
    if not node_available:
        env["PATH"] = _path_without_node(env.get("PATH", ""))

    # 自验：子进程里的 node 可见性必须和本用例声称的一致，否则下面的正/反向断言
    # 全是空转（"没命中"可能就是尺子本身没瞄准）。用 `which(..., path=...)` 直接解析
    # 将要传给子进程的 PATH，避免为一句自检再多起一个 python。
    visible = shutil.which("node", path=env.get("PATH"))
    assert bool(visible) is node_available, (
        f"子进程 node 可见性自验失败：期望 {'可见' if node_available else '不可见'}，实际 {visible!r}"
    )

    args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if noconftest:
        args.append("--noconftest")
    args += targets
    if k:
        args += ["-k", k]
    return subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)


def _parity_subset(**kwargs) -> subprocess.CompletedProcess:
    return _run_child(["tests/test_cross_engine.py"], k=PARITY_SUBSET, **kwargs)


def test_parity_cases_execute_instead_of_skipping_when_node_is_available():
    """node 可用时，对拍必须真的跑（通过 > 0 且跳过 = 0），不是收集了就完事。"""
    if shutil.which("node") is None:
        pytest.skip("本机无 node：本断言由 test_gate_goes_red_when_node_is_missing 覆盖")

    completed = _parity_subset(node_available=True, allow_no_node=False)
    out = completed.stdout
    assert completed.returncode == 0, (
        f"对拍子集在 node 可用环境下应全绿，实际 rc={completed.returncode}\n{out}\n{completed.stderr}"
    )
    passed = re.search(r"(\d+) passed", out)
    assert passed and int(passed.group(1)) > 0, f"没有任何用例通过——门禁没跑：\n{out}"
    assert "skipped" not in out, f"node 可用却出现 skip，门禁被弱化：\n{out}"
    summary = GATE_SUMMARY.search(out)
    assert summary, f"conftest 的对拍门禁汇总行缺失（门禁可观测性被破坏）：\n{out}"
    assert summary.group(2) == "0" and summary.group(3) == "0", f"门禁汇总行显示有失败/跳过：{summary.group(0)}"
    print(f"[GATE] node 可用：{passed.group(1)} 条对拍实测通过，门禁汇总行 {summary.group(0)}")


def test_gate_goes_red_when_node_is_missing():
    """node 缺失 = 红。夹具里删掉 node 的 PATH 项，跑真子进程验证。

    两种跑法都要红：普通跑（模块内守卫 + conftest 钩子）与 `--noconftest`（只剩模块内
    守卫）——后者证明这条门禁不依赖某个可能被人删掉的 conftest。
    """
    for noconftest in (False, True):
        completed = _parity_subset(node_available=False, allow_no_node=False, noconftest=noconftest)
        label = "--noconftest" if noconftest else "普通跑"
        out = completed.stdout + completed.stderr
        assert completed.returncode != 0, f"缺 node 时门禁必须红（{label}），实际 rc=0 —— 又静默蒸发了：\n{out}"
        assert re.search(r"\bfailed\b", out), f"{label}：没有失败计数输出：\n{out}"
        assert "XH_ALLOW_NO_NODE=1" in out, f"{label}：失败信息没写明逃生阀用法：\n{out}"
        if noconftest:
            # 只剩模块内守卫：这条失败信息必须来自被守卫的模块自身。
            assert "node 依赖型门禁不可用" in out, (
                f"{label}：模块内的硬失败守卫没生效（失败可能只来自 conftest）：\n{out}"
            )
        else:
            # 普通跑：模块内守卫与 conftest 钩子都会报，任一措辞都可，但必须说清 node 缺失。
            assert "对拍" in out and "node" in out, f"{label}：失败信息没说清是 node 缺失导致门禁不可用：\n{out}"
        print(f"[GATE] 缺 node（{label}）：rc={completed.returncode}，已按失败处理并给出逃生阀说明")


def test_offline_engine_gates_also_go_red_when_node_is_missing():
    """另外两处 node 依赖门禁（离线题库 / p0 黄金值）也必须变红，不许静默 skip。

    这两处没有 conftest 钩子兜底，红色完全来自 `_node_guard.require_node()`——
    所以这条同时验证"共享守卫在三个文件里都真的接上了"。
    """
    completed = _run_child(
        ["tests/test_offline_puzzles.py", "tests/test_p0_rules.py"], node_available=False, allow_no_node=False
    )
    out = completed.stdout + completed.stderr
    assert completed.returncode != 0, f"缺 node 时这两处门禁必须红，实际 rc=0：\n{out}"
    failed = re.search(r"(\d+) failed", out)
    assert failed and int(failed.group(1)) >= 3, f"预期至少 3 条红（题库 2 + p0 1），实际输出：\n{out}"
    assert "node 依赖型门禁不可用" in out, f"失败信息不是来自共享守卫：\n{out}"
    assert "XH_ALLOW_NO_NODE=1" in out, f"失败信息没写明逃生阀用法：\n{out}"
    print(f"[GATE] 缺 node：题库/p0 门禁 {failed.group(1)} 条按失败处理")


def test_escape_valve_skips_visibly_when_explicitly_waived():
    """`XH_ALLOW_NO_NODE=1` 才允许跳过，且跳过必须在输出里看得见。"""
    completed = _parity_subset(node_available=False, allow_no_node=True)
    out = completed.stdout + completed.stderr
    assert completed.returncode == 0, f"放宽后应为绿（全部 skip），实际 rc={completed.returncode}：\n{out}"
    skipped = re.search(r"(\d+) skipped", out)
    assert skipped and int(skipped.group(1)) > 0, f"放宽后应看到 skip 而不是空跑：\n{out}"
    summary = GATE_SUMMARY.search(out)
    assert summary, f"放宽后仍应打印门禁汇总行：\n{out}"
    assert summary.group(1) == "0" and int(summary.group(3)) == int(skipped.group(1)), (
        f"汇总行必须显示「通过 0 / 跳过 {skipped.group(1)}」，实际 {summary.group(0)}"
    )
    assert "已放宽" in out, f"输出里看不出「已放宽」，无法区分通过/未执行：\n{out}"
    print(f"[GATE] 逃生阀生效：{skipped.group(1)} 条标为 skip（= 门禁未执行，非通过）")
