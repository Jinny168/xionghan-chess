# D 批次终验结果整理稿（2026-11-19）

> **口径说明**：本文件是**核验方实跑结果的整理稿**，原始日志与探针产物在核验方工作区，
> 不在本仓库内。下列数字均按核验方实跑记录抄录，未在本仓库重新执行；如需复现，
> 按「复现入口」一节的命令在干净环境单轮串行重跑。

## 1. 结论速览

| 门禁项 | 结果 |
|---|---|
| 全量 pytest（共享树，补 PATH 后有效口径） | **1621 passed / 2 skipped** |
| 全量 pytest（git 不在 PATH 的原始口径） | 1614 passed / 9 skipped（7 条为假跳过） |
| 跨引擎对拍 | **95 通过 / 0 失败 / 0 跳过** |
| ruff | 全绿（All checks passed） |
| mypy（无参） | 25 文件，0 issue |
| S1 / S3 / S5 `--check` | 全绿 |
| RULE_VERSION | 3（未升） |
| 规则 fixtures | 389 局面 / 848 走子 |
| node verifier rules | 23816 着法 / 1237 校验项 |
| node verifier removals | 24 / 24 |
| node verifier position-key | 6 处两态全等 |
| 定向五套件 | 35 passed |

## 2. 全量口径与 7 条假跳过

- **原始口径（git 不在 PATH）**：全量单轮 **1614 passed / 9 skipped**。其中 7 条跳过来自
  `tests/test_baseline_meta.py` 的 `_has_commit()` 调用裸 `git`，git 不在 PATH 时整文件
  静默 skip，属环境假跳过，不是「产物依赖跳过」。
- **有效口径（把 `C:\Program Files\Git\cmd` 加进 `$env:PATH` 后）**：产物依赖三件套
  （`test_baseline_meta.py` / `test_compare_baselines.py` / `test_report_rounding.py`）
  **24 passed**；合并后全量 **1621 passed / 2 skipped**。
- 干净 detached worktree（无本机未入库产物）口径：**1583 passed / 14 skipped**（12 条产物
  依赖跳 + 2 条永久跳），与共享树口径并存，不删。

## 3. 产物与生成链门禁

- **S1 `gen_web_profiles.py --check`**：全绿；`ruleVersion=3`，optionsDigest / profilesHash
  与产物逐字节一致。
- **S3 `build_webapp_bundle.py --check`**：全绿；bundle 与 5 类已跟踪产物同源。
- **S5 `gen_rule_fixtures.py --write` 后 `--check`**：全绿；fixtures 389 局面 / 848 走子，
  两份跨端 fixtures 逐字节一致。
- **node verifier**：rules 23816 着法 / 1237 校验项；removals 24/24；position-key 6 处
  两态全等。

## 4. 锚定反证（修3 历史基线指纹）

- 反证流程：临时把 n=64 基线 sidecar 的 beginner 配置指纹改成当前口径 → 锚定守卫 **EXIT=1**；
  还原后复跑 → **EXIT=0**。
- 锚定指纹：`aiConfigDigest.a = b014d8072e5a7c7d`（0.55 两层串行旧口径），
  `b = 0004d697df110392`（medium）；`anchorCommit=33e8fab`；legacyNote 含
  0.55 / 0.18 / 等价比较说明。历史基线按记录 commit 派生，不随当前 CONFIGS 漂移改写。

## 5. 目检证据

- 12 张证据 PNG 哈希两两互异；`webapp_m2_shadow_soft.png` 为 34,975 B，SHA256 前缀
  `3dda71a0f1f3`（M-2 假证据重拍后样本）。
- 证据目录 `benchmarks/visual_evidence/` 默认不入库；CI 无该目录时证据守卫整组 skip 并写明原因。

## 6. 计时用例抖动定性

- 计时用例 **4 passed / 1.00s**，属降频抖动（跨模块顺序 / Qt 焦点时序），非本轮回归；
  单文件隔离复跑全绿，第三次全量复跑全绿。

## 7. 复现入口

- 跑 pytest 前先把 git 目录加进 PATH，避免 `test_baseline_meta.py` 假跳过：
  ```powershell
  $env:PATH = "C:\Program Files\Git\cmd;$env:PATH"
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- mypy 无参：`.\.venv\Scripts\python.exe -m mypy`
- 生成链顺序：S1 `gen_web_profiles.py --write` → S3 `build_webapp_bundle.py` →
  S4 `--check` → S5 `gen_rule_fixtures.py --write` → S6 verify-rules。

## 8. 不变量复核

- `RULE_VERSION=3` 未升；规则 / 存档 / PGN 零改动；`CONFIGS` medium/hard 字段级零 diff；
  未新增色值、未扩裸色白名单条目；未引入 canvas 像素基线；两条线判据（星轨按题态屏蔽 /
  文字提示按 scored 分流）未合并；playwright 未进任何依赖清单。
