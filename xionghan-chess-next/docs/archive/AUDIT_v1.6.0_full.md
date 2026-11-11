# 匈汉象棋 v1.6.0 全栈审计复核

## 版本与范围

| 项目 | 结论 |
|---|---|
| 目标版本 | 1.6.0 |
| Android | versionCode 8 / versionName 1.6.0 |
| 历史 2.0.0 | 已废止，跟踪路径为 0 |
| 测试基线 | 125 passed, 1 warning |

## 关键修复

| 风险 | 处理 |
|---|---|
| A-1 / F-1 MCTS 实验态 | master 档接入混合 MCTS、可选训练模型、叶子估值 |
| R-03 广播放大 | WebSocket 广播 compact replay tail，保留完整快照兼容 |
| R-05 明文流量 | Android Release 关闭 cleartext，交付文档要求 HTTPS |
| R-06 i18n | Web 动态文案补齐 locale |
| R-09 pending 状态 | undo 后清理 pending draw/undo/restart 与 pause |

## 残留风险

| 编号 | 等级 | 说明 |
|---|---|---|
| F-1 | P1 | master vs hard 50 局非截断胜率 >=55% 未取得有效证据 |
| F-10 | 待确认 | C-01/03/04/11/12 规则项待产品拍板，本版未修改规则语义 |
| R-08 | P3 | 历史大体积二进制治理仍建议迁移到 Git LFS 或外部发布存储 |

## 上线建议

v1.6.0 可作为工程功能版本交付，但 master 棋力卖点应标注为“实验增强/可选模型推理”，不得宣称已稳定强于 hard。
