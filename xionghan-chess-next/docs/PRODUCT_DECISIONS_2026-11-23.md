# 产品口径裁决建议（2026-11-23）

> 状态：**裁决建议，未实施**。提出人：游有方（创意总监）。
> 基线：HEAD `d41aca35b9da0826eca55ccb2bc0c842c6ddb70e`（短号 `d41aca3`）已核对；版本 2.2.1；`RULE_VERSION = 3`（`src/xionghan_chess/core/profiles.py:29`）。
> 范围：仅本文件。不改源码、测试、其它文档、CHANGELOG、版本源；不推送。
> 下文所有路径相对 `xionghan-chess-next/`。引用既有口径一律逐字，不改写。

## 0. 取证口径（逐条可核对）

| 项 | 事实 | 证据 |
|---|---|---|
| A 服务端 | `/api/analysis` 调 `analyze_game(game, request.difficulty)`，未传上限 → 走默认 200 | `src/xionghan_chess/service/app.py:710`；`src/xionghan_chess/core/analysis.py:45-50`（`max_plies: int = 200`） |
| A 桌面 | 上限 120，真被截断时带 `cappedPlies` | `src/xionghan_chess/desktop/ui/workers.py:32,127,130-131`；提示落点 `src/xionghan_chess/desktop/ui/dialogs.py:897-900` |
| A Webapp | 上限 120，真被截断才提示 | `webapp/js/ui/app.js:158-160,890`；文案 `webapp/js/i18n.js:321,659` |
| A Web 旧树 | 调服务端拿结果，既无 120 上限也无 `capped` 提示键 | `web/js/app.js:324-325`；`web/js/i18n.js:149-151`（只有 `analysis.shallow` / `shallow_hint`）；`web/index.html:173` |
| A 已知不一致 | 代码注释已如实记录，行为未对齐 | `src/xionghan_chess/desktop/ui/workers.py:27-31` |
| B 现状 | `render == "glyph"` 时强制写回 `piece_style="glyph"`，并落盘 | `src/xionghan_chess/desktop/config.py:331-344,369-383` |
| B 理由原文 | 「那只是"下次再选图片风格时"的记忆位」 | `src/xionghan_chess/desktop/config.py:338-339` |
| B 先例 | 轻量档只提示一次、不改档位 | `.workbuddy/memory/2026-11-22.md:130-133`；`src/xionghan_chess/desktop/app.py:620-646`；`tests/test_desktop_light_profile_intro.py:1-11` |
| B 先例 | 「无背景」不再静默改写 | `.workbuddy/memory/2026-11-18.md:141-148`（commit `5b1ac38`）；`docs/IMPROVEMENT_PLAN.md:71,250` |

补充：未跟踪的生成树 `online/public/index.html` 已在客户端本地分析里用 `const CAP = 120` 并发提示（`:6292,7023`），但该树不是本项裁决的输入，且**不得手改生成物**。

---

## 任务 A：复盘分析覆盖面 200 手 vs 120 手

### A-1 裁决

**统一到 120 手。** Web 服务端按 120 手分析，Web 客户端补「真被截断才出现」的覆盖提示；桌面与 Webapp 行为与文案不改。

### A-2 理由（从玩家体验出发）

1. **覆盖面不一致就是"教的东西不一样"，不是"深度不同"。** 同一份棋谱，Web 会点评第 150 手并给出档位，桌面/Webapp 根本不看这一手。玩家换设备复盘同一局会得到两套事实。这与"棋盘即主角、小而美"的体验目标直接冲突——玩家不该先搞懂"我在哪个端"。

2. **120 是本版已发布的产品承诺，200 是唯一离群值。** `docs/CHANGELOG_2.2.1.md:14` 逐字写着：

   > **分析手数由 40 手提高到 120 手**。中后盘的失误不再因为超出旧上限而被略过；如果一局真的长到被截断，会明确提示「只分析了前 120 手」，不会让人误以为整局都看过了。

   `tests/test_replay_analysis_dialog.py:99` 逐字写着：

   > 桌面从 40 提到 120：与 webapp 的 `const CAP = 120` 同值，不许再漂。

   两端已有共同锚点与防漂移守卫；`src/xionghan_chess/desktop/ui/workers.py:27-31` 也已注明服务端"留待后续对齐"。把 Web 对齐到 120 是兑现承诺，不是新口径。

3. **"浅层参考"的定位决定了 200 不会更可信。** `docs/CHANGELOG_2.2.1.md:13` 逐字写着「去掉「评分下降 120」「损失 500」这类精确数字与胜率百分比……现在只给出**档位**……并明确标注这是「浅层参考」」。分析定位是轻量参考而非权威报告；从 120 延长到 80 手额外内容，增加的是等待与阅读负担，不是判断质量。

4. **本地是主体验，Web 是便利入口。** 产品硬约束是纯本地、零采集、零账号、零联网依赖。让联网/旧树入口向本地口径看齐，比反过来抬高桌面与移动端负担更合理；移动端 WebView 的 120 是刻意选择（`webapp/js/ui/app.js:158-160` 注释明写只有真截断才提示）。

5. **等待成本是体验成本。** `analyze_game` 逐手重建局面并搜索（`core/analysis.py:58-66`）。服务端 200 手意味着更长的阻塞请求与更大的返回体；对"傻瓜式"产品，可预期的短等待优于偶尔更全但更慢的结果。

### A-3 「允许分层」是否成立

**不采用分层；并且判定既有「按端分层验收，不承诺全端同深度」口径不适用于本项。**

- 该口径出处 `docs/ITERATION_PLAN_ROUND_NEXT.md:216` 的 P0-1 行，成本/风险栏逐字为「**按端分层验收，不承诺全端同深度**」。它讲的是**呈现深度/搜索深度/展示丰富度**可按端不同（例如某端先只有档位、另一端后续再加走势说明）。
- 本项分歧是**覆盖面**：哪些手被分析、哪些手会产生档位结论。这是数据集层面的不同，不是深度层面的不同。用"深度"口径去豁免"覆盖面"差异，等于允许三端对每个具体着法给出不同事实。
- 项目对该口径已有一次边界裁定，逐字见 `.workbuddy/memory/2026-11-22.md:132-134`：

  > 桌面复盘口径纳入。口径原文限定「铺到 Web」，但同一份棋谱 web 显示「失误」、桌面显示「评分下降 120」，两端教相反的东西。纳入是加严，不违背「不承诺全端同深度」。

  即：**统一口径属于加严，不违背分层口径**；反过来，拿分层口径去阻止统一，才是误用。

**若主理人仍然要求分层，只有在同时满足下列四条时才可接受**（缺一条即退回统一 120）：

1. 差异只发生在每手搜索深度/呈现粒度，**不得**发生在该分析哪些手；同一份棋谱三端必须给出同一组被点评的 ply 与同一档位标签；
2. 每一端在**真被截断时**各画各的提示，且提示中的手数取自该端实际上限，不硬编码；
3. 用户可见口径中不得出现"某端看得更多所以结论不同"的隐含事实分叉；
4. 不静默替换用户选择、不借分层顺手改规则语义或 AI 配置。

### A-4 用户可见文案（中英各一）

按现有 `analysis.capped` 键的语义扩展，只在 `history > cap` 时出现；不写分值、不作权威口吻、不出现"正确/错误"判词。

- 中文：`（仅分析前 {n} 手，浅层参考；未分析的手不判断好坏）`
- English: `(First {n} plies only — a shallow reference; later moves are not judged.)`

落点约束：`{n}` 必须来自单一上限常量，不得写死 `120`；文案替换既有 `analysis.capped` 的值，保持三端同一句；`web/js/i18n.js` 目前**没有** `analysis.capped` 键（`:149-151` 只有 shallow/shallow_hint），需由实现方补上。生成物（`webapp/dist/`、`online/public/`、`webapp/.edgeone/assets/`）不得手工编辑，随构建重生成。

### A-5 不作为（本项明确不碰）

- 不碰 AI `CONFIGS` / 搜索预算 / 难度映射（`core/ai.py`）。改覆盖面不等于改深度；`CONFIGS` 一动会牵动 K5 胜率与新手采样率口径（`.workbuddy/memory/2026-11-18.md:130`）。
- 不 bump `RULE_VERSION`（当前 3）、不改 `core/rules.py` / `core/profiles.py` 走法语义、不改棋谱格式。这是复盘呈现覆盖面，不是规则语义。
- 不改 `quality_for_loss` 阈值、`scoreLoss` / `winRate` 计算（`core/analysis.py:69-108`）。口径对齐时最容易"顺手调档位"，那会把一次一致性修复变成一次未评审的平衡变更。
- 不改 `core/benchmark.py:307` 的 `max_plies=240`（评测口径，与复盘呈现正交）。
- 不借机改 UI 布局、主题、动效；棋盘仍是主角，面板保持平面、克制。
- 不 bump 版本源、不改 CHANGELOG（本轮只出裁决建议）。

---

## 任务 B：棋子美术偏好被规范化

### B-1 裁决

**判定为同类缺陷，不是可辩护的有意设计。**

准确表述是：**代码层面是有意实现，产品前提是错误的**。`3ada66a` 的提交说明逐字写着「`piece_render == "glyph"` 的老配置 → `piece_style = "glyph"`（**老配置优先**，哪怕旧文件里还留着 `piece_style="cartoon"` 的美术偏好）」，说明这个分支是写进去的；但它依赖的前提——"cartoon 只是记忆位"——对 1.6.x 老用户不成立。前提不成立的有意实现，落到用户身上就是静默替换。

### B-2 证据链与理由

1. **1.6.x 的 `piece_style` 是真实生效的可见选择，不是记忆位。** `e2ccd78^`（引入 `piece_render` 之前）的 `src/xionghan_chess/desktop/ui/dialogs.py:66` 逐字有 `("traditional","modern","cartoon")` 三值下拉；`src/xionghan_chess/desktop/ui/board_widget.py:336-347` 按 `piece_style == "modern" / "cartoon"` 实际改画法；云同步映射里也有 `pieceStyle:"piece_style"`（`app.py:477,502`）。用户选 cartoon，看到的就是 cartoon，且被持久化、被同步。

2. **1.7.0 的"新键补默认"制造了这个组合。** `e2ccd78` 给 `DEFAULTS` 加 `"piece_render": "glyph"`，注释逐字为「新增键不 bump CONFIG_VERSION：`{**DEFAULTS, **data}` 会自动给旧配置补上默认值」。于是**每一个** 1.6.x 显式选过 cartoon 的用户，升级后配置都变成 `piece_style="cartoon", piece_render="glyph"`——`piece_render` 的值是程序补的，不是用户选的。

3. **1.7.1 的规范化把这个补出来的默认值当成用户意图，并落盘。** `src/xionghan_chess/desktop/config.py:338-341` 逐字：

   > **老配置优先**：`piece_render == "glyph"` 时必须回到字形（哪怕当时还存着 `piece_style="cartoon"` 的美术偏好 —— 那只是"下次再选图片风格时"的记忆位）。

   `load_config()` 在 `:369-372` 改写、`changed = True`，`:377-383` 调 `save_config(merged)` 回写。用户的 cartoon 选择被**静默且持久地**改掉。

4. **"记忆位"只对另一类人成立，而这类人不会被这条分支命中。** "先选 cartoon、再主动切回字形"的用户，其当下明确选择就是字形——`tests/test_desktop_piece_settings.py:80-83` 逐字写着「四值互斥：选了「书法字形」就等于 style="glyph"（不再保留旧美术偏好）」。对这类用户，写 `glyph` 是执行他的选择，不冲突。**分支真正命中的是第 2 条里的 1.6.x 用户，对他们 `piece_style="cartoon"` 是选择本身，不是记忆。** 一句注释把两个人群合并处理，是缺陷的根因。

5. **它违背已发布的产品承诺与既有先例。**
   - `e2ccd78^:docs/QA_PIECE_ATLAS.md:87` 的 B-2 验收逐字要求「① 重启后棋盘为卡通；② 设置下拉显示 cartoon；③ 图谱「使用中」在 cartoon —— **三处一致**；④ 可读 `config.json` 时 `piece_style=cartoon`」。现在的规范化同时破坏前三处与第四处。
   - 用户裁定原文 `.workbuddy/memory/2026-11-22.md:130`：「项目已有原则「用户选择不被静默替换」」；`src/xionghan_chess/desktop/app.py:624` 原文「项目原则是「用户的选择不再被静默替换」，自动改档违背它」。
   - `docs/IMPROVEMENT_PLAN.md:250` 的 P2-7 原文：「取消"无背景选项被静默改写" | 用户选择不再被静默替换 | 甄原 #12，对齐"交给用户"」；同文件 `:71` 的处置原文「**不允许静默改写**」。
   - `.workbuddy/memory/2026-11-18.md:143-145` 的「选什么存什么」已经对背景键执行过一次同类修复。本项是同一个缺陷类型换了键名。

### B-3 处置方案（与轻量档先例一致）

**先例的可迁移原则**：`.workbuddy/memory/2026-11-22.md:130-133` 的方案 A 逐字是「老用户档位用方案 A（只提示一次，不改档位）」，理由是「项目已有原则「用户选择不被静默替换」」且避免「「看着换了档、规则没变」的静默无效结果」。迁移原则 = **不自动改用户已选值；需要告知时只提示一次并落本地标记；改不改由用户决定**。

1. **主处置：自动保留偏好（属"撤销错误改写"，不是迁移）。**
   - 判据：加载时 `piece_render` 键**缺失**（真正的 1.6.x 存量）且 `piece_style` ∈ {`traditional`, `modern`, `cartoon`} → 视为用户显式选择，**保留 `piece_style` 原值**，并派生 `piece_render="image"`。棋盘、设置下拉、图谱三处回到用户当初看到的样子，一次提示都不必发——因为用户眼前没有发生任何新变化。
   - 已有 `piece_render` 键的 2.x 配置一律维持现状：用户当下明确选过 glyph 就写 glyph，明确选过某风格就写 image；不为"召回记忆"额外改写任何值。
   - 不 bump `CONFIG_VERSION` / `schema_version`：这是纠错分支，不是新 schema 迁移；沿用 `{**DEFAULTS, **data}` 补默认的既有机制。
   - 不得采用"保留 `piece_style=cartoon` 但渲染 glyph"的中间态：那会产生「设置显示 A、棋盘/图谱为 B」，违反 `e2ccd78^:docs/QA_PIECE_ATLAS.md:89` 的 B-3 验收原文「任何时刻不得「设置显示 A、棋盘/图谱为 B」」。

2. **兜底：仅当无法原样保留（原值已被旧版本落盘冲掉、或该风格资源缺失而必须回退）时，一次性提示，不自动替用户改。** 机制与轻量档一致：本地标记键（如 `piece_style_intro_shown`，只提示一次、落盘、不进云同步映射），提示后原值/回退态照实保留，用户可在设置里自行改。

   用户可见文案：
   - 中文：`你之前选过卡通棋子。现在棋盘按当前默认显示字形，原来的风格仍可在「设置 → 外观」里启用，我们不会替你改。`
   - English: `You previously chose cartoon pieces. The board now uses the current default look; your earlier style is still available under Settings → Appearance — we won't change it for you.`

   （`{风格}` 按实测原值替换；无可靠证据时**不猜**，用上面这版不带具体风格名的中性句。）

3. **不做的替代方案**：不把 cartoon 自动迁移成 glyph（现行为的"体面版"仍违背原则）；不做全量配置回滚；不改规则档位、AI 配置、棋谱格式。

### B-4 后续同类新键的默认策略（避免每次重裁）

按下列顺序判断，逐条沿用项目既有写法：

1. **规则类键**：一律进 `rule_options`，由 `RuleOptions.merged()` 的白名单/别名表裁决；不在 `config` 顶层另开第二份定义（依据 `src/xionghan_chess/desktop/config.py:174-182` 的注释「判据统一走 `RuleOptions.merged()`……不会在 config 里长出第二份」）。走规则变更流程，`RULE_VERSION` 按语义决定。
2. **纯新增偏好键**：`DEFAULTS` 声明默认值，**不 bump `schema_version` / `CONFIG_VERSION`**，由 `{**DEFAULTS, **data}` 补缺（依据 `config.py:98-100,111-122,143-147` 多处原文「纯新增键，不 bump schema_version」）。
3. **用户显式选择过的存在值**：**只补缺、不改写**。缺键才写默认值；有值且合法 → 原样保留；非法/未知值 → 不静默改成默认，按第 5 条处理。判据是"这个值是不是用户选的"，**不是**"新键的默认值看起来更合理"。特别注意：由新键自动补出来的默认值**不构成用户意图**（本项正是栽在这里）。
4. **派生字段**（如 `piece_render` 由 `piece_style` 派生）：可以重算派生值，但**不得用派生逻辑回写覆盖源值**；派生结果与源值冲突时，优先保留用户可见的一致性（三处一致：棋盘 / 设置 / 图谱），必要时按第 5 条提示。
5. **确实需要改变用户可见状态**：走一次性提示 + 本地标记键，不改用户值、不自动迁移、不进云同步映射（零采集）。文案照轻量档语气：「可在设置里切换」「我们不会替你改」。
6. **已下线/已移除的 UI 选项**：移除入口 ≠ 改写存量值。存量值要么继续被尊重，要么明确回落并提示；`docs/IMPROVEMENT_PLAN.md:71` 的原文「允许静默改写」已被 `5b1ac38` 废止，当前口径是「用户选什么就存什么」（`.workbuddy/memory/2026-11-18.md:143-145`）。
7. **一次性引导/提示标记**：纯本地，不进云同步映射，不 bump schema（依据 `config.py:120-122,145-147`）。

---

## 与调度方判断不一致（口径精度与时效提示）

未发现影响两项结论的前提错误；HEAD、版本、行号均核对一致（`service/app.py:710`、`core/analysis.py:48`、`workers.py:32`、`webapp/js/ui/app.js:160`、`config.py:331-344`、`workers.py:27-31`）。以下三处为引用精度/时效提示：

1. **B 项注释引用是转述，不是逐字。** 调度信写「代码注释声明的理由是『美术偏好只是记忆位』」；逐字原文为「那只是"下次再选图片风格时"的记忆位」（`src/xionghan_chess/desktop/config.py:339`）。含义一致，本文按原文引用。
2. **IMPROVEMENT_PLAN.md 是历史快照，不是当前状态。** 调度信说 P2-1②/P2-7「已被修成『用户选什么就存什么』」，事实如此（`.workbuddy/memory/2026-11-18.md:141-148`，commit `5b1ac38`）；但 `docs/IMPROVEMENT_PLAN.md:71` 仍保留未修复时的待办原文「处置：让 `none` 真正持久化（首选），或明确回落并提示，**不允许静默改写**」。引用它作依据时须标注"计划原文/未同步修复状态"。
3. **"Web 端"在文件树上有两层。** 调度信说的「Web 端没有截断提示」对受控旧树 `web/` 成立（`web/js/app.js:324-325`、`web/js/i18n.js:149-151`）；未跟踪的生成树 `online/public/index.html` 已有本地分析的 `const CAP = 120` 与提示（`:6292,7023`），但它不调 `/api/analysis`（`:6970-6990` 走本地 worker），不是本次分歧的一方，也不可手改。结论不变：分歧只在受控 `web/` + 服务端。

---

## 汇总表

| 项 | 选择 | 理由一句话 | 依赖 | 下一步责任角色 |
|---|---|---|---|---|
| A 分析覆盖面 | **统一到 120**（服务端下调 + Web 补真截断提示；桌面/Webapp 不动） | 2.2.1 已承诺 120 且两端有防漂移守卫；覆盖面不同会让同一局在三端教出不同事实，而"分层"只豁免深度不豁免覆盖面 | 服务端调用点显式传上限；Web i18n 补 `analysis.capped`；生成物随构建重生成；需一次三端同谱回归 | 主理人排期 → tech-architect 定单一上限来源 → QA 做同谱三端核对 |
| B 棋子偏好 | **同类缺陷；自动保留偏好（撤销错误改写），兜底一次性提示，不迁移** | 1.6.x 的 `cartoon` 是真实可见且被同步的选择，不是记忆位；把它当记忆位改写正是「用户选择不被静默替换」明令禁止的行为 | 区分"无 `piece_render` 键"的存量与 2.x 配置；风格资源缺失时的回退路径；本地提示标记键；不动 `CONFIG_VERSION` | 主理人排期 → tech-architect 定判据与落盘时机 → QA 补"重启后三处一致"回归 |

> 两项均为**建议**，需主理人裁定后才进入实现；本文件不包含代码、测试或版本变更。

---

## 补裁：A-1 / A-4 截断提示文案冲突（同日追加）

> 来源：主理人退回意见；柯桥良架构文档 `docs/ARCH_DECISIONS_2026-11-23.md` §D 末尾异议 1、2（原文已按纪律逐字核对）。
> 基线：本补裁核验时 HEAD = `ac5e11f976c137c15f35d3be5dac87594414a643`（已含 `910ce9c` / `ac5e11f` 两笔架构文档）；本文件 `1a04b82` 原文**未改**，以下为追加与覆盖。
> 性质：**原裁决的局部更正**——A-4 新句撤回，A-1 原文维持。下表覆盖原「汇总表」的 A 行。

### 补-0 核验结论（逐条可核对）

| 核验项 | 实测 | 证据 |
|---|---|---|
| 三端文案已逐字同一 | 中文逐字为「（仅分析前 {n} 手）」（全角括号）；英文同为 `(first {n} plies only)` | 桌面 `src/xionghan_chess/desktop/ui/dialogs.py:900` + `src/xionghan_chess/desktop/texts.py:275`；Webapp `webapp/js/i18n.js:321,659`；Web `web/js/i18n.js` 零命中 |
| 桌面承载机制 | `dlf()` 查 `texts.py` 的 `TEMPLATES`，**不读 locales** | `texts.py:222,275,329-338`；`locales/zh-CN.json:615-624` 无 `capped` 键 |
| Webapp 承载机制 | `analysis.capped` i18n 键，是 S 链源文件 | `webapp/js/i18n.js:321,659` |
| Web 承载机制 | 无 `analysis.capped` 键 | `web/js/i18n.js:149-151` 只有 `analysis.shallow` / `analysis.shallow_hint` |
| 重生成边界 | `web/` **不在** S1–S6 产物链；`webapp/js/i18n.js` **在**链上 | `README.md:87-103`；架构文档 §D `:441-454` |
| 「浅层参考」已常驻 | 三端各有独立的中性标注，不依赖截断句 | 桌面 `src/xionghan_chess/desktop/ui/report.py:159`；Web `web/index.html:173`；Webapp `analysis.shallow` / `analysis.shallow_hint` |

### 补-1 采用哪一句：**保留现有三端同句，撤回 A-4 新句**

最终文案（中英各一，逐字）：

- 中文：`（仅分析前 {n} 手）`
- English: `(first {n} plies only)`

原 A-4 的两条新句 `（仅分析前 {n} 手，浅层参考；未分析的手不判断好坏）` / `(First {n} plies only — a shallow reference; later moves are not judged.)` **撤回，不再作为待落地文案**。

理由（从玩家体验出发）：

1. **现有句已经满足原任务对文案的全部要求。** 它只在真截断时出现，不写精确分值、不作权威判词、语气中性；「浅层参考」由三端各自的**常驻**标注承担（桌面 `report.py:159`「浅层参考：依据本机浅层搜索，仅供参考。」、Web `index.html:173`、Webapp `analysis.shallow`）。把同一句免责声明塞进截断行，是第二遍说同一件事，不是更清楚。
2. **"克制、平面面板、棋盘即主角"反对加长这行。** 新句比现有句长一倍以上，收益是把已在旁边常驻的信息重复一遍；成本是三端文案落点全动。这是负收益的改动。
3. **范围控制优先于文案洁癖。** 保留现有句 ⇒ 桌面零改动、Webapp 零改动、不碰 S1–S6、不碰生成物、不需要新标记键；`web/js/i18n.js` 补一个与桌面/Webapp **逐字同值**的键即可收口本项。用一次"顺手统一"换来三端文案回归与全链重生成，与「小而美、傻瓜式」相悖。
4. **A-4 的「保持三端同一句」在现有句上已经成立**（中英两语均逐字同句，仅承载机制不同）。冲突不是既有事实造成的，是我写 A-4 时引入新句造成的——这一处由我负责更正，不要求架构侧或实现方迁就。

### 补-2 A-1 是否需要替换：**不需要，原文维持**

A-1 原文「**统一到 120 手。** Web 服务端按 120 手分析，Web 客户端补「真被截断才出现」的覆盖提示；桌面与 Webapp 行为与文案不改。」**逐字有效**，无需替换。

为消除今后被误读的空间，在 A-1 后**追加**（不是替换）以下澄清段，可直接粘贴：

> 澄清：此处「文案不改」指桌面与 Webapp 沿用当前逐字同值的截断句——中文「（仅分析前 {n} 手）」、英文 `(first {n} plies only)`（桌面 `dialogs.py:900` + `texts.py:275`；Webapp `webapp/js/i18n.js:321,659`）。Web 旧树没有该键，由实现方新增同值键；三端承载机制不同但字面同一句。

### 补-3 A-4 落点约束的处理：**改为「Web 新增同值键」**

原 A-4 中的这一句：

> 落点约束：`{n}` 必须来自单一上限常量，不得写死 `120`；文案替换既有 `analysis.capped` 的值，保持三端同一句；`web/js/i18n.js` 目前**没有** `analysis.capped` 键（`:149-151` 只有 shallow/shallow_hint），需由实现方补上。生成物（`webapp/dist/`、`online/public/`、`webapp/.edgeone/assets/`）不得手工编辑，随构建重生成。

其中「文案替换既有 `analysis.capped` 的值」**撤销**，替换为以下整段（其余约束——`{n}` 来源、生成物不得手改——继续有效）：

> 落点约束：`{n}` 必须来自单一上限常量，不得写死 `120`；三端截断句沿用当前逐字同值的现有句——中文「（仅分析前 {n} 手）」、英文 `(first {n} plies only)`——桌面与 Webapp 文案**不改**；`web/js/i18n.js` 目前没有 `analysis.capped` 键（`:149-151` 只有 shallow/shallow_hint），由实现方**新增**该键并写入与桌面/Webapp 逐字相同的值。本轮不改桌面 `texts.py` / `locales`、不改 Webapp i18n，因此**不触发 S1–S6 重生成**；生成物（`webapp/dist/`、`online/public/`、`webapp/.edgeone/assets/`）不得手工编辑，也不必随本项重生成。

### 补-4 对架构侧意见的评价（含一处落点更正）

1. **异议 1 成立，不是高估。** 我原 A-1「桌面与 Webapp 行为与文案不改」与原 A-4 新句确实字面冲突；架构侧指出后我撤回新句，不改由实现方二选一。
2. **异议 2 的方向成立，但本轮不再发生。** `webapp/js/i18n.js` 确属 S 链源文件，改它就要按 `README.md:87-103` 的固定顺序跑 S1→S6 并连带 `tests/fixtures/*`。保留现有句后 Webapp 零改动，**这条成本被完全避免**；架构文档 §D `:441-454` 关于「`web/` 不在 S1–S6 链、补它的键不触发重生成」的判断同时成立，可照用。
3. **一处需要更正的落点（否则实现方会改错文件）。** 架构异议 1 写「必须在 `locales` 两语加 `analysis.capped` 键、并把 `dialogs.py:900` 改为读该键」。实测桌面翻译走 `texts.py` 的 `dlf()` / `TEMPLATES`（`:222,275,329-338`），**不读 `locales`**（`locales/zh-CN.json:615-624` 本就没有 `capped` 键，这是设计如此，不是漏配）。若将来主理人另行裁定要换桌面文案，正确落点是 `dialogs.py:900` 的调用点 + `texts.py:275` 的 `TEMPLATES` 条目，而不是 locales。**本轮二者都不动。**
4. **架构侧对 D-A.1 步骤④（codegen 下发上限）的成本提示与本补裁正交**，不在此裁定；是否走「测试断言」退路仍由主理人按排期决定。

### 补-5 覆盖后的汇总表（覆盖原表 A 行，B 行不变）

| 项 | 选择 | 理由一句话 | 依赖 | 下一步责任角色 |
|---|---|---|---|---|
| A 分析覆盖面 | **统一到 120**；Web 服务端下调 + Web 新增 `analysis.capped` 同值键；桌面与 Webapp 文案沿用现值 | 覆盖面差异会让同一局三端教出不同事实；截断句现有三端已逐字同句，新句只是重复常驻的「浅层参考」，不值得换三端落点与全链重生成 | 服务端调用点显式传上限；`web/js/i18n.js` 补键且值逐字同桌面/Webapp；`{n}` 来自单一上限常量；不改 `webapp/js/i18n.js` ⇒ 不跑 S1–S6；需一次三端同谱回归 | 主理人裁定 → 主程序实现 → QA 同谱三端核对 |
| B 棋子偏好 | **同类缺陷；自动保留偏好（撤销错误改写），兜底一次性提示，不迁移** | 1.6.x 的 `cartoon` 是真实可见且被同步的选择，不是记忆位；把它当记忆位改写正是「用户选择不被静默替换」明令禁止的行为 | 区分"无 `piece_render` 键"的存量与 2.x 配置；风格资源缺失时的回退路径；本地提示标记键；不动 `CONFIG_VERSION` | 主理人排期 → tech-architect 定判据与落盘时机 → QA 补"重启后三处一致"回归 |

> 本补裁只更正 A-4 的文案落点，不改变 A-2/A-3/A-5 与任务 B 的任何裁定；仍未实现，仍需主理人确认。
