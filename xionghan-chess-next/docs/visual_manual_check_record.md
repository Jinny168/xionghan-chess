# 人工目检执行记录（M-1 … M-7）

> 本文件是**待真人逐条打勾**的空模板。自动门禁（`tests/test_visual_alignment_triad.py`）只钉代码片段与数值；
> 渲染结果层（字形、投影、对比、层级）按 TRIAD 第 3 节口径**仅人工验收**，不引入 canvas 像素基线（字体 / DPR / 抗锯齿三处非确定）。
>
> **当前状态：证据已备，判定未做。** 下表结论栏在真人目检前一律保持未勾选；任何人不得代替真人填「通过」。
> 所有离屏渲染 / 截图证据仅为观察材料，判定仍归真人。

## 0. 执行环境（目检时填写）

- 日期：__________
- 目检人：__________
- 桌面端版本 / 构建：__________
- 浏览器与缩放（web / webapp）：__________
- 主题（classic / 其余浅色 / dark）：__________

## 1. 证据清单

证据目录：`benchmarks/visual_evidence/`（离屏渲染产物，默认不入库）。

证据目录：`benchmarks/visual_evidence/`（离屏渲染产物，默认不入库）。

> 下表为**真人目检可勾清单**，每行四列：证据文件名 / 应看什么 / 通过判据 / 结论。
> **结论栏在真人目检前一律留空**，任何人不得代替真人填「通过」；自动门禁只钉代码片段与数值，渲染结果层判定归真人。

### 1.1 桌面端（c5）

| 证据文件名 | 应看什么 | 通过判据 | 结论 |
|---|---|---|---|
| `benchmarks/visual_evidence/c5_m1_glyph_weight.png` | 同一枚子的字高 / 盘径、字重 | 与 webapp 同名图肉眼一致；无「桌面过粗」或「网页字幕感」 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/c5_m2_shadow_soft.png` | 浅色 classic + 盘边棋子 + 200% 下缘裁切的投影 | 投影重心向下、无硬边、不与棋子脱开（VA-05 的 0.55 倍差应能看出） | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/c5_m4_dark_markers.png` | dark 主题下的可走点与可吃点 | 可走点不消失；可吃点不与红叉混淆（深色 0.15 放大补偿的理由） | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/c5_m7_state_layers.png` | 将军 + 选择 + 可走点 + 上一步四态同屏 | 层级仍是「上一步 < 可吃 < 选择 < 将军」；都亮等于都没亮视为不通过 | ☐ 通过　☐ 不通过 |

### 1.2 webapp

| 证据文件名 | 应看什么 | 通过判据 | 结论 |
|---|---|---|---|
| `benchmarks/visual_evidence/webapp_m1_glyph_weight.png` | 同一枚子的字高 / 盘径、字重 | 与桌面同名图肉眼一致；无「网页字幕感」 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/webapp_m2_shadow_soft.png` | 浅色 classic + 盘边棋子 + 200% 下缘裁切的投影 | 投影重心向下、无硬边、不与棋子脱开；与 M-1 全景图形态不同 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/webapp_m4_dark_markers.png` | dark 主题下的可走点与可吃点 | 可走点不消失；可吃点不与红叉混淆 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/webapp_m7_state_layers.png` | 将军 + 选择 + 可走点 + 上一步四态同屏 | 层级「上一步 < 可吃 < 选择 < 将军」；将军标记为会话内临时抬高 `inCheck` 触发，非真实将军局面，真人需以真实将军局复核 | ☐ 通过　☐ 不通过 |

### 1.3 特色棋子徽记（B4/C1，VA-14）

| 证据文件名 | 应看什么 | 通过判据 | 结论 |
|---|---|---|---|
| `benchmarks/visual_evidence/c1_badge_13x13_glyph.png` | 13×13 字形模式徽记 | 射=四角星+细环、尉=双短斜杠、檑=三条短横、巡=空心小方；徽记落在盘缘上方（0.86 r），不压子面字形 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/c1_badge_13x13_image.png` | 13×13 位图模式徽记 | 位图模式叠加在美术图之上；墨色沿用棋子自身 ink，不靠颜色作为唯一区分 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/c1_badge_9x10_glyph.png` | 9×10 字形模式徽记 | 同 13×13 字形口径，小尺寸下徽记仍可辨、不糊成一团 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/c1_badge_9x10_image.png` | 9×10 位图模式徽记 | 同 13×13 位图口径，小尺寸下不压字形 | ☐ 通过　☐ 不通过 |

### 1.4 web 旧树

| 证据文件名 | 应看什么 | 通过判据 | 结论 |
|---|---|---|---|
| `benchmarks/visual_evidence/web_m1_glyph_weight.png` | 13×13 初始局全景：棋子字高 / 盘径比例、字重、河界文字 | 可核：13 行 13 列格线完整；双方棋子在位；棋子圆径 ≈0.78 格；河界显示中文「长城 / 阴山」而非 i18n key。`human-only`：字高 / 字重与桌面、webapp 同名图肉眼一致，无字幕感或过粗 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/web_m2_shadow_soft.png` | classic 浅底、盘边棋子、200% 下缘裁切的投影柔边 | 可核：取景为棋盘下缘一带（非全景）；投影偏移向下、不压相邻棋子；与 M-1 哈希互异（守卫已核）。`human-only`：投影边缘柔化无硬边、不与棋子脱开 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/web_m4_dark_markers.png` | dark 主题（盘底 #2c2c2c）下选中环 / 可走点 / 可吃叉 / 受害环 | 可核：深底上可见 ≥1 枚选中金环、≥1 个可走点、≥1 个落点可吃叉、≥1 个受害环；叉为实心 X、环为空心圆，形态不混；标记与盘底对比度 ≥3:1（图形标记口径）。`human-only`：标记在深底不发虚 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/web_m7_state_layers.png` | 将军环 + 选择环 + 可走点 + 上一步起讫框四态同屏 | 可核：四类标记各 ≥1 处可见；绘制顺序 上一步框 < 可吃 < 选择 < 将军；将军环为会话内临时置 `check=true` 触发，**非真实将军局面**，需以真实将军局复核。`human-only`：四态不糊成一团 | ☐ 通过　☐ 不通过 |

## 2. 逐条执行记录

### M-1 字形与字重

- 判据（TRIAD）：三端各开一局，同一局面截图并排；同一枚子的字高 / 盘径肉眼一致；无「网页字幕感」或「桌面过粗」。
- 桌面证据：`benchmarks/visual_evidence/c5_m1_glyph_weight.png`
- 网页证据：`benchmarks/visual_evidence/webapp_m1_glyph_weight.png`；web 旧树：`benchmarks/visual_evidence/web_m1_glyph_weight.png`
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-2 投影柔边

- 判据（TRIAD）：浅色 classic 主题，棋子摆到盘边（下缘投影落在空处），对棋子下缘放大到 200% 裁切观察；投影重心向下、无硬边、不与棋子脱开（VA-05 的 0.55 倍差应能看出）。
- 桌面证据：`benchmarks/visual_evidence/c5_m2_shadow_soft.png`
- 网页证据：`benchmarks/visual_evidence/webapp_m2_shadow_soft.png`（浅色 classic + 盘边棋子 + 200% 下缘裁切）；web 旧树：`benchmarks/visual_evidence/web_m2_shadow_soft.png`
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-3 盘底色与纸纹

- 判据（TRIAD）：四主题各看一次；无明显「塑料平涂」；暗角不压四角刻线（webapp `drawBoardSurface` 的暗角口径）。
- 桌面证据：本轮未出图，需活体切换四主题目检。
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-4 深色主题标记对比

- 判据（TRIAD）：dark 主题下摆一个可走点和一个可吃点；可走点不消失、可吃点不与红叉混淆（桌面深色单独放大到 0.15 的理由）。
- 桌面证据：`benchmarks/visual_evidence/c5_m4_dark_markers.png`
- 网页证据：`benchmarks/visual_evidence/webapp_m4_dark_markers.png`；web 旧树：`benchmarks/visual_evidence/web_m4_dark_markers.png`
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-5 高 DPI / 小盘缩放

- 判据（TRIAD）：浏览器缩放 50% 与 200%，或窗口拉窄到最小宽度；线宽不发虚、投影比例不失控（专抓 VA-06 的固定 px 缺陷）。
- 证据：本轮未出图，需在真实窗口 / 浏览器缩放比例下目检。
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-6 落子手感

- 判据（TRIAD）：同一手棋在三端各走一次；动画结束时无回弹、无残影；时长差异能被感知但不突兀（当前三端 320ms）。
- 证据：本轮未出图（动画需活体走子），需三端各走同一手目检。
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-7 状态叠加层级

- 判据（TRIAD）：将军 + 选择 + 可走点 + 上一步四态同屏；层级仍是「上一步 < 可吃 < 选择 < 将军」，都亮等于都没亮视为不通过。
- 桌面证据：`benchmarks/visual_evidence/c5_m7_state_layers.png`
- 网页证据：`benchmarks/visual_evidence/webapp_m7_state_layers.png`（web 旧树：`benchmarks/visual_evidence/web_m7_state_layers.png`；两图将军标记均为离屏会话内临时把 `check` 置真触发，非真实将军局面）
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### 特色棋子徽记（B4/C1，VA-14）

- 判据（TRIAD）：射=四角星+细环、尉=双短斜杠、檑=三条短横、巡=空心小方；徽记落在盘缘上方（0.86 r），不压子面字形；墨色沿用棋子自身 ink，不靠颜色作为唯一区分。
- 桌面证据：
  - `benchmarks/visual_evidence/c1_badge_13x13_glyph.png`（13×13 字形模式）
  - `benchmarks/visual_evidence/c1_badge_13x13_image.png`（13×13 位图模式）
  - `benchmarks/visual_evidence/c1_badge_9x10_glyph.png`（9×10 字形模式）
  - `benchmarks/visual_evidence/c1_badge_9x10_image.png`（9×10 位图模式）
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

## 3. 本轮证据缺口与待办

- **webapp 截图已补（D2）**：Playwright 装入 `.venv`（未写入 `requirements.txt` / `pyproject.toml` 等任何依赖清单），`channel="chrome"` 复用本机 Chrome，未下载 Chromium；本地 `http.server` 托管 `webapp/`。已出 M-1 / M-2 / M-4 / M-7 四张 webapp 图。**web 旧树截图仍待补**（卡点见下条）。
- **web 旧树截图（F3/H）已解锁出图**：G 批次在 `web/js/app.js` 末尾加了仅离屏使用的调试桥——只有页面在模块加载前已置 `window.__XH_DEBUG__==='offscreen'`，才挂 `window.__xh={app,draw,resizeBoard,geometry}`，生产路径不启用、不进导出清单。H 脚本 `scripts/capture_web_evidence.py` 复用 `.venv` Playwright 1.65.2、`channel="chrome"` 复用系统 Chrome（未下载 Chromium），`http.server` 只托管 `web/`（不托管 webapp），经离屏桥注入 staging 局面与标记数组，已出 `web_m1/m2/m4/m7_*.png` 四张。历史卡点（模块作用域未暴露、开局强依赖后端、标记只由接口推帧）均由该桥绕开；**注入的是 staging 局面，只核对标记层级与形态，不作规则正确性依据**。
- **M-2 重拍（证据守卫）**：首版 M-2 误与 M-1 全景图逐字节相同，已按「浅色 classic + 盘边棋子 + 200% 下缘裁切」重拍；`tests/test_visual_evidence_guard.py` 只读文件校验证据图哈希两两不同、各图 >20 KB、文件名与本模板索引一致（目录缺失则 skip）。M-1 为全景开局图（看字高 / 盘径 / 字重），与 M-2 裁切图形态不同。
- **M-7 将军标记口径**：webapp 离屏会话内临时把 `rules.inCheck` 置真以触发将军环，非真实将军局面；真人目检时应以真实将军局复核层级。
- M-3、M-5、M-6 依赖活体主题切换 / 窗口缩放 / 动画走子，离屏脚本无法覆盖，列入真人目检步骤。
- 离屏证据为** staging 局面**（手工摆子、个别态由脚本强制），只用于核对标记层级与形态，不作为规则正确性依据。
