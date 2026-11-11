# 文档索引

> 索引本身不是权威内容，只负责指路。**archive 组为历史快照，只读不改，不代表当前实现。**
> 最后核对日期：2026-11-11，对应 HEAD `4d88879`。

## current · 维护中（可更新）

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构与功能说明（含三档 AI、WASM 结论、离线数据 codegen） | ✅ 维护中 |
| [AI_TIERS.md](AI_TIERS.md) | 三档参数、S4 重标定、K1–K5 契约、标定纪律（v2 判定） | ✅ 维护中 |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | 已知问题与未完成实测登记 | ✅ 维护中 |
| [WASM_DECISION.md](WASM_DECISION.md) | WASM 可行性结论、证据与重开条件 | ✅ 维护中 |
| [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) | 对标基准与改进计划（S1–S5 路线图载体） | ✅ 维护中 |
| [PUZZLE_LIBRARY.md](PUZZLE_LIBRARY.md) | 题库清单（自动生成，勿手改） | ✅ 维护中 |
| [AUDIT_1.7.5_full.md](AUDIT_1.7.5_full.md) | v1.7.5 全面审计（最近一次，含 S1–S5 执行记录） | 参考 |

## rules · 规则与棋型

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [PIECE_RULES.md](PIECE_RULES.md) | 棋子行棋规则 | ✅ 权威 |
| [GAME_MODES.md](GAME_MODES.md) | 三种对弈模式的定义、实现对照与验收清单 | ✅ 权威 |
| [RULES.md](RULES.md) | 规则基线 | ✅ 权威 |

## release · 发布与运行

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [release/RUN.md](release/RUN.md) | 运行与部署 | ✅ 权威 |
| [LINUX_DEPLOY.md](LINUX_DEPLOY.md) | Linux 服务器部署 | ✅ 权威 |
| [ANDROID.md](ANDROID.md) | Android 客户端 | ✅ 权威 |
| [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) | WebSocket 协议契约（现行，随服务端实现更新） | ✅ 权威 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 常见问题 | ✅ 权威 |
| [CHANGELOG_1.8.2.md](CHANGELOG_1.8.2.md) | 最近一份更新日志（注意：当前 `__version__` 为 2.0.0，2.0.0 的 changelog 尚缺） | ✅ 当前 |

## ui · 界面与体验

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [UI_AUDIT_2026-10-31.md](UI_AUDIT_2026-10-31.md) | 匈汉象棋 UI 系统审计（2026-10-31） | 参考 |
| [UI_GEOMETRY_AUDIT_2026-10-31.md](UI_GEOMETRY_AUDIT_2026-10-31.md) | 匈汉象棋 桌面端运行期几何审计（2026-10-31） | 参考 |

## ops · 运维与本地环境

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [RUN_LOCAL_PLAN.md](RUN_LOCAL_PLAN.md) | 本机可玩交付计划：桌面版 + 网页版 | 参考 |

## materials · 对外材料（非产品文档，见 [materials/](materials/)）

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [materials/WEBAPP_1024.md](materials/WEBAPP_1024.md) | WorkBuddy「1024 造物挑战」投稿材料 | 对外材料 |
| [materials/XHS_POST.md](materials/XHS_POST.md) | 小红书发布文案（1024 参赛作品） | 对外材料 |

> 注：`materials/HY4_SUBMISSION_KIT.md` / `materials/HY4_CONVERSATION_RECORD.md` 及其引用的 `contest-record/`、`xhs/` 素材**尚未纳入版本控制**；本索引只索引已入库文件，避免新克隆出现死链。入库后再补。<br>
> `RETRO_S4_2026-11-11.md`（S4 复盘）同样是未跟踪文件，未列入索引。

## archive · 历史快照（已归档，只读不改）

> 这些文件已移入 [`archive/`](archive/)，**只对当时版本有效**。归档理由与合并建议见 [archive/README.md](archive/README.md)。

| 文件 | 用途 | 是否权威 |
|---|---|---|
| [archive/AI_FIXES.md](archive/AI_FIXES.md) | AI Bug 修复清单 | ❌ 历史快照 |
| [archive/AI_v1.3.0.md](archive/AI_v1.3.0.md) | 匈汉象棋 AI 引擎优化 v1.3.0（方案 + 实施 + 审计） | ❌ 历史快照 |
| [archive/AUDIT_1.6.0_full.md](archive/AUDIT_1.6.0_full.md) | 匈汉象棋 v1.6.0 全面审计报告 | ❌ 历史快照 |
| [archive/AUDIT_CODE_2026-10-31.md](archive/AUDIT_CODE_2026-10-31.md) | 代码审计 2026-10-31（结构 / 内存 / 并发三章） | ❌ 历史快照 |
| [archive/AUDIT_DESKTOP_1.7.0.md](archive/AUDIT_DESKTOP_1.7.0.md) | 匈汉象棋 v1.7.0 桌面版架构与工程审计报告 | ❌ 历史快照 |
| [archive/AUDIT_STRUCTURE_1.7.0.md](archive/AUDIT_STRUCTURE_1.7.0.md) | 匈汉象棋 v1.7.0 结构审计报告（目录 / 命名 / 依赖 / 职责） | ❌ 历史快照 |
| [archive/AUDIT_TESTABILITY_1.7.0.md](archive/AUDIT_TESTABILITY_1.7.0.md) | 可验证性审计报告（v1.7.0） | ❌ 历史快照 |
| [archive/AUDIT_v1.3.0_analysis.md](archive/AUDIT_v1.3.0_analysis.md) | 匈汉象棋 v1.3.0 全栈审计与安卓重构方案 | ❌ 历史快照 |
| [archive/AUDIT_v1.3.0_post_review.md](archive/AUDIT_v1.3.0_post_review.md) | 匈汉象棋 v1.3.0 优化成果审查报告 | ❌ 历史快照 |
| [archive/AUDIT_v1.4.0_full.md](archive/AUDIT_v1.4.0_full.md) | 匈汉象棋 v1.4.0 全栈工程审计与交付报告 | ❌ 历史快照 |
| [archive/AUDIT_v1.6.0_full.md](archive/AUDIT_v1.6.0_full.md) | 匈汉象棋 v1.6.0 全栈审计复核（摘要） | ❌ 历史快照 |
| [archive/AUDIT_v1.6.0_reaudit.md](archive/AUDIT_v1.6.0_reaudit.md) | 匈汉象棋 v1.6.0 复审审计报告 | ❌ 历史快照 |
| [archive/CHANGELOG_1.5.0.md](archive/CHANGELOG_1.5.0.md) | 匈汉象棋 v1.5.0 更新日志 | ❌ 历史快照 |
| [archive/CHANGELOG_1.6.0.md](archive/CHANGELOG_1.6.0.md) | 匈汉象棋 v1.6.0 更新日志（已收尾） | ❌ 历史快照 |
| [archive/CHANGELOG_1.7.0.md](archive/CHANGELOG_1.7.0.md) | 匈汉象棋 v1.7.0 更新日志 | ❌ 历史快照 |
| [archive/CHANGELOG_1.8.0.md](archive/CHANGELOG_1.8.0.md) | 匈汉象棋 v1.8.0 更新日志 | ❌ 历史快照 |
| [archive/CHANGELOG_1.8.1.md](archive/CHANGELOG_1.8.1.md) | 匈汉象棋 v1.8.1 更新日志 | ❌ 历史快照 |
| [archive/DELIVERY_1.4.0.md](archive/DELIVERY_1.4.0.md) | 匈汉象棋 v1.4.0 交付说明 | ❌ 历史快照 |
| [archive/DELIVERY_1.5.0.md](archive/DELIVERY_1.5.0.md) | 匈汉象棋 v1.5.0 交付说明 | ❌ 历史快照 |
| [archive/DELIVERY_1.6.0.md](archive/DELIVERY_1.6.0.md) | 匈汉象棋 v1.6.0 交付说明 | ❌ 历史快照 |
| [archive/DELIVERY_AI_2026-10-30.md](archive/DELIVERY_AI_2026-10-30.md) | AI 对战体验：本轮交付与结论（2026-10-30） | ❌ 历史快照 |
| [archive/DESIGN_PIECE_MARKERS.md](archive/DESIGN_PIECE_MARKERS.md) | 特色子识别标记 · 设计规格 | ❌ 历史快照 |
| [archive/DESKTOP_ITERATION_PLAN_1.7.0.md](archive/DESKTOP_ITERATION_PLAN_1.7.0.md) | 桌面版全面回顾 + 迭代升级计划 | ❌ 历史快照 |
| [archive/DESKTOP_LEGACY_REFERENCE.md](archive/DESKTOP_LEGACY_REFERENCE.md) | 原版 Desktop 功能参考与迁移状态 | ❌ 历史快照 |
| [archive/DOCS_PLAN_2026-10-31.md](archive/DOCS_PLAN_2026-10-31.md) | 文档盘点与归并方案（2026-10-31，已被本索引取代） | ❌ 历史快照 |
| [archive/GAP_ANALYSIS_vs_legacy.md](archive/GAP_ANALYSIS_vs_legacy.md) | 新旧版本功能差异审计：缺失功能清单与补全方案 | ❌ 历史快照 |
| [archive/i18n-language-switch.md](archive/i18n-language-switch.md) | 匈汉象棋 · 中英文切换（i18n）功能规划与 AI 提示词 | ❌ 历史快照 |
| [archive/PROMPT_1.6.0_delivery.md](archive/PROMPT_1.6.0_delivery.md) | AI 提示词：匈汉象棋 v1.6.0 全流程测试 + 版本交付 | ❌ 历史快照 |
| [archive/QA_PIECE_ATLAS.md](archive/QA_PIECE_ATLAS.md) | 棋子图谱 / 三风格棋子美术 · 验收用例 | ❌ 历史快照 |
| [archive/QA_REPORT_1.4.0.md](archive/QA_REPORT_1.4.0.md) | v1.4.0 QA 报告 | ❌ 历史快照 |
| [archive/QA_REPORT_1.5.0.md](archive/QA_REPORT_1.5.0.md) | v1.5.0 QA 报告 | ❌ 历史快照 |
| [archive/QA_REPORT_1.6.0.md](archive/QA_REPORT_1.6.0.md) | 匈汉象棋 v1.6.0 QA 测试报告 | ❌ 历史快照 |
| [archive/QA_v1.3.0.md](archive/QA_v1.3.0.md) | 匈汉象棋 v1.3.0 质量保障与交付总览 | ❌ 历史快照 |
| [archive/RELEASE_NOTES_1.1.0.md](archive/RELEASE_NOTES_1.1.0.md) | 匈汉象棋 1.1.0 Release Notes | ❌ 历史快照 |
| [archive/TRAINING_1.6.0.md](archive/TRAINING_1.6.0.md) | v1.6.0 MCTS 自博弈与神经网络训练 | ❌ 历史快照 |
| [archive/UNIFIED_UI_OPTIMIZATION_1.1.md](archive/UNIFIED_UI_OPTIMIZATION_1.1.md) | 匈汉象棋三端统一 UI 与功能优化方案（1.1.0） | ❌ 历史快照 |
| [archive/VERSION_PLAN_1.6.0.md](archive/VERSION_PLAN_1.6.0.md) | 匈汉象棋 v1.6.0 版本规划方案 | ❌ 历史快照 |
| [archive/AI_BENCHMARK_1.6.0_screening.json](archive/AI_BENCHMARK_1.6.0_screening.json) | v1.6.0 AI 基准筛选数据 | ❌ 历史快照 |
| [archive/AI_BENCHMARK_1.6.0_smoke.json](archive/AI_BENCHMARK_1.6.0_smoke.json) | v1.6.0 AI 基准冒烟数据 | ❌ 历史快照 |
