"""Session-wide guard for the cross-engine parity gate.

``tests/test_cross_engine.py`` is the project's ONLY guard against the Python
(``core/rules.py``) and offline (``android/Resources/assets/offline/offline.js``)
rule engines drifting apart. It used to self-skip case by case when ``node`` was
missing (``shutil.which("node") is None``), which meant that on a machine without
node the whole gate silently evaporated while ``pytest`` still reported a green
run.

Two nets now stand between that failure mode and a green build:

1. **In the module** (P0-1 的正修): every node-launching helper calls
   ``_require_node()``, which raises a genuine failure when node is missing; the
   only skip left is the module-level mark gated on ``XH_ALLOW_NO_NODE=1``.
   ``tests/test_gate_integrity.py`` asserts this and runs the red path with
   ``--noconftest`` too, so the guarantee does not depend on this file.
2. **Here** (this conftest): the same condition is also caught at hook level, so
   a future edit that reintroduces a silent skip in the parity module still fails
   the session, and the collected/passed/failed/skipped counts of the parity
   cases are always printed -- a green line can then be told apart from an empty
   one.

Nothing here touches any assertion in ``test_cross_engine.py``; this hook is the
second net, not the first. No marker is registered on the tests themselves (that
would mean editing the parity module); membership is decided by module path.
"""

from __future__ import annotations

import os
import shutil

import pytest

NODE = shutil.which("node")
ALLOW_NO_NODE = os.environ.get("XH_ALLOW_NO_NODE") == "1"
PARITY_MODULE = "test_cross_engine.py"

NO_NODE_MESSAGE = (
    "跨引擎对拍无法运行：未在 PATH 中找到 `node`。\n"
    "`tests/test_cross_engine.py` 是本项目唯一的镜像护栏（Python rules.py ↔ "
    "offline.js）；缺 node 时它不该产出绿色结果（此前是逐条静默 skip，等同于护栏失效），"
    "故这里**默认直接判失败**。\n"
    "  → 请安装 Node.js（>=20）。\n"
    "  → 若确需在无 node 环境运行，设 `XH_ALLOW_NO_NODE=1` 显式放宽（届时对拍用例整模块标为 skip）。"
)

# Collected parity-case count, filled during collection, read at the summary.
_PARITY_TOTAL = 0


def _is_parity(item: pytest.Item) -> bool:
    path = getattr(item, "path", None) or getattr(item, "fspath", "")
    return PARITY_MODULE in str(path)


def pytest_configure(config: pytest.Config) -> None:
    # Greppable intent even though the tests carry no marker themselves.
    config.addinivalue_line(
        "markers", "requires_node: cross-engine parity case that needs a `node` binary"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    global _PARITY_TOTAL
    _PARITY_TOTAL = sum(1 for item in items if _is_parity(item))


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function):
    """Fail the parity module (red) instead of letting it skip to green.

    Runs in the call phase, so the outcome is a genuine FAILURE (not a setup
    error). Any other test, and any run where node is present or explicitly
    waived, returns ``None`` and lets the normal pyfunc call proceed.
    """
    if _is_parity(pyfuncitem) and NODE is None and not ALLOW_NO_NODE:
        pytest.fail(NO_NODE_MESSAGE, pytrace=False)
    return None


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    total = _PARITY_TOTAL
    if not total:
        return
    stats = terminalreporter.stats

    def _count(outcome: str) -> int:
        return sum(1 for rep in stats.get(outcome, [])
                   if PARITY_MODULE in getattr(rep, "nodeid", ""))

    passed, failed = _count("passed"), _count("failed")
    skipped, errored = _count("skipped"), _count("error")

    if NODE is None and not ALLOW_NO_NODE:
        state = "node 缺失 → 对拍门禁已按**失败**处理（设 XH_ALLOW_NO_NODE=1 可放宽）"
    elif NODE is None:
        state = "node 缺失，已放宽（XH_ALLOW_NO_NODE=1）→ 对拍用例跳过"
    else:
        state = f"node 可用（{NODE}）"

    terminalreporter.write_sep(
        "=",
        f"跨引擎对拍门禁：收集 {total} 条 | 通过 {passed} | 失败 {failed} | "
        f"跳过 {skipped} | 报错 {errored} | {state}",
    )
