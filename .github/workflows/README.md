# CI 使用说明（`.github/workflows/`）

## 这个目录只有一个 workflow

`ci.yml` 里 **4 个 job**，按事件分流：

| 事件 | `lint` | `test` | `gate-negative` | `slow` |
|---|---|---|---|---|
| `push` 到 `master` | ✅ | ✅ | — | — |
| `pull_request` → `master` | ✅ | ✅ | — | — |
| `workflow_dispatch`（手动） | ✅ | ✅ | ✅ | ✅ |
| `schedule`（每周三 18:00 UTC） | — | — | ✅ | ✅ |

判据：**阻断合并的只有 `lint` + `test`**。`slow` 与 `gate-negative` 不进 PR 路径，
所以它们红也不会挡住合并；要用它们当判据时手动触发一次并看 job 结论。

`gate-negative` 是**负向自检**：把 `node` 从 `PATH` 摘掉后跑对拍子集，**期望非零退出**。
它验的不是代码，而是"门禁的报警器还会不会响"——如果哪天有人把对拍改回静默 skip，
这个 job 会绿（因为它期望红），而 `test` 也会绿，只有这一条会红。

> 旧的 `slow.yml` 已合并进 `ci.yml` 的 `slow` job（两个文件都会跑 `-m slow`，
> 手动触发时会重复跑两遍、定时任务也会每周重复一次）。要回退：`git revert` 对应提交。

## 手动触发

```bash
gh workflow run ci.yml --ref master          # 全套（lint + test + slow）
gh workflow run ci.yml -f  # 无入参，本 workflow 不接受参数
gh run watch                                  # 跟进当前这次
```

也可以网页：Actions → CI → Run workflow。

## 本地复现 CI 的两个关键环境变量

```bash
cd xionghan-chess-next
export QT_QPA_PLATFORM=offscreen              # 桌面测试无头运行（CI 里是 job 级 env）
export XDG_CONFIG_HOME=$PWD/.ci-xdg           # 把桌面用例的配置目录挪出 ~/.config
pytest tests/ -m "not slow" -q                # = job `test`
pytest tests/ -m slow -q                      # = job `slow`（20 条，墙钟级）
```

`AI_TIME_SCALE` **不要**在 shell 里全局 export：它是全局时间倍率，会把所有 AI 用例的
预算一起改掉，让"到底是慢还是错"无法区分。要放大预算请在用例内 `monkeypatch.setenv`。

## 排查手册：CI 红、本地绿时先做这一件事

**不要立刻判 flaky，先把命令粒度缩小到单用例/单参数重跑一次。**

本项目实测过两次"整跑绿、单跑红"（或反过来）都是**预算/负载敏感**，不是随机：
`test_ai.py` 的 `test_every_difficulty_prefers_a_clean_material_capture[beginner]`
在同一台机器上整跑 5 轮有 2 轮红，但只跑那一个参数时 **100% 红**。

```bash
# 1. 先缩到单参数（pytest 的 nodeid 支持 [param] 后缀）
pytest "tests/test_ai.py::test_every_difficulty_prefers_a_clean_material_capture[beginner]" -q
# 2. 再放大到整文件，看是否只在特定顺序下出现
pytest tests/test_ai.py -q -m "not slow"
# 3. 最后整跑，确认是"顺序污染"还是"负载敏感"
pytest tests/ -m "not slow" -q
```

两类根因的判断口径（本项目都真实发生过）：

| 现象 | 判据 | 归因 |
|---|---|---|
| 单跑红、整跑绿（或反之）且缩到单用例后稳定 | 用例自身对墙钟/顺序有隐含依赖 | 用例缺陷，必须改用例（抬预算/注入时钟/隔离事件队列），**不要加重试** |
| 缩到单用例仍随机 | 真的非确定性 | 才可考虑 flaky 标记，且要在注释里写清观测到的比例 |

`--durations=N` 的输出是判断"是不是被某个昂贵用例挤到"的第一手材料：
`test` job 已固定带 `--durations=15`。

## 前置条件（`test` job 会硬性检查）

1. **node ≥ 22.7**。`web/js/app.js` 是 ESM，而 `.js` 在 node 20 及更早默认按 CommonJS
   解析，`node --check` 会直接报 `Cannot use import statement outside a module`。
   CI 用 `actions/setup-node` 钉 `22`，不要按 `package.json` 的 `engines: ">=20"` 往下调。
2. **Git LFS 对象**。`web/assets/pieces/**`、`desktop/resources/sounds/**`、
   `avatars/`、`backgrounds/` 都在 LFS 里；没有对象时它们是 ~130 字节的指针文本，
   Qt/Pillow/wave 都解不开。本地缺对象时先 `git lfs pull`。
3. **Pillow**。`requirements/dev.txt` 未声明它，而 `test_desktop_pieces_assets` 里
   4 条资产门禁靠它；缺它时用例走 `importorskip` **静默跳过**，门禁等于不存在。
   `test` job 会显式补装。

## 「空绿」是怎么被拦住的（三层，缺一层就漏）

跨引擎对拍 81 条全部 skip 时，`pytest` 的退出码仍是 **0**。所以"pytest 绿"本身不能证明
对拍跑过。当前有三层，最后一层在 pytest 之外：

| 层 | 位置 | 拦什么 |
|---|---|---|
| 1 | `tests/test_cross_engine.py::_require_node()` | 缺 node 时逐条硬失败（`--noconftest` 也生效） |
| 2 | `tests/conftest.py` 的会话钩子 | 同条件的第二道，并打印「收集/通过/跳过」计数 |
| 3 | `ci.yml` 的 `对拍门禁汇总行断言` step | **消费**那行计数：断言 `跳过==0` 且 `通过==收集` |

第 3 层是必须的：前两层只保证"会红"，但如果有人显式放宽（`XH_ALLOW_NO_NODE=1`）或给对拍
加了 `-k` 白名单，pytest 依然 rc=0，只有第 3 层会红。`gate-negative` job 则反过来验
第 1/2 层在 runner 上真的会红。

## 门禁口径的唯一来源

不要在本目录的 YAML 里重新定义 pytest 参数。标记与 `pythonpath` 都来自
`xionghan-chess-next/pyproject.toml` 的 `[tool.pytest.ini_options]`：

- 主门禁 `pytest tests/ -m "not slow"`
- 全量 `pytest tests/ -m slow`
- `--strict-markers` 已开（写错的 marker 是错误，不是静默 no-op）
