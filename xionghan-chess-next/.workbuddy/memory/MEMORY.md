# 匈汉象棋 · 项目长期记忆（2026-11-11 收口）

> 本文件是跨会话的策展记忆，只放长期有效的结论与纪律。逐日过程见同目录 `2026-*.md`，30 天前的日志已移入 `archive/`。

## 一、仓库与环境

- git 根在上级 `xionghan-chess/`；远端 SSH `git@github.com:Jinny168/xionghan-chess.git`；主分支 `master`，同时推 `main`（两次 `git ls-remote` 核验两端同 SHA）。
- `git ls-remote` 会被全局 `remote.origin.uploadpack=true` 打断 → 用 `GIT_CONFIG_GLOBAL=$TEMP/xh-gitconfig`（含 `core.sshCommand` 与 `user.*`）。push 本身走 SSH 正常。
- `mypy` 必须**无参**跑（`mypy src` 会带出 217 个 PySide6 类型噪音）；`npm` 走 `node .../npm-cli.js`；不要从 Bash 调 PowerShell（安全策略会拦）。
- 后台 python 会被降频；长标定用 `--resume` 分批、**恒定 `--n`**（`total_games` 决定 `book_index`，递增会破坏开局取样等价）。
- **2 个 python PID ≠ 并发**：`.venv/Scripts/python.exe` 是 launcher，会拉起 `C:\Python312\python.exe` 作子进程并原样传参。判定要看 `ParentProcessId`、CPU 时间、`sys._base_executable`，不能只数进程名或比命令行。

## 二、数据纪律（踩过的坑）

1. 引用胜率 / 配置前**先核 checkpoint 文件与样本量**；没核到手上的数只写方向、不写幅度。
2. 等价 / 差异判断**逐手或逐项比对**，不用聚合比分（root3 与 root5 同为 2–7–1，但逐手路径不同）。
3. 一次采样不写定律；结论必须带样本量 + CI + 覆盖面。n=10 的曲线只能写趋势。
4. **脚本门禁标记 ≠ 设计契约**：K4 验收读 `contractPass`，不读 `pass`；`pass=true` 只代表档位可分。
5. `--config-a/b` 只注入实例 config、**不改 `CONFIGS`**；扫候选与改全局必须分开。
6. **跨成员转述必须贴原文块，禁止重写数字 / 符号**（2026-11-09 曾把 536 行重写成 69 行，误伤成员并污染结论）。
7. 「上次全量全绿」不能当当前基线，先跑再下结论；共享工作树每个小单元做完即 commit，不留未提交在途改动。

## 三、架构契约

- 三端共享 Python 核心：桌面 PySide6 / Web（服务端算棋，`web/` 无独立规则引擎）/ Android WebView。
- 对外三档 `beginner / medium / hard`；旧名 `easy→beginner`、`expert→hard`、`master→hard` 是**同一对象别名**，不是数值副本。
- `CONFIGS`（`src/xionghan_chess/core/ai.py`）是唯一来源；`PRODUCT_TIERS` 从它派生，`tests/test_level_targets_product.py` 逐字段钉死。
- `depth` 是迭代加深上限；S4 后真实可达 1/2/3（实测完成深度 A 1.000 / B 1.999）。
- 看门狗 = `PREFIX_MAX(0.78) + cap × 1.15` → 3.08 / 6.53 / 14.58s；**与 cap 改动必须同 commit**。
- `wallClean` 在 product 只记录、在 target 才是硬门；硬门是零深度 + nodes≤2% + K2 三条。
- 零深度 = `completed_depth == 0`；`_root` 对 wall 超时保留已完成根着法，nodes/cancel 仍整层作废。
- MCTS 已从产品链路下线，只剩 `benchmark_match(a_simulations=...)` 显式入口。

## 四、S4 标定终局（2026-11-11）

- root16：`13-50-1`；root18（唯一一次预登记调整，仅注入、未进 `CONFIGS`）：`12-49-3`。**两轮 score 都是 13.5，A 得分率均 0.2109**，Wilson `[0.1289, 0.3258]`，Elo −229.2。
- ⇒ K4 出带是**结构性**的（d1→d2 的质变），不是选错 `root_limit`；两轮都 `contractPass=false`、`contractFailedGates=["band: 0.7891 > 0.75"]`；按预登记不再调参、不扩 n。
- 认证 10pt 宽的设计带需 n≈320（约 10 小时机时），明确不做；**K4 结论是「不可认证」**，不是「已验证失败」。
- 产品定稿 **root16**（唯一有完整无污染 n=64 数据，且 K1/K2/K3 都在该配置下验过）。
- K5（新手前 3 局合计 35–50%、第 5 局起 ≥55%，人工试玩 3–5 人 × 各 5 局）**未测**；出结果前不得宣称「入门档已验收」。

## 五、协作纪律

- 主理人只做编排 / 仲裁 / 汇编，**不代写专业产出**；迭代需求同样要调度，不因「改动小」自己动手。
- 大分叉合并：**取远端树 + 重放本地增量**，比 `-X theirs` 自动合并可靠。
- 动 `docs/` 前先备份；曾 `git rm -r docs` 误删整个目录（已用 `git checkout HEAD -- docs/` 还原）。
