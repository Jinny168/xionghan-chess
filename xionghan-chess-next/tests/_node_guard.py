"""node 依赖型门禁的**唯一**守卫（三个测试文件共用，勿再复制第二份）。

## 为什么要有这个文件

`test_cross_engine.py`（Python `core/rules.py` ↔ `offline.js` 镜像对拍）、
`test_offline_puzzles.py`（离线题库 ↔ 离线引擎）、`test_p0_rules.py`（黄金值经
`offline_rules_probe.cjs` 复核）三处都要起 `node` 子进程。它们原先各自写了一份

    if not shutil.which("node"):
        pytest.skip("Node.js is required ...")

于是没有 node 的机器上这批用例**整体静默跳过、pytest 仍报绿**——门禁保护力度为零
（docs/AUDIT_TESTABILITY_1.7.0.md §5 表格 / §6 P0-1，跨两个版本未修）。

三份重复守卫本身就是隐患（改一处忘两处 = 新的隐性同步点），所以统一收到这里：

- `require_node()`：缺 node 一律**硬失败**，失败信息说清原因 + 逃生阀用法；
- `module_skip_mark()`：**唯一**允许跳过的地方，只在显式 `XH_ALLOW_NO_NODE=1` 时
  返回一个整模块 skip 标记，让"门禁未执行"在输出里看得见（≠ 通过）。

## 与 `tests/conftest.py` 的分工（两道网，故意不互相 import）

- **第一道（模块内）**：本文件。红色写在用例自己身上，`--noconftest`、把文件拷到
  `tests/` 之外也照样红。
- **第二道（会话级）**：`conftest.py` 按模块路径拦一道钩子。它故意不 import 本文件：
  conftest 在收集期最早被加载，此时 `tests/` 未必已在 `sys.path` 上，为了共用几十行
  文案去动导入顺序不值得。两处文案独立，语义相同。
"""

from __future__ import annotations

import os
import shutil

import pytest

NODE = shutil.which("node")
ALLOW_NO_NODE = os.environ.get("XH_ALLOW_NO_NODE") == "1"

NO_NODE_REASON = (
    "node 依赖型门禁不可用：PATH 里找不到 `node` 可执行文件。\n"
    "本用例要起 node 子进程去比对 Python 规则引擎与离线引擎（offline.js / 题库 / "
    "rules probe）；缺 node 时**不允许退化成 skip** —— 那会让整批对拍静默不执行，"
    "而 pytest 仍报绿（P0-1，docs/AUDIT_TESTABILITY_1.7.0.md §5/§6）。\n"
    "  → 装 Node.js（>=20，`node --version` 能跑即可）后重跑。\n"
    "  → 临时环境确实装不了 node：设 `XH_ALLOW_NO_NODE=1` 显式放宽——届时这批用例整"
    "模块标为 skip，且必须当作「门禁未执行」，不得作为规则一致性已通过的证据。\n"
    "  → CI 里**不要**设这个变量（设了就等于让本 bug 从 env 侧复活）。"
)


def require_node() -> None:
    """缺 node 时硬失败，绝不回落到 skip。

    每个要起 `node` 子进程的 helper 都在最前面调它。
    """
    if NODE is not None:
        return
    # 走到这里说明 XH_ALLOW_NO_NODE 没设（放宽的情形已由 module_skip_mark 整体 skip）。
    pytest.fail(NO_NODE_REASON, pytrace=False)


def module_skip_mark() -> pytest.MarkDecorator | None:
    """整模块跳过标记：**唯一**的 skip 入口，只在显式放宽且 node 缺失时非 None。"""
    if NODE is None and ALLOW_NO_NODE:
        return pytest.mark.skip(reason=NO_NODE_REASON)
    return None
