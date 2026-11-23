# 人工目检执行记录（M-1 … M-7）

> ## 状态：已废弃（2026-11-23 用户裁定）
>
> **真人目检作为视觉验收手段已取消。** 本文件与 `benchmarks/visual_evidence/` 的 20 张 PNG 保留存档，
> 不再执行勾选、不再填写结论栏。视觉层继续由自动门禁
> （`tests/test_visual_alignment_triad.py` + `docs/visual_alignment_ledger.json`）守卫；
> **渲染结果层不再有人工验收结论**，报告时不得写成「目检通过」或「三端观感已人工确认」。
>
> 同批裁定废弃的还有 K5 人工试玩（`docs/K5_PLAYTEST_RECORD.md`）。
>
> ---

> 本文件是**待真人逐条打勾**的空模板。自动门禁（`tests/test_visual_alignment_triad.py`）只钉代码片段与数值；
> 渲染结果层（字形、投影、对比、层级）按 TRIAD 第 3 节口径**仅人工验收**，不引入 canvas 像素基线（字体 / DPR / 抗锯齿三处非确定）。
>
> **当前状态：证据已备，判定未做。** 下表结论栏在真人目检前一律保持未勾选；任何人不得代替真人填「通过」。
> 所有离屏渲染 / 截图证据仅为观察材料，判定仍归真人。

> **证据时效声明（2026-11-23 核对）**：证据图分多批拍摄，**并非全部对应当前版本**。
>
> - 11/18 12:08–16:01 的桌面 `c5_*`、`c1_badge_*` 与 webapp `webapp_m1/m4/m7`，
>   早于 `d34a86c`（11/18 16:02，VA-02/04/05/11 数值对齐：盘径 0.39 / 字号 1.15r /
>   投影偏移 0.10r / 可吃点 0.42 格）——**图里仍是旧参数，不得当当前判据**。
> - `webapp_m2`（11/18 17:35）、web 旧树 `web_m*`（11/19 15:54）、徽记对照 `i_*`
>   （11/19 16:53，晚于 `fbd6c46` 徽记默认关）拍摄于对应改动之后，可作参考。
> - 11/22 的 `87bf31b`（桌面默认精简档 / 首跑文案 / 系统亮暗监听）与 `efeb61c`
>   （web 侧栏分层）之后未重出图。
>
> **判定口径**：以当前 **2.2.1 实机**为准 —— 按各条判据「三端各开一局、同一局面并排观察」。
> 上述 PNG 只作形态参考（例如「投影应向下、无硬边」），**不得据旧图勾选通过 / 不通过**。
> 桌面与 webapp 旧图缺少可复跑的生成脚本（入库的仅 `scripts/capture_web_evidence.py`
> 与 `scripts/capture_badge_evidence.py`），重拍列为待办，**不阻塞本次目检**。

## 0. 执行环境（目检时填写）

- 日期：__________
- 目检人：__________
- 桌面端版本 / 构建：__________
- 浏览器与缩放（web / webapp）：__________
- 主题（classic / 其余浅色 / dark）：__________

## 1. 证据清单

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

### 1.5 徽记开关对照（I-1，VA-14：形态保留、默认关）

> 开关 `pieceBadges` / `piece_badges` 三端默认 `false`；关闭时不画星 / 杠 / 横 / 方徽记，
> 不留环 / 星描边或半透明残影；开启后既有徽记几何口径不变（orbit 0.86 / size 0.26 /
> stroke 0.055，徽记与邻子间隙 ≥0.06 格，由 `test_badge_clearance` 静态复算兜底）。

| 证据文件名 | 应看什么 | 通过判据 | 结论 |
|---|---|---|---|
| `benchmarks/visual_evidence/i_default_no_badges_web.png` | web 旧树默认关初始局全景 | 可核：特色子（射 / 檑 / 尉 / 巡）盘缘上方**无**星 / 横 / 斜杠 / 空心方徽记描边，无半透明残影；盘面无吃子图例卡片。`human-only`：棋子本体文字清晰、不缺笔 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/i_badges_on_web.png` | web 旧树开启态，200% 上缘特色子行裁切 | 可核：射=四角星+细环、檑=三条短横；徽记落在盘缘上方（0.86 r），与邻子 / 子面字形留出 ≥0.06 格间隙，不压字。`human-only`：徽记墨色沿用棋子自身 ink | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/i_default_no_badges_webapp.png` | webapp 默认关初始局全景 | 可核：特色子盘缘上方无徽记描边、无残影；与开启态对照可辨差异。`human-only`：棋子本体不受影响 | ☐ 通过　☐ 不通过 |
| `benchmarks/visual_evidence/i_badges_on_webapp.png` | webapp 开启态初始局全景 | 可核：射=四角星+细环、尉=双短斜杠、檑=三条短横、巡=空心小方四类徽记在位；徽记在盘缘上方、不压子面字形。`human-only`：与 web 旧树 / 桌面同名口径肉眼一致 | ☐ 通过　☐ 不通过 |

## 1.6 AI 视觉复核结论（非人眼终审）

> 口径：本节由 MainAgent 直接查看在盘 PNG 后填写，**不是实机人眼终审**，也不替代第 2 节的真人打勾。
> 只写「我看到了什么」，不写「整体观感良好」这类主观结论。未经查看的图一律标「未复核」，不代填。

复核人：MainAgent（AI 视觉复核）　复核日期：2026-11-19　查看方式：直接读取 `benchmarks/visual_evidence/` 在盘 PNG。

| 证据文件名 | AI 复核结论 | 我实际看到的 | 仍需人眼 |
|---|---|---|---|
| `i_default_no_badges_web.png` | 默认态成立 | 射 / 檑 / 尉 / 巡 四类特色子盘缘上方均无星、横、斜杠、空心方描边，无半透明残影；盘面无吃子图例卡片；河界为「长城 / 阴山」中文，不是 i18n key；13 列格线完整 | 棋子文字笔画清晰度、长期观感 |
| `i_badges_on_web.png` | 开启态成立 | 射＝四角星＋细环、檑＝三条短横，徽记位于盘缘上方（0.86 r 位置），与相邻棋子、子面字形均留出可见间隙，未压字 | 徽记墨色深浅是否与棋子本体一致 |
| `i_default_no_badges_webapp.png` | 默认态成立 | 特色子盘缘上方无任何徽记描边或残影；盘面与 web 旧树默认态观感一致，无图例卡片 | 与桌面端字重是否一致 |
| `i_badges_on_webapp.png` | 开启态成立 | 射＝四角星＋细环、檑＝三条短横、尉＝双短斜杠、巡＝空心小方，四类徽记均在位且各自形态不混，均落在盘缘上方不压字形 | 小尺寸 / 高 DPI 下的可辨性 |
| 其余 16 张（c5_* / webapp_m1,m2,m4,m7 / web_m1,m2,m4,m7 / c1_badge_*） | **本轮未由 AI 复核** | — | 全部待真人逐条打勾 |

**由本节可关闭的项**：I-1 批的「默认关是否零残留」「开启态徽记是否在位且不压字」两条，机器证据（哈希互异 + 开关门禁）加本次看图已足够；**其余全部仍归真人**，尤其是 M-3 盘底纸纹、M-5 缩放、M-6 落子动画这三项离屏无法覆盖。

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
- I-1 开关对照证据（默认关 / 开启，web 旧树 + webapp）：
  - `benchmarks/visual_evidence/i_default_no_badges_web.png` / `i_badges_on_web.png`
  - `benchmarks/visual_evidence/i_default_no_badges_webapp.png` / `i_badges_on_webapp.png`
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

## 3. 本轮证据缺口与待办

- **webapp 截图已补（D2）**：Playwright 装入 `.venv`（未写入 `requirements.txt` / `pyproject.toml` 等任何依赖清单），`channel="chrome"` 复用本机 Chrome，未下载 Chromium；本地 `http.server` 托管 `webapp/`。已出 M-1 / M-2 / M-4 / M-7 四张 webapp 图。**web 旧树截图仍待补**（卡点见下条）。
- **web 旧树截图（F3/H）已解锁出图**：G 批次在 `web/js/app.js` 末尾加了仅离屏使用的调试桥——只有页面在模块加载前已置 `window.__XH_DEBUG__==='offscreen'`，才挂 `window.__xh={app,draw,resizeBoard,geometry}`，生产路径不启用、不进导出清单。H 脚本 `scripts/capture_web_evidence.py` 复用 `.venv` Playwright 1.65.2、`channel="chrome"` 复用系统 Chrome（未下载 Chromium），`http.server` 只托管 `web/`（不托管 webapp），经离屏桥注入 staging 局面与标记数组，已出 `web_m1/m2/m4/m7_*.png` 四张。历史卡点（模块作用域未暴露、开局强依赖后端、标记只由接口推帧）均由该桥绕开；**注入的是 staging 局面，只核对标记层级与形态，不作规则正确性依据**。
- **M-2 重拍（证据守卫）**：首版 M-2 误与 M-1 全景图逐字节相同，已按「浅色 classic + 盘边棋子 + 200% 下缘裁切」重拍；`tests/test_visual_evidence_guard.py` 只读文件校验证据图哈希两两不同、各图 >20 KB、文件名与本模板索引一致（目录缺失则 skip）。M-1 为全景开局图（看字高 / 盘径 / 字重），与 M-2 裁切图形态不同。
- **M-7 将军标记口径**：webapp 离屏会话内临时把 `rules.inCheck` 置真以触发将军环，非真实将军局面；真人目检时应以真实将军局复核层级。
- M-3、M-5、M-6 依赖活体主题切换 / 窗口缩放 / 动画走子，离屏脚本无法覆盖，列入真人目检步骤。
- 离屏证据为** staging 局面**（手工摆子、个别态由脚本强制），只用于核对标记层级与形态，不作为规则正确性依据。
