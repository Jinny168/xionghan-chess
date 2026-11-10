# 匈汉象棋 v1.6.0 QA 测试报告

## 自动化结果

| 项目 | 命令 | 结果 |
|---|---|---|
| Python 全量测试 | `./.venv/Scripts/python.exe -m pytest -q --durations=10` | 125 passed, 1 warning |
| Python 编译 | `./.venv/Scripts/python.exe -m compileall -q src tests scripts` | 通过 |
| Web JS | `node --check web/js/app.js && node --check web/js/i18n.js` | 通过 |
| Android 离线 JS | `node --check android/Resources/assets/offline/offline.js && node --check android/Resources/assets/offline/offline-locales.js` | 通过 |
| JSON | `locales/*.json` 与 `src/xionghan_chess/core/data/*.json` | 通过 |
| 版本扫描 | `rg "2\\.0\\.[0-9]\|1\\.5\\.0\|1\\.4\\.0" locales src web android deploy packaging pyproject.toml package.json tests` | 源码生产路径无旧版本 |
| 2.0.0 跟踪 | `git ls-files \| Select-String '2\\.0\\.0'` | 0 |

唯一警告为既有 `StarletteDeprecationWarning`，不影响本版功能验收。

## 高风险专项

| 风险 | 覆盖 | 实测 | 判定 |
|---|---|---|---|
| Android 离线 vs Python Core | 四配置初始局面、确定性走棋局面、14 类棋子局面合法着集合与将军状态 | `tests/test_cross_engine.py` 19 项通过 | 通过 |
| master 棋力真实性 | 50 局 2 ply 筛查、50 局 80 ply 长筛查尝试 | 2 ply 胜率无效；80 ply 未在交付窗口完成 | 未通过正式胜率证据 |
| 训练流水线 | 自博弈样本、JSONL、NumPy 训练、NPZ 保存、可选推理加载 | `tests/test_training_pipeline.py` 通过 | 通过 |
| 广播放大 | compact replay tail 元数据与完整快照兼容 | `test_compact_snapshot_keeps_replay_tail_metadata` 通过 | 通过 |
| Android cleartext | manifest 回归守卫 | `test_android_release_manifest_disables_cleartext_traffic` 通过 | 通过 |

## 缺陷与回归

| 编号 | 等级 | 路径 | 处理 | 回归 |
|---|---|---|---|---|
| F-1 | P0 | `src/xionghan_chess/core/ai.py`, `src/xionghan_chess/core/mcts.py` | master 接入混合 MCTS 与可选模型推理 | 功能通过，正式胜率证据未通过 |
| F-3 | P1 | `tests/test_cross_engine.py`, `scripts/offline_rules_probe.cjs` | 扩展离线/在线规则等价性 | 通过 |
| F-4 | P1 | `src/xionghan_chess/service/rooms.py`, `web/js/app.js`, `src/xionghan_chess/desktop/app.py` | WebSocket 广播 compact replay | 通过 |
| F-5 | P1 | `android/AndroidManifest.xml` | 关闭 cleartext | 通过 |
| F-7 | P2 | `web/js/app.js`, `locales/*.json` | 动态文案走 i18n | 通过 |
| F-9 | P3 | `src/xionghan_chess/core/game.py` | undo 清理 pending 状态 | 通过 |
| F-10 | 待确认 | 规则语义 | 仅补一致性测试，未改规则 | 待产品确认 |

## 结论

自动化、跨引擎、训练流水线、安全与广播优化均达到 v1.6.0 工程交付条件。master 档 50 局非截断胜率 >=55% 缺少有效证据，发布时必须作为已知风险披露，不能作为已验收卖点宣传。
