# 全量门禁结果 · 2026-11-23

> 入库说明：本文件把此前只存在于 `.workbuddy/memory/2026-11-23.md:111` 的全量门禁结果固化为仓库内可核对文件（对应 `docs/ARCH_GAP_2026-11-25.md` §6 T2）。**本文件不重新执行测试**，只誊录已实测数字并标注出处、日期口径与环境。
> 复核人：**柯桥良 · 2026-11-23**。

---

## 1. 测量口径

| 项 | 内容 |
|---|---|
| 门禁 HEAD | `356789aa3ffd3469445fa125674bf22e5935addd`（短 `356789a`，2026-11-23 `refactor(test): 网页兵开关守卫改读 core 共享分组`，批次收口HEAD） |
| 完整命令 | `python -m pytest tests/ -q --color=no -p no:cacheprovider` |
| 执行位置 | 仓库子目录 `xionghan-chess-next`；`pyproject.toml:74-83` 定义 `testpaths=tests`；**不加** `-m "not slow"`，即全量口径 |
| 版本基线 | 2.2.2 · `RULE_VERSION=3` · 规则语义零改动 |
| 唯一原始出处 | `.workbuddy/memory/2026-11-23.md:111`（memory 非提交范围，故入库固化） |

## 2. 原始结果行

2026-11-23 memory 原文（`:111-112`）：

> **最终门禁**：全量 `1825 passed, 3 skipped, 0 failed`；跨引擎对拍 95/95；
> `bundle --check` / `verify-rules.mjs` 1237 校验项全绿；ruff / mypy 无参全绿。

2026-11-25 独立复核的完整输出行（`docs/ARCH_GAP_2026-11-25.md` §7，同一组计数、补上耗时与 warning）：

> 执行结果（2026-11-25 本机实测）：**`1825 passed, 3 skipped, 1 warning in 621.45s (0:10:21)`**，退出码 0，与调度方前提及 `.workbuddy/memory/2026-11-23.md:111` 的 `1825 passed, 3 skipped, 0 failed` 完全一致（"1 warning"为 Starlette 的 httpx 弃用提示，非失败）。

- 主结果：**`1825 passed, 3 skipped, 1 warning in 621.45s (0:10:21)`，`EXIT=0`**。
- `"1 warning"` 是 Starlette 的 httpx 弃用提示，不是失败项；`0 failed` 与 2026-11-23 原始记载一致。

## 3. 环境

| 项 | 实测值 | 出处 |
|---|---|---|
| Python | **3.12.3** | 本机 `./.venv/Scripts/python.exe --version` |
| PySide6 / Qt | **6.12.0** | 本机 `PySide6.__version__`；`docs/ARCH_GAP_2026-11-25.md:196` |
| git 根 | `C:/Users/27415/PycharmProjects/xionghan-chess`（项目目录为其子目录 `xionghan-chess-next`） | `docs/ARCH_GAP_2026-11-25.md:197` |
| 测试规模 | `test_*.py` 182 / `*.py` 186 | `docs/ARCH_GAP_2026-11-25.md:193` |

## 4. 跨引擎对拍汇总行

> 跨引擎对拍 **95/95**（`.workbuddy/memory/2026-11-23.md:111`；`docs/ARCH_GAP_2026-11-25.md:26`）。

## 5. 3 个 skip 的逐个原因

| # | 用例 | 原因（源码内 skip 原文） |
|---|---|---|
| 1 | `tests/test_deploy_version.py:68` | `pytest.skip("线上核对需显式开启：XIONGHAN_VERIFY_DEPLOY=1")` —— 需显式设置环境变量才执行线上核对 |
| 2 | `tests/test_generated_puzzles.py:225` | `pytest.skip("当前无 7 ply 题，G4 7ply 分支为未来 mate7 保护（本轮无题可选）")` —— 题库当前无 7ply 题 |
| 3 | `tests/test_desktop_piece_render.py:166` | `pytest.skip("刺已从 PieceType 移除（a3dc236），缺美术仍能画墨的场景不再存在")` —— 「刺」已移除，场景不再存在 |

## 6. 日志尾部 `SystemExit: 1` 的性质

日志尾部的 `SystemExit: 1` 来自沙箱在 pytest **结束后**清理 `pytest-of-*` 临时目录的 `atexit` 钩子，**发生在汇总行之后**，不影响测试结果；不得据此判定门禁失败（见 `docs/ARCH_GAP_2026-11-25.md:187`）。

## 7. 日期口径说明（避免误读）

- **2026-11-23**（本文件名与复核人署名）：批次收口门禁，HEAD `356789a`，原始记载 `1825 passed, 3 skipped, 0 failed` + 对拍 95/95。
- **2026-11-25**：柯桥良在 `ARCH_GAP_2026-11-25.md` §7 独立复核，输出含耗时与 warning 的完整行 `1825 passed, 3 skipped, 1 warning in 621.45s (0:10:21)`；计数与 2026-11-23 一致，多出的 `1 warning` 为弃用提示、非失败。
- 两份记录**不是矛盾或两次不同结论**，同一组 `1825/3/95-95` 的两次记载；本文件同时保留，便于后来者核对，不必翻 memory。
