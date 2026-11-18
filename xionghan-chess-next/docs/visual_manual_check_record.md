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

| # | 验收项 | 桌面离屏证据 | web / webapp 证据 | 这张图该看什么 |
|---|---|---|---|---|
| M-1 | 字形与字重 | `benchmarks/visual_evidence/c5_m1_glyph_weight.png` | `benchmarks/visual_evidence/webapp_m1_glyph_weight.png`（web 旧树待补） | 同一枚子的字高 / 盘径肉眼一致；无「网页字幕感」或「桌面过粗」 |
| M-2 | 投影柔边 | `benchmarks/visual_evidence/c5_m2_shadow_soft.png` | `benchmarks/visual_evidence/webapp_m2_shadow_soft.png`（web 旧树待补） | 浅色 classic 下放大看棋子下缘：投影重心向下、无硬边、不与棋子脱开（VA-05 的 0.55 倍差应能看出） |
| M-3 | 盘底色与纸纹 | 本轮未出图，按第 2 节手工步骤四主题各看一次 | 待补 | 无明显「塑料平涂」；暗角不压四角刻线 |
| M-4 | 深色主题标记对比 | `benchmarks/visual_evidence/c5_m4_dark_markers.png` | `benchmarks/visual_evidence/webapp_m4_dark_markers.png`（web 旧树待补） | dark 主题下可走点不消失、可吃点不与红叉混淆（深色 0.15 放大补偿的理由） |
| M-5 | 高 DPI / 小盘缩放 | 本轮未出图，按第 2 节手工步骤 | 待补 | 浏览器缩放 50% / 200% 或窗口拉窄到最小宽度：线宽不发虚、投影比例不失控 |
| M-6 | 落子手感 | 本轮未出图（动画需活体走子），按第 2 节手工步骤 | 待补 | 同一手棋三端各走一次：动画结束无回弹、无残影；320ms 差异可感知但不突兀 |
| M-7 | 状态叠加层级 | `benchmarks/visual_evidence/c5_m7_state_layers.png` | `benchmarks/visual_evidence/webapp_m7_state_layers.png`（web 旧树待补；将军标记为会话内临时抬高 inCheck 触发，见第 3 节） | 将军 + 选择 + 可走点 + 上一步四态同屏；层级仍是「上一步 < 可吃 < 选择 < 将军」，都亮等于都没亮视为不通过 |
| 徽记（B4/C1，VA-14） | 特色棋子形状徽记 | `benchmarks/visual_evidence/c1_badge_13x13_glyph.png`、`benchmarks/visual_evidence/c1_badge_13x13_image.png`、`benchmarks/visual_evidence/c1_badge_9x10_glyph.png`、`benchmarks/visual_evidence/c1_badge_9x10_image.png` | 待补 | 射=四角星+细环、尉=双斜杠、檑=三横、巡=空心方；徽记落在盘缘上方，不压子面字形；位图模式叠加在美术图之上 |

## 2. 逐条执行记录

### M-1 字形与字重

- 判据（TRIAD）：三端各开一局，同一局面截图并排；同一枚子的字高 / 盘径肉眼一致；无「网页字幕感」或「桌面过粗」。
- 桌面证据：`benchmarks/visual_evidence/c5_m1_glyph_weight.png`
- 网页证据：`benchmarks/visual_evidence/webapp_m1_glyph_weight.png`（web 旧树待补）
- 结论：☐ 通过　☐ 不通过
- 备注 / 偏差记录：__________

### M-2 投影柔边

- 判据（TRIAD）：浅色 classic 主题，放大到 200% 观察棋子下缘；投影重心向下、无硬边、不与棋子脱开（VA-05 的 0.55 倍差应能看出）。
- 桌面证据：`benchmarks/visual_evidence/c5_m2_shadow_soft.png`
- 网页证据：`benchmarks/visual_evidence/webapp_m2_shadow_soft.png`（web 旧树待补）
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
- 网页证据：`benchmarks/visual_evidence/webapp_m4_dark_markers.png`（web 旧树待补）
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
- 网页证据：`benchmarks/visual_evidence/webapp_m7_state_layers.png`（web 旧树待补；该图将军标记为离屏会话内临时把 `rules.inCheck` 置真触发，非真实将军局面）
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

- **webapp 截图已补（D2）**：Playwright 装入 `.venv`（未写入 `requirements.txt` / `pyproject.toml` 等任何依赖清单），`channel="chrome"` 复用本机 Chrome，未下载 Chromium；本地 `http.server` 托管 `webapp/`。已出 M-1 / M-2 / M-4 / M-7 四张 webapp 图。**web 旧树截图仍待补**。
- **M-7 将军标记口径**：webapp 离屏会话内临时把 `rules.inCheck` 置真以触发将军环，非真实将军局面；真人目检时应以真实将军局复核层级。
- M-3、M-5、M-6 依赖活体主题切换 / 窗口缩放 / 动画走子，离屏脚本无法覆盖，列入真人目检步骤。
- 离屏证据为** staging 局面**（手工摆子、个别态由脚本强制），只用于核对标记层级与形态，不作为规则正确性依据。
