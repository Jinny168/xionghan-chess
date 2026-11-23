# 架构裁定 2026-11-23：三项技术欠账的方案与契约

> 技术架构总监 · 柯桥良
> 范围：C-1 棋子→开关分组上移 core / 默认时长口径残余 / 桌面 `prefers-reduced-motion` 系统级入口
> 性质：**方案与裁定文档**。本轮不改源码、不改测试、不重生成任何产物；所有结论先经 grep / 源码 / 运行时实测取证。
> 基线：HEAD `d41aca35b9da0826eca55ccb2bc0c842c6ddb70e`（短 `d41aca3`，与调度方一致）；git 根在上一级 `C:/Users/27415/PycharmProjects/xionghan-chess`，工作目录为其子目录 `xionghan-chess-next`。
> 前提假设：版本 2.2.1、`RULE_VERSION=3`、规则语义零改动；三端 = 桌面 PySide6 / Web 旧树（`web/`，服务端算棋）/ Webapp 离线 PWA（`webapp/`）+ Android WebView。若这些前提变化，本文结论需重估。

---

## 0. 与调度方判断不一致（先说清楚，避免按错前提推）

三项里有两处调度方给的前提与实测不符，一处需要澄清口径。按纪律如实列出：

| # | 调度方前提 | 实测结论 | 证据 |
|---|---|---|---|
| 1 | 「三端删除硬编码」「离线端 `offline.js` 如何拿到这份分组」——暗示离线端也有一份分组要删/要接 | **不存在第三份、也不存在离线端触点。** 硬编码只有 **3 份**：桌面 2 份（`piece_atlas.py`、`dialogs.py`）+ Web 旧树 1 份（`web/js/app.js`）。Webapp 与 Android 离线端的设置界面用**扁平 `RULE_LABELS` 列表**渲染，根本不按棋子分组；它们既无需删，也无需接收该分组 | `grep -rn "pieceRuleKeys\|PIECE_OPTION_KEYS" src/ web/ webapp/js android/Resources/` → 仅 3 处命中；`webapp/js/ui/app.js:79` `RULE_LABELS`、`:2421` `for (const [key,label] of Object.entries(RULE_LABELS))`；`android/Resources/assets/offline/offline.js` 内 `rule\|规则` 命中仅为走法规则注释，无设置项渲染 |
| 2 | `PIECE_OPTION_GROUPS` 全仓零命中 → 未做 | 结论一致（零命中属实），但**理由要补**：C-2 守卫 `tests/test_option_wiring.py` 并非靠 `PIECE_OPTION_GROUPS` 工作，而是靠 AST/正则/import 直接读那 **3 份硬编码**。所以 C-1 删硬编码会**当场打破 C-2 守卫**，必须先重构守卫再删——这是调度方未点明的第一依赖 | `grep -rn "PIECE_OPTION_GROUPS"` → 仅 `docs/IMPROVEMENT_PLAN.md:96,97` 与 `docs/AUDIT_1.7.5_full.md:222` 三处文档命中，源码/测试 0 命中；`tests/test_option_wiring.py:17-22,120-124,155-172,192-201` |
| 3 | 「PySide6 6.12.0 的 `QStyleHints` 未暴露 reduced-motion 属性」「Qt 平台主题也读不到」 | **`QStyleHints` 本身确实没有该属性**（记载成立），但 **`QStyleHints::accessibility()` 在 Qt 6.12 新增了 `motionPreference`**——这正是 reduced-motion 的原生入口，且 Windows 平台插件已实现。项目恰是 PySide6/Qt 6.12.0，实测可读。调度方「无入口、需等 Qt 暴露」的结论**已过期** | 运行时实测（§3.1）：`QtCore.qVersion()==6.12.0`、`acc.motionPreference()==MotionPreference.NoPreference`、枚举 `['NoPreference','ReducedMotion']`、`motionPreferenceChanged` 存在；Qt commit `444b9f854e0`：「Read and detect changes in this setting on **Windows**, macOS, iOS and the Gnome desktop for now」；`doc.qt.io/qt/qaccessibilityhints.html`：`[read-only, since 6.12] motionPreference` |

另有口径澄清：`IMPROVEMENT_PLAN.md:96` 写「`PIECE_OPTION_GROUPS` 三处一致」，这是立项时的措辞；实际落地的 C-2 守卫守的是**三份硬编码彼此一致 + 定稿指纹**，不是某个叫 `PIECE_OPTION_GROUPS` 的对象。下文按实际代码说话。

**批次后追加的前提更正（见后文）**：④ C-1 语义等价物 `PIECE_OPTION_KEYS` 有 2 个消费点、桌面①改动点应为 3 处（见「补记」节）；⑤ 产品裁决 A-1/A-4 截断句冲突，经游有方补裁 `94289e4` 撤回新句、三端沿用现有同句（见 §D 异议 1）；⑥ Web 补键落点经主理人 `b307c68` 更正为 `locales/*.json` 而非 `web/js/i18n.js`（见 §D 异议 6）。这三处均晚于本表成稿，按纪律不回改原表、在此登记。

---

## 1. 任务 A：C-1 棋子→开关分组上移 core

### 1.1 三份硬编码的精确位置与逐键比对

**精确定位（逐个 grep 取证，非记忆）：**

```
$ grep -rn "PIECE_OPTION_GROUPS" --include="*.py" --include="*.js" src/ web/ webapp/
（0 命中）
$ grep -rn "pieceRuleKeys\|PIECE_OPTION_KEYS" --include="*.py" --include="*.js" src/ web/ webapp/js android/Resources/
src/xionghan_chess/desktop/ui/piece_atlas.py:91:PIECE_OPTION_KEYS: dict[PieceType, tuple[str, ...]] = {
web/js/app.js:145:const pieceRuleKeys={
（dialogs.py 用局部字面量，见下）
$ grep -n "piece_definitions" src/xionghan_chess/desktop/ui/dialogs.py
308:        piece_definitions = {
356:        for kind, (title_key, description_key, rules) in piece_definitions.items():
```

| 端 | 文件:行 | 数据名 | 形态 | 键集 |
|---|---|---|---|---|
| 桌面① | `src/xionghan_chess/desktop/ui/piece_atlas.py:91-115` | `PIECE_OPTION_KEYS` | 模块级 dict `PieceType -> tuple[str,...]` | 11 型全列（含 5 个空组） |
| 桌面② | `src/xionghan_chess/desktop/ui/dialogs.py:308-352` | `piece_definitions`（`SettingsDialog.__init__` 局部字面量） | dict `PieceType -> (标题key, 说明key, rules元组)` | 11 型全列（含 5 个空组） |
| Web 旧树 | `web/js/app.js:145-151` | `pieceRuleKeys` | 对象字面量 `kind -> [keys]` | **只列 6 个非空组**，其余靠 `:491` 的 `(pieceRuleKeys[kind]||[])` 兜空 |

**逐键比对结果（三份仍完全一致，6 组 / 18 键）：**

| 棋子 | 开关键（按源码顺序） | 桌面① | 桌面② | Web |
|---|---|---|---|---|
| king | `king_can_leave_palace`, `king_diagonal_in_palace`, `king_lose_diagonal_outside_palace`, `invasion_victory` | ✓(:92-97) | ✓(:309-318) | ✓(:146) |
| horse | `horse_blocked_by_leg`, `horse_straight_three`, `horse_straight_three_move_only` | ✓(:99) | ✓(:320-324) | ✓(:147) |
| elephant | `elephant_can_cross_river`, `elephant_gain_jump_two_enemy_territory` | ✓(:100) | ✓(:325-329) | ✓(:147) |
| advisor | `advisor_can_leave_palace`, `advisor_gain_straight_outside_palace` | ✓(:101) | ✓(:330-334) | ✓(:148) |
| pawn | `pawn_fast_move_before_enemy_territory`, `pawn_charge`, `pawn_three_line_capture`, `pawn_backward_at_base`, `pawn_resurrection`, `pawn_promotion` | ✓(:103-110) | ✓(:336-347) | ✓(:149) |
| archer | `archer_enhanced_mode` | ✓(:112) | ✓(:349) | ✓(:150) |
| rook / cannon / guard / thunder / patrol | `()` 空组 | ✓ | ✓ | 未列出（等价空） |

三组集合与挂载归属逐一相等；守卫 `tests/test_option_wiring.py:260-278` 正在跑这条比对并钉住 `6 组 / 18 键` 定稿指纹（`EXPECTED_GROUP_KEYS` :92-110）。**顺序也一致**（虽然守卫用 frozenset 只比集合，但逐行目视三份顺序相同）——上移后应保留该顺序，因为设置界面的呈现顺序是产品口径。

> 注：`IMPROVEMENT_PLAN.md:96` 记载立项时是 6 组 / 19 键（pawn 7 项），2.0.0 删 `pawn_full_movement_at_base` 后变 18 键（守卫注释 :87-91 有同述）。**不要按 19 键写方案。**

### 1.2 上移后的数据形态与 API 字段设计

**core 侧（`src/xionghan_chess/core/profiles.py`）新增：**

建议名沿用调度方与 `AUDIT_1.7.5_full.md:222` 的既定称呼 `PIECE_OPTION_GROUPS`，与既有 `OPTION_DEPENDS_ON`(:147)、`UI_ACTION_REQUIRES`(:176)、`NEGATED_OPTIONS`(:197) 同处一文件、同一风格：

```
PIECE_OPTION_GROUPS: dict[PieceType, tuple[str, ...]] = {
    PieceType.KING: (...), ... PieceType.PATROL: (),
}
def piece_option_groups() -> dict[str, list[str]]:
    """给三端 UI 用（JSON 友好：key 用 value 字符串、值用 list）。"""
    return {kind.value: list(keys) for kind, keys in PIECE_OPTION_GROUPS.items() if keys}
```

**三个刻意的设计选择（附依据）：**

1. **只上移「规则开关键」，不上移 i18n 键。** 桌面②的 `(标题key, 说明key, rules)` 里前两项是展示元数据；`gen_web_profiles.py:57-59` 已明确「Python `core/profiles.py` 不持有展示元数据」，core 不应突然持有。上移后各端保留自己的 `piece.<kind>_label` / `piece_rule.<kind>_long` 查表，只把第三项换成从 core 读。
2. **空组不下发**（`if keys`）。Web 现有消费点 `:491` 本就 `(pieceRuleKeys[kind]||[])`，空组下发只会让 API 载荷变大且无人消费；桌面②的 `piece_groups[kind]` 要为每个兵种建 GroupBox，空组由各端本地的 `PieceType` 全集生成，不依赖这张表。
3. **形状用 `dict[str, list[str]]` + 值字符串键**，与 `option_dependencies()`(:160-162)、`action_requirements()`(:186-188) 完全同构，不引入新范式。

**API 侧（`src/xionghan_chess/service/app.py:237-269` `/api/profiles`）新增字段：**

```
"pieceOptionGroups": piece_option_groups(),
```

放在 `optionDependencies`(:257) 旁，命名沿用既有 camelCase（`negatedOptions`/`actionRequirements`/`ruleVersion`）。**每个 profile 对象内各带一份**（与 `optionDependencies` 同层级），不放顶层——`/api/profiles` 返回的是 `list[dict]`，现有调用方式是 `profiles[0]?.negatedOptions`(:546) 与 `app.profiles.get(id)?.actionRequirements`(:144)，保持层级一致才不需要改客户端的解析结构。

**向后兼容（老客户端不认识新字段）：**

| 场景 | 行为 | 依据 |
|---|---|---|
| 新服务端 + 老客户端（不认识 `pieceOptionGroups`） | JSON 多一个键，老客户端忽略即可，行为完全不变 | 既有先例：`optionDependencies`/`actionRequirements` 都是这样渐进下发的，老版本 web 未读它们时照常运行 |
| 新客户端 + 老服务端（没有该字段） | **必须降级，但绝不复制一份硬编码 fallback**。降级口径：`const groups = profile?.pieceOptionGroups; if (!groups) → 把所有开关键拍平进「常规规则」区`（Web 已有 `general` 扁平渲染路径 `:487`），退化为 webapp 那种扁平列表。用户仍能看到并操作全部开关，只是没有棋子分组标题 | 既有降级范式：`actionVisible` 在 `parents` 缺失时返回常驻（`:144`，注释「宁可多一个能点会报错的按钮，也不要让按钮凭空消失」）；Web `:494` `const deps=profile?.optionDependencies||{}` 缺字段即不置灰。**关键区别**：那些是「少一个增强」，这里是「少一个分组呈现」，都不能靠硬编码兜底，否则 C-1 白做 |
| 桌面端 | 直接 import core，无 API、无版本协商问题；桌面与 core 同包发布 | `dialogs.py:53` 与 `piece_atlas.py:57` 均已 import core.profiles |

**「新增开关触点 7 → 4」的兑现口径：** `IMPROVEMENT_PLAN.md:145` 的 7 处是 `profiles.py` 字段 / `merged()` 别名 / `OPTION_DEPENDS_ON` / `NEGATED_OPTIONS` / `PROFILES` 覆盖 / `rules.py` 逻辑 / `offline.js`；另外「3 份分组」单列。**C-1 只消掉「3 份分组 → 1 处定义（core）+ 3 处读取」**，不含离线端（它本就没有分组触点）。上移后新增一个棋子规则开关要改的是：core 字段（含分组挂载）、`rules.py` + `offline.js` 双引擎、两份 locales——即计划所称的「4」。本方案不改变另外 7 处的职责。

### 1.3 三端改动清单（精确文件:函数）

前提：**先完成 §1.4 的守卫重构**，否则删硬编码即红。

| 端 | 文件:函数 | 改动 | 不变的部分 |
|---|---|---|---|
| 桌面① | `src/xionghan_chess/desktop/ui/piece_atlas.py` 模块级 `PIECE_OPTION_KEYS`(:91-115)，**两个消费点**：`_switches_section`(:543，可写开关)、`_rule_state_row`(:755，只读状态行)；`:533` 为文档字符串 | **删除整块常量**；两处消费点都改为 `from xionghan_chess.core.profiles import piece_option_groups` 并按 `PieceType` 取值；`:533` 文档字符串一并改写 | 该文件的图谱逻辑不动；**两处必须同源改**，否则桌面图谱页读硬编码、设置页读 core，形成同一端两处分叉 |
| 桌面② | `src/xionghan_chess/desktop/ui/dialogs.py::SettingsDialog.__init__`（`piece_definitions` :308-352，消费点 :356 的 `for kind, (title_key, description_key, rules)`） | **删掉每个三元组的第 3 项 rules**；循环改为 `for kind, (title_key, description_key) in ...`，`rules` 从 `piece_option_groups().get(kind.value, ())` 取 | 11 个 GroupBox 的标题/说明/登场复选框、`:437` `_update_piece_availability`、`:477` `_apply_dependency` 全部保留 |
| Web 旧树 | `web/js/app.js` 模块级 `pieceRuleKeys`(:145-151)；消费点 `openSettings` 附近 `:491` | **删除 `pieceRuleKeys` 字面量**；`:491` 改为 `const groups = profile?.pieceOptionGroups`，`rules=(groups?.[kind]||[]).map(...)`；`:486` 的 `profile` 已存在，无需新增请求 | `:487` 常规规则区、`no_progress_draw_plies` 下拉、`:494` `optionDependencies` 置灰不变 |
| Webapp 离线 PWA | `webapp/js/ui/app.js` — **不改** | 无分组触点（`RULE_LABELS` 扁平渲染 :79/:2421） | — |
| Android 离线 | `android/Resources/assets/offline/offline.js` — **不改** | 无分组触点；无需调 API | — |
| core | `core/profiles.py` 新增 `PIECE_OPTION_GROUPS` + `piece_option_groups()` | 唯一数据源 | 不碰 `RuleOptions` 字段/别名/依赖/反向表，不碰 `RULE_VERSION` |
| service | `service/app.py::profiles` :237-269 | 新增 `"pieceOptionGroups": piece_option_groups()` 一个键 | 其余下发字段逐字不动 |
| 守卫 | `tests/test_option_wiring.py` — **先改** | 见 §1.4 | `EXPECTED_GROUP_KEYS`、`EXEMPT` 的判据语义保留 |

**关于「离线端怎么拿到这份分组」——裁定：本轮不需要拿。** 依据：
- 离线端设置界面不按棋子分组呈现（`webapp/js/ui/app.js:79,2421` 扁平 `RULE_LABELS`；Android `offline.js` 无规则开关渲染代码），没有消费点；
- 硬约束是「零联网依赖」，Android 以 `file://` 加载资源，`AUDIT_1.7.5_full.md:476` 已明确否决「运行时读 JSON 表」方案（`MainActivity.cs` 未开 `AllowFileAccessFromFileURLs`）；
- **若未来离线端要上分组 UI**，正确路径是走已有产物链：`scripts/gen_web_profiles.py::payload()`(:127-143) 增加 `PIECE_OPTION_GROUPS` → 重生成 `webapp/js/core/profiles.js`；Android 侧由 `scripts/gen_offline_data.py` 在生成区块里同样从 core 导出（该文件 :3-4 已定义「只生成数据、规则实现手写」的分界）。**绝不新增一个 JS 副本，也绝不在离线端调 `/api/profiles`。**

### 1.4 依赖顺序与门禁

**必须按此顺序，颠倒即红：**

```
① 重构 C-2 守卫 tests/test_option_wiring.py（先让它读 core，且能证明三端已不再硬编码）
② core/profiles.py 加 PIECE_OPTION_GROUPS + piece_option_groups()
③ service/app.py::profiles 加下发字段
④ 桌面两处 + Web 一处删硬编码，改为消费 core/API
⑤ 跑守卫 + 接口测试 + 对拍（见下）
```

**① 守卫重构的具体断言（这是本方案最关键的一步）：**

现有守卫的 3 个读取函数 `desktop_atlas_groups()`(:120-124)、`desktop_dialog_groups()`(:155-172)、`web_groups()`(:192-201) 分别读硬编码；删完后会 `assert ... is not None` 失败。改法：

| 现有断言 | 上移后改为 | 依据 |
|---|---|---|
| `test_three_ends_have_identical_grouping`(:260) 比三份硬编码相等 | 改为「三端源码**不含**分组字面量」+「三端都引用共享名字」（照抄 `test_three_fronts_read_the_shared_action_table` :337-354 的「断言消费方式而非某一行」范式） | 同源后两端天然相等，这条要换成守「不回退」 |
| `test_every_rule_option_is_grouped_or_explicitly_exempt`(:207) 的 grouped 来自三份 | grouped 改为**一份**：`piece_option_groups()` 的键并集 | 守卫的「新字段必须被覆盖」语义不变，只是数据源归一 |
| `test_grouping_matches_the_frozen_fingerprint`(:271) 读 atlas | 改读 core 的 `piece_option_groups()`，仍比 `EXPECTED_GROUP_KEYS` 6 组 / 18 键 | 这是防「两端一致地错」的核心，见 §1.5 |
| `test_grouped_keys_are_real_rule_fields`(:281)、`test_both_locales_cover...`(:302) | grouped 来源同样改读 core；其余不变 | — |
| 新增：`test_shared_group_is_downstream_and_offline_is_flat` | 断言 `service/app.py` 源码含 `"pieceOptionGroups": piece_option_groups()`；断言 `web/js/app.js` 含 `pieceOptionGroups` 且**不再**含 `const pieceRuleKeys`；断言 `webapp/js/ui/app.js` 与 Android `offline.js` 仍不含分组名（防有人「顺手补一份」） | 与 :353-354 的同款写法 |

**②–⑤ 门禁清单：**

| 门禁 | 命令 / 判据 | 卡点与作用 |
|---|---|---|
| 守卫重构先行 | `pytest tests/test_option_wiring.py -q` 全绿；**先注入一个假字段验证必红**（C-2 立项时已做过两次红证，`IMPROVEMENT_PLAN.md:206`） | 卡在 PR：守卫没改就删硬编码 → 测试红，合并不了 |
| core/API 同步 | `pytest tests/test_option_polarity.py tests/test_web_profiles_codegen.py -q`；后者 :30-39 跑 `gen_web_profiles.py --check`，确认 core 改动未让产物漂移 | 卡在 PR：core 改了但没意识到产物链 → `--check` 红。**本轮无需 `--write`**：新字段不进 webapp 产物（§1.3） |
| 接口字段在线 | `pytest tests/test_option_polarity.py -q`（:120 直接 GET `/api/profiles`）；新增一条断言 `r.json()[0]["pieceOptionGroups"] == piece_option_groups()` | 卡在 PR：service 忘了下发 → 红 |
| 产物链完整性 | **本轮不重生成 S1–S6**（README.md:86-103；`gen_rule_fixtures.py:87-96` sourceDigest 含 bundle 产物，顺序不可倒）。仅跑只读 `--check`：`python scripts/gen_web_profiles.py --check`、`python scripts/build_webapp_bundle.py --check` | 若有人误跑 `--write`，必须按 S1→S2→S3→S4→S5→S6 全链重跑并连带 24MB fixtures（`tests/fixtures/removal_fingerprint.json` 等）——**本轮禁止**，因为不动走法语义、`RULE_VERSION` 仍是 3 |
| 对拍回归 | `pytest tests/test_cross_engine.py -q`（`_require_node()` 已硬失败，无 node 会红而不是静默跳过，见 `AUDIT_1.7.5_full.md:114`）；`node webapp/tests/verify-rules.mjs`（README :102） | 卡在 PR：本轮虽不动走法，但 core 文件被改，跑一遍证明「只动 UI 元数据、未碰引擎」 |

**明确不做的伪需求**：不为「离线端拿分组」新增 API 调用、不重生成 fixtures、不 bump `RULE_VERSION`、不动 `offline.js`。

### 1.5 风险：「两端一致地错」如何防

**历史事故的真实形态**（不能只说「有先例」）：`AUDIT_1.7.5_full.md:114` 与 `ITERATION_PLAN_ROUND_NEXT.md:180` 记载 81 条对拍全绿仍分叉；`AUDIT_1.7.5_full.md:476` 给出根因——**所有用例都把 Python state 注入 JS，JS 自己那份开局 roster 从未进入对拍**，所以「一致性检查」只证明了「注入之后行为一致」，没证明「两份初始数据一致」。本项目同类风险在 `IMPROVEMENT_PLAN.md:146` 被概括为「两端'一致地错'时对拍抓不到」。

**C-1 的具体风险与阻断：**

| 风险 | 为什么一致性检查抓不到 | 本方案阻断动作 |
|---|---|---|
| 上移时把某个键挂错棋子（例：把 `horse_blocked_by_leg` 挂到 pawn） | 三端都读 core，天然一致；只比「三端相等」会全绿，但 UI 分组是错的 | **保留 `EXPECTED_GROUP_KEYS` 定稿指纹**（`test_option_wiring.py:92-110,271-278`），上移后改为读 core 比指纹；改指纹 = 显式产品变更，须在 PR 说明用户侧变化。这是唯一能抓「同源但错」的门 |
| 键集合对、归属错 | frozenset 只比集合比不出归属（守卫注释 :28 已指出这点） | 指纹是 `dict[str, frozenset[str]]`（:92），按棋子逐组比；不要退化成「键全集相等」 |
| 三端一起漏掉某个新开关 | 同源后更能「一起漏」 | `test_every_rule_option_is_grouped_or_explicitly_exempt`(:207) 改为读 core 后仍断言：`fields(RuleOptions) ⊆ grouped ∪ EXEMPT`；`EXEMPT` 仍在 :65-85，且 :225-257 四条防豁免表退化（理由非空、无重叠、无死条目、只允许两类）全保留 |
| 有人后来又抄一份硬编码回去 | 代码能跑、测试全绿 | 新增的 `test_shared_group_is_downstream_and_offline_is_flat` 直接 grep 三端源码：Web 不得再出现 `const pieceRuleKeys`，离线端不得出现分组名（§1.4 表末行） |
| core 与 API 下发不同步 | 桌面读 core、Web 读 API，两条路各错各的 | 接口测试断言 API 返回值 `== piece_option_groups()`（同一函数），不是另写一份期望值 |

**验收判据（落地时逐条打勾，缺一不可）：** ① 指纹仍是 6 组 / 18 键且归属逐项匹配；② 三端源码再也搜不到分组字面量；③ API 字段与 core 函数输出逐字节相等；④ C-2 红证仍有效（注入假字段必红且点名）。

---

## 2. 任务 B：`Room.initial_minutes` 口径残余

### 2.1 裁定：**改成引用 `DEFAULT_INITIAL_MINUTES`，不留 20**

不是「风险低所以不动」——有可核对的**遗漏证据**：

```
$ grep -n "initial_minutes" tests/test_default_minutes_single_source.py
3: B2 把 UI 的默认时长从 20 改成 10 时，`Game`、服务端请求模型、房间创建三处
7: 这条测试锁的就是"五处指向同一个常量"。以后谁再手写一个数字，立刻红。
25:    sources = {
26:        "Game.__init__": ...
27:        "桌面 DEFAULTS": ...
28:        "API CreateRoomRequest": ...
29:        "RoomManager.create": ...
30:    }
```

docstring 自称守**五处**（:7），`sources` 字典只有**四处**（:25-30）——漏掉的第五处正是 `src/xionghan_chess/service/rooms.py:61` `initial_minutes: int = 20`。这不是「有意保留的旧值」，是守卫自身的漏网。其余四处与常量都已对齐：

| 位置 | 现状 | 证据 |
|---|---|---|
| `core/game.py:26` | `DEFAULT_INITIAL_MINUTES = 10` | grep |
| `core/game.py:36` | `initial_minutes: int = DEFAULT_INITIAL_MINUTES` | grep |
| `desktop/config.py:128-129` | `"initial_minutes": DEFAULT_INITIAL_MINUTES`，注释「数值本身不在这里写死」 | grep |
| `service/app.py:149` | `Field(DEFAULT_INITIAL_MINUTES, ge=1, le=180, alias="initialMinutes")` | grep |
| `service/rooms.py:199` | `RoomManager.create(..., initial_minutes: int = DEFAULT_INITIAL_MINUTES)` | grep |
| `service/rooms.py:61` | **`initial_minutes: int = 20`** ← 唯一漏网 | grep |

**为什么改它是低风险、但仍然是「该做」：** `Room(...)` 在生产路径只有两处构造，`rooms.py:213-221`（`create`）与 `:259-261`（`create_from_game`），**都显式传 `initial_minutes`**；默认值 20 在生产中不会被读到。唯一不传参的构造点是测试 `tests/test_service_difficulty_errors.py:50`，该用例只断言 `ai_difficulty`（:52-53），不触及时长。所以改动**没有用户可观测行为变化**，但消除了「未来某调用点漏传就拿到 20」的契约陷阱——这正是这条测试存在的目的（docstring :3-7）。

**受影响的测试（落地时逐个处理，本轮只列清单）：**

| 测试 | 影响 | 处置 |
|---|---|---|
| `tests/test_default_minutes_single_source.py` | 把 `Room.__init__` 的 `initial_minutes` 默认值加进 `sources`（:25-30），四处补成五处，兑现 docstring | 必改；改完 `test_constant_is_the_agreed_value`(:20) 仍 10 不变 |
| `tests/test_service_difficulty_errors.py:50` | 直接 `Room(...)` 的默认值 20→10 | **无需改断言**（只测难度归一），但跑一遍确认绿 |
| `tests/test_desktop_config.py:65-82` | 用户配置里的 20 仍须保留 | 无需改；它是老配置处置的护栏（见 §2.3） |
| `tests/test_cross_engine.py:1149` 的 `"initialMinutes": 20` | fixture 显式传参，不依赖默认值 | 不改；确认它走的是显式路径即可 |
| `tests/test_benchmark_match.py:260` `initial_minutes=180` | 显式传参 | 不改 |

**接口语义影响：无。** `Room` 是服务端内部 dataclass，不是 HTTP 契约面；HTTP 契约是 `CreateRoomRequest.initial_minutes`（`app.py:149`，已是 10），由 `app.py:314` 显式传给 `RoomManager.create`。不 bump `RULE_VERSION`（时长不是走法语义，不改合法着法/移除集合/`positionKey`）。

**另一个同源字面量（建议同批改，附理由）：** `rooms.py:257` `remaining = max(game.state.clocks_ms.values(), default=20 * 60_000)` 也是 20。它是「从既有 Game 重建房间时时钟读数的兜底」，虽几乎不可达（`Game.__init__:48` 总会初始化 `clocks_ms`），但与本项属同一默认值家族；建议一并为 `DEFAULT_INITIAL_MINUTES * 60_000` 并加一条覆盖测试。若评估认为不值得动，需在 PR 中写明「此 20 是时钟兜底、非新局默认」，避免下次又被视为漏网。**裁定倾向：同批改，成本一行。**

### 2.2 为什么改 20→10 不造成可观测差异（可核对依据，不是「风险低」）

1. **生产调用链全覆盖**：`grep -rn "Room(" src/ tests/` → `rooms.py:213` 与 `:259` 两处生产构造均显式传 `initial_minutes`（:217 / :260），`:547` / `:562` 只读 `room.initial_minutes` 回灌 `Game`。默认值 20 在生产环境**没有任何进入路径**。
2. **HTTP 入口常量已统一**：`app.py:149` 请求模型默认 10，`app.py:314` 显式传入。
3. **桌面/网页用户侧已是 10**：桌面 `config.py:129` 取常量、`app.py:2184` 显式传；网页 `web/index.html:70` `<option value="10" selected>`、`web/js/app.js:75` `initialMinutes:10`、`:171` 显式传。
4. **走法语义零触碰**：时长只写 `clocks_ms`（`game.py:48`），不影响 `rules.py` / `offline.js` 的合法着法与 `removal_fingerprint`。`RULE_VERSION=3` 不变，无需重生成 fixtures。

### 2.3 老用户配置里的 `initial_minutes=20`：**不动、不提示**

与轻量档先例保持一致，但理由要写准：

- **先例原文**：`docs/CHANGELOG_2.2.1.md:25`——「使用完整规则档的老用户会收到一次『轻量模式』推荐提示：只在首次启动时提示一次，**不会自动改动你的规则档位**，是否切换完全由你决定」。核心原则：**用户选择不被静默替换**。
- **已有护栏**：`tests/test_desktop_config.py:71-82` `test_existing_initial_minutes_is_not_overwritten` 明确断言「用户配置里已经写着的 20 分钟必须原样保留」，注释点破「顺手写成'总是写成新默认'就等于把老用户的选择悄悄抹掉」。
- **裁定**：`Room.initial_minutes` 是**运行时对象**的默认值，不涉及任何持久化用户配置；桌面 `initial_minutes` 是**用户持久化偏好**，已有测试钉死不覆盖。两者互不干涉。本轮**不改用户配置、也不弹提示**——因为与轻量档不同，时长在设置界面直接可见且用户可随时改（桌面 `dialogs.py:151/246/508`，网页 `web/index.html:70`），不存在「用户不知道自己被设成 20」的隐蔽性，提示属多余打扰。若产品侧坚持要有提示，须另立产品变更、同样遵守「不自动改」。

---

## 3. 任务 C：桌面端 `prefers-reduced-motion` 系统级入口

### 3.1 Qt 侧还有没有别的入口可读：**有，而且就在 QStyleHints 里（间接）**

**现状记载**：`KNOWN_ISSUES.md:84-91` 与 `board_widget.py:112-115` 写「PySide6 6.12.0 的 `QStyleHints` 未暴露 reduced-motion 属性（仅 `colorScheme`、`useHoverEffects` 等），Qt 平台主题也读不到 Windows 开关」。

**实测复核（本机，非文档推断）：**

```
$ QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -c "..."
PySide6 6.12.0 / Qt 6.12.0
QStyleHints 的 dir() 全量属性：accessibility, colorScheme, colorSchemeChanged,
  contextMenuTrigger, cursorFlashTime, fontSmoothingGamma, keyboardAutoRepeatRate(F),
  keyboardInputInterval, menuSelectionWraps, mouseDoubleClickDistance/Interval,
  mousePressAndHoldInterval, mouseQuickSelectionThreshold, passwordMaskCharacter/Delay,
  setFocusOnTouchRelease, showIsFullScreen/Maximized, showShortcutsInContextMenus,
  singleClickActivation, startDragDistance/Time/Velocity, tabFocusBehavior,
  toolTipWakeUpDelay, useHoverEffects, useRtlExtensions, wheelScrollLines
→ 确认：QStyleHints **直接属性**里确实没有 motion/animation 项（调度方这点没错）

app.styleHints().accessibility() → <class 'PySide6.QtGui.QAccessibilityHints'>
acc.motionPreference() → MotionPreference.NoPreference
Qt.MotionPreference 枚举 → ['NoPreference', 'ReducedMotion']
acc.motionPreferenceChanged → 信号存在
```

**结论**：`QStyleHints` 直接属性无此入口，但 **`QStyleHints::accessibility()`（Qt 6.10 新增）在 Qt 6.12 暴露了 `motionPreference`**（`doc.qt.io/qt/qaccessibilityhints.html`：`[read-only, since 6.12] motionPreference`：「the motion preference set by the system…determine if the user interface should have fewer animated effects」）。Qt 官方 commit `444b9f854e0`（「Add QAccessibilityHints::motionPreference」, 2026-02-13）写明：**「Read and detect changes in this setting on Windows, macOS, iOS and the Gnome desktop for now」**，Fixes QTBUG-133042。即：**Windows 平台插件已实现读取与变更检测**，不需要自己碰注册表。

> 注意 offscreen 平台恒返回 `NoPreference`（无系统偏好可读），这与 Windows 真机行为不同——真机接入验收必须在 Windows 上做（§3.4）。

### 3.2 若走 Windows 注册表 / 系统主题：具体路径与可核对依据

**裁定：不需要自己读注册表**，Qt 6.12 已封装且带变更信号，自己读反而引入维护负担。但按调度方要求给出可核对依据，说明 Qt 读的是什么、以及「若将来 Qt 封装失效」时的兜底位置：

| 层 | 具体路径 / 常量 | 可核对依据 |
|---|---|---|
| 系统参数（Qt 封装读取的语义） | `SystemParametersInfo(SPI_GETCLIENTAREAANIMATION, …)` | 微软 Learn《Client area animation parameter》：`SPI_GETCLIENTAREAANIMATION` / `SPI_SETCLIENTAREAANIMATION`「indicates whether the user wants to disable animations in UI elements…enables you to enable or disable all such animations」；微软《Accessibility parameters》把 Client area animation 列为辅助功能参数，用户改动时系统发 `WM_SETTINGCHANGE`（`learn.microsoft.com/en-us/windows/win32/winauto/accessibility-parameters`） |
| 持久化注册表（系统参数的落盘处） | `HKEY_CURRENT_USER\Control Panel\Desktop` → `UserPreferencesMask`（REG_BINARY） | 微软 Learn 社区问答（「在 windows 10 中显示动画」问题，accepted answer）明确：该项保存动画效果设置、被第三方反复写回会导致开关自动恢复；MSDN 论坛帖给出「关闭 Animate controls and elements inside windows」时 `UserPreferencesMask=hex:90,12,01,80,10,00,00,00` 的实测值。**位掩码的位定义微软未公开文档化**，这正是「不要自己解析注册表」的理由 |
| UI 入口 | 「在 Windows 中显示动画」／`sysdm.cpl` → 高级 → 性能 → 视觉效果 → 自定义 | 同上微软 Q&A 的操作步骤 |

**为什么自己读注册表是坏方案（成本/风险）：** ① `UserPreferencesMask` 的位含义无官方规范，只能靠实测，Windows 版本升级可能变；② 系统参数与注册表可能不同步（第三方软件写回，微软 Q&A 有实例）；③ 需自己监听 `WM_SETTINGCHANGE` 才能响应运行时变化，而 Qt 已提供 `motionPreferenceChanged`；④ 跨平台要另写 macOS/iOS/Gnome 三套，Qt 已覆盖这四类平台（commit 444b9f85）；⑤ 项目硬约束是纯本地零联网——这两条路都本地，但注册表解析更脆。

### 3.3 成本与风险

**接入设计（对齐 Web/Webapp 的既有口径）：** Web 是 `systemReducedMotion()`（`web/js/app.js:85`）与用户开关**相互独立**，落子动画条件为 `app.preferences.animation!==false && !systemReducedMotion()`（`:199`），将军脉冲同理（`:195`）；Webapp 注释更直白（`webapp/js/ui/app.js:25-26`）：「只读媒体查询命中与否，不改用户偏好开关」。桌面应照此合成：

```
system_reduced = (QGuiApplication.styleHints().accessibility().motionPreference()
                  == Qt.MotionPreference.ReducedMotion)
animations_on = config["animations"] and not system_reduced
```

- `config.animations`（`desktop/config.py:107` 默认 True；`app.py:1633` 传给 BoardWidget `animations=`；`board_widget.py:529` `self.animations_enabled`）**保持为唯一用户偏好**，系统信号只作否决项，不写回配置（对齐「用户选择不被静默替换」）。
- 运行时切换：连 `motionPreferenceChanged` 信号，切换时重算 `animations_on` 并调 `set_animations`（`board_widget.py:527-529`）；Web 端的 `matchMedia` 是即时生效，桌面也应即时响应，不做「下次启动生效」。
- 降级：读不到 accessibility / Qt < 6.12 / 非 Windows 且平台未实现 → `motionPreference==NoPreference` → `system_reduced=False` → **完全退回当前行为**（只看 `config.animations`），零回归。`try/except` 只包属性访问，不吞掉 UI 逻辑异常。

**跨平台：** commit 444b9f85 覆盖 Windows/macOS/iOS/Gnome；KDE 等非 Gnome Linux 桌面可能仍返回 `NoPreference`（降级为当前行为）。这对桌面端（PySide6 打包）可接受；Android WebView 走 Webapp 的 `matchMedia`，不在本项范围。

**成本估计（供排期，非本轮实施）：** 约 0.25–0.5 人日——一个 accessor + 一处合成 + 一个信号连接 + 3–4 条单测（含「系统 ReducedMotion 时用户开 animations 仍不播」「NoPreference 时照旧」「信号触发后即时切换」）。比调度方原先设想的「注册表读取 + 跨平台适配」低一个量级。

### 3.4 裁定：**本轮不做代码接入；但前提已翻转为「条件具备、下轮可低成本做」**

- **本轮不做**：三项任务本轮只出方案；且 C 项要翻转 `KNOWN_ISSUES.md:84-91` 与 `board_widget.py:112-115` 的既有记载，属于文档/语义澄清，不应夹带在方案提交里。
- **解除条件（更新 KNOWN_ISSUES.md §5 时用）**：不再是「待 Qt 暴露平台属性」——**Qt 6.12 已暴露**。改为：
  1. 在 Windows 真机做一次 A/B 验证：系统「在 Windows 中显示动画」开 → `motionPreference()` 应返回 `NoPreference`；关 → 应返回 `ReducedMotion`；来回切换应触发 `motionPreferenceChanged`。**这是接入前的硬门禁**，因为 offscreen 实测恒为 `NoPreference`，不能代表 Windows 平台插件行为。
  2. 验证通过后，按 §3.3 的合入口径接入，`config.animations` 不变、不写回系统偏好。
  3. 若真机 A/B 不通过（Qt 的 Windows 封装失效或语义与「显示动画」开关不一致），才退回「自己读 `SPI_GETCLIENTAREAANIMATION`（必要时解析 `UserPreferencesMask`）」的兜底方案，并同步在 KNOWN_ISSUES 写明「Qt 原生路径失效、改用系统参数」及实测证据。

---

## 4. 汇总表

| 项 | 裁定 | 依赖 | 阻塞 | 下一步责任角色 |
|---|---|---|---|---|
| **A · C-1 分组上移** | **做**。3 份硬编码（桌面2+Web1）上移 core；离线端无触点、不改。core 加 `PIECE_OPTION_GROUPS` + `piece_option_groups()`；API 加 `pieceOptionGroups`（每 profile 内、与 `optionDependencies` 同层）；老客户端忽略新字段、新客户端对老服务端降级为扁平规则区而**不复制硬编码** | ① **先重构 C-2 守卫**（现读 3 份硬编码，删完即红）；② core 定义；③ service 下发；④ 三端删硬编码；⑤ 门禁 | 守卫未重构前不能删硬编码；**本轮禁跑 S1–S6 `--write` 与 fixtures 重生成**（不动走法语义、`RULE_VERSION=3`）；离线端加分组 UI 属未来需求、本轮不做 | 架构（本文）→ 主程序：先改 `tests/test_option_wiring.py`，再按 §1.3 清单改 4 处源码 → QA：红证注入 + `test_cross_engine.py` + `verify-rules.mjs` |
| **B · 默认时长残余** | **改** `rooms.py:61` 为引用 `DEFAULT_INITIAL_MINUTES`（建议连同 `:257` 兜底一并改）。理由：守卫自称五处实守四处，这是漏网非有意保留；生产路径两处构造均显式传参，改动无可观测差异。`RULE_VERSION` 不变 | `test_default_minutes_single_source.py` 把第五处补进 `sources`；跑 `test_service_difficulty_errors.py`、`test_desktop_config.py:71-82` | 无硬阻塞；唯一需注意别把老用户配置里的 20 顺手改掉（`test_desktop_config.py:82` 已钉死） | 主程序：一行常量替换 + 测试补位 → QA：确认老配置不覆盖用例仍绿 |
| **C · 桌面 reduced-motion** | **本轮不做接入**；但**前提翻转**：Qt 6.12 原生有 `QStyleHints.accessibility().motionPreference()`（实测可读、`motionPreferenceChanged` 存在），Windows 插件已实现。**解除条件**：Windows 真机 A/B 验证开关切换能改变返回值并触发信号 → 通过后按 §3.3 低成本接入（0.25–0.5 人日） | 真机 A/B 验证；接入时沿用 Web/Webapp「系统偏好为独立否决项、不写回用户配置」口径 | 当前仅有 offscreen 实测（恒 `NoPreference`），缺 Windows 真机证据；`KNOWN_ISSUES.md:84-91` / `board_widget.py:112-115` 的旧结论需在下轮一并更正 | 架构（本文）→ QA：Windows 真机 A/B（必须有开/关两态截图或输出）→ 通过后主程序接入 + 更新 KNOWN_ISSUES |

**全局约束复核**：三项均不触碰走法语义，`RULE_VERSION` 保持 3，不重生成 24MB fixtures；本轮只新建本文件、只用一个显式路径提交（`git add docs/ARCH_DECISIONS_2026-11-23.md`），不 amend、不推送、不用 `-a/-A/stash`，不纳入 `.workbuddy/memory/MEMORY.md` 及任何 untracked 产物。

---

## 补记（C-1 前提精度）：语义等价物 `PIECE_OPTION_KEYS` 与「部分落地」复核

调度方后续补核：原任务说「`PIECE_OPTION_GROUPS` 全仓零命中 → 未做」字面成立，但存在**语义等价物**。本节按实读代码复核，结论：**C-1 未在任何程度上落地**，三份硬编码全部健在；但需更正两处措辞精度。

**精确取证（HEAD `d41aca3`，逐行实读）：**

```
$ grep -rn "PIECE_OPTION_KEYS\|pieceRuleKeys\|piece_definitions" --include="*.py" --include="*.js" src/ web/ webapp/js android/Resources/
src/xionghan_chess/desktop/ui/dialogs.py:308:        piece_definitions = {
src/xionghan_chess/desktop/ui/dialogs.py:356:        for kind, (title_key, description_key, rules) in piece_definitions.items():
src/xionghan_chess/desktop/ui/piece_atlas.py:91:PIECE_OPTION_KEYS: dict[PieceType, tuple[str, ...]] = {
src/xionghan_chess/desktop/ui/piece_atlas.py:533:        - 只放**单子**开关（`PIECE_OPTION_KEYS`）...
src/xionghan_chess/desktop/ui/piece_atlas.py:543:        keys = [key for key in PIECE_OPTION_KEYS.get(self.kind, ()) if hasattr(options, key)]
src/xionghan_chess/desktop/ui/piece_atlas.py:755:        rows += [(t(f"rule.{key}_short", self.language), key) for key in PIECE_OPTION_KEYS.get(self.kind, ())]
web/js/app.js:145:const pieceRuleKeys={
web/js/app.js:491:  ...(pieceRuleKeys[kind]||[]).map(...)
$ grep -rn "pieceOptionGroups\|piece_option_groups\|PIECE_OPTION_GROUPS" --include="*.py" --include="*.js" src/ web/ webapp/js
（0 命中 → core 无定义、API 无字段）
```

**两处更正：**

1. **§0 表格第 2 行措辞更正**：`PIECE_OPTION_GROUPS` 零命中属实，但语义等价物 **`PIECE_OPTION_KEYS` 确实存在**，且不是「一份」而是 **1 个模块常量 + 2 个消费点**（`piece_atlas.py:543` `_switches_section` 可写开关、`piece_atlas.py:755` `_rule_state_row` 只读状态行；`:533` 是文档字符串）。§1.3 桌面①行已据此写全为「删除常量 + 改 `:543`/`:755` 两处读取」——这两个消费点必须一并改为读 core，否则桌面图谱页会保留硬编码读取而设置页改了源，形成「同一端两处读不同源」的新分叉。
2. **「`king4|horse3|elephant2|archer1` 旧键名 grep 零命中」的口径说明**：计划文档（`IMPROVEMENT_PLAN.md:96`）里 `king4 · horse3 · elephant2 · advisor2 · pawn7 · archer1` 是**分组形状的计数描述**（「king 组 4 个键」），不是源码里的字面标识符。真实代码里分组以**开关键数组**形式存在（`dialogs.py:309-351`、`piece_atlas.py:92-115`、`app.js:146-150`），所以按 `king4` 这种 token 去 grep 必然零命中，**不能据此推断分组已删除或已上移**。逐键实比结果仍是 §1.1 的 6 组 / 18 键、三份一致。

**「还剩什么没做」精确清单（C-1 完全未落地）：** ① core 无 `PIECE_OPTION_GROUPS` / `piece_option_groups()`（0 命中）；② `/api/profiles` 无 `pieceOptionGroups` 字段（`service/app.py:239-269` 全字段已逐行核对，无此项）；③ 桌面 2 处 + Web 1 处硬编码仍在；④ C-2 守卫仍读三份硬编码（`test_option_wiring.py:120-201`），未改为读 core。**结论不变**：§1 全节方案照旧执行，只是桌面①的改动点从 1 处扩展为 3 处（常量定义 + 2 个消费点）。

---

## D. 承接产品裁决的实现规格

> 来源：`docs/PRODUCT_DECISIONS_2026-11-23.md`（原裁决 commit `1a04b82`；**补裁 commit `94289e4`**，游有方，状态「裁决建议，未实施」）。本节只出**技术落地规格**，不实现、不改源码/测试/版本源。裁决原文与补裁原文按项目纪律逐字引用；引用块之外是我的架构裁定。
> 基线同前文：`d41aca3` 起手核对；补裁核验时 HEAD 为 `ac5e11f`（本文前两笔架构 commit），本次更新时 HEAD 已含 `94289e4`。
> **效力顺序**：补裁 `94289e4` 覆盖原裁决的 A-4 文案与落点（A-4 新句撤回、A-1 原文维持、A-2/A-3/A-5 与任务 B 不变）；主理人 `b307c68`《实施落点更正》进一步覆盖 Web 补键的**文件落点**（从 `web/js/i18n.js` 更正为 `locales/*.json`），方向不变。下文凡涉及截断提示文案与 Web 补键落点，一律以这两笔覆盖为准；原 A-4 原文块与补裁里「补 `web/js/i18n.js`」的表述保留存档但**不是最终落点**。

### D. 裁决原文（关键段逐字照贴）

**A 项裁决原文 · A-1**

> **统一到 120 手。** Web 服务端按 120 手分析，Web 客户端补「真被截断才出现」的覆盖提示；桌面与 Webapp 行为与文案不改。

**A 项裁决原文 · A-3 首段**

> **不采用分层；并且判定既有「按端分层验收，不承诺全端同深度」口径不适用于本项。**
>
> - 该口径出处 `docs/ITERATION_PLAN_ROUND_NEXT.md:216` 的 P0-1 行，成本/风险栏逐字为「**按端分层验收，不承诺全端同深度**」。它讲的是**呈现深度/搜索深度/展示丰富度**可按端不同（例如某端先只有档位、另一端后续再加走势说明）。
> - 本项分歧是**覆盖面**：哪些手被分析、哪些手会产生档位结论。这是数据集层面的不同，不是深度层面的不同。用"深度"口径去豁免"覆盖面"差异，等于允许三端对每个具体着法给出不同事实。

**A 项裁决原文 · A-4 文案与落点**

> - 中文：`（仅分析前 {n} 手，浅层参考；未分析的手不判断好坏）`
> - English: `(First {n} plies only — a shallow reference; later moves are not judged.)`
>
> 落点约束：`{n}` 必须来自单一上限常量，不得写死 `120`；文案替换既有 `analysis.capped` 的值，保持三端同一句；`web/js/i18n.js` 目前**没有** `analysis.capped` 键（`:149-151` 只有 shallow/shallow_hint），需由实现方补上。生成物（`webapp/dist/`、`online/public/`、`webapp/.edgeone/assets/`）不得手工编辑，随构建重生成。

> ⚠️ **上方 A-4 已被补裁 `94289e4` 局部覆盖**：新句撤回、落点改为「Web 新增同值键、三端沿用现有句」。补裁原文见本节末「补裁原文块」。此处保留仅为存档，不得据此实现。

**A 项裁决原文 · A-5 不作为**

> - 不碰 AI `CONFIGS` / 搜索预算 / 难度映射（`core/ai.py`）。改覆盖面不等于改深度；`CONFIGS` 一动会牵动 K5 胜率与新手采样率口径（`.workbuddy/memory/2026-11-18.md:130`）。
> - 不 bump `RULE_VERSION`（当前 3）、不改 `core/rules.py` / `core/profiles.py` 走法语义、不改棋谱格式。这是复盘呈现覆盖面，不是规则语义。
> - 不改 `quality_for_loss` 阈值、`scoreLoss` / `winRate` 计算（`core/analysis.py:69-108`）。口径对齐时最容易"顺手调档位"，那会把一次一致性修复变成一次未评审的平衡变更。
> - 不改 `core/benchmark.py:307` 的 `max_plies=240`（评测口径，与复盘呈现正交）。

**B 项裁决原文 · B-1**

> **判定为同类缺陷，不是可辩护的有意设计。**
>
> 准确表述是：**代码层面是有意实现，产品前提是错误的**。`3ada66a` 的提交说明逐字写着「`piece_render == "glyph"` 的老配置 → `piece_style = "glyph"`（**老配置优先**，哪怕旧文件里还留着 `piece_style="cartoon"` 的美术偏好）」，说明这个分支是写进去的；但它依赖的前提——"cartoon 只是记忆位"——对 1.6.x 老用户不成立。前提不成立的有意实现，落到用户身上就是静默替换。

**B 项裁决原文 · B-3 主处置与兜底**

> 1. **主处置：自动保留偏好（属"撤销错误改写"，不是迁移）。**
>    - 判据：加载时 `piece_render` 键**缺失**（真正的 1.6.x 存量）且 `piece_style` ∈ {`traditional`, `modern`, `cartoon`} → 视为用户显式选择，**保留 `piece_style` 原值**，并派生 `piece_render="image"`。棋盘、设置下拉、图谱三处回到用户当初看到的样子，一次提示都不必发——因为用户眼前没有发生任何新变化。
>    - 已有 `piece_render` 键的 2.x 配置一律维持现状：用户当下明确选过 glyph 就写 glyph，明确选过某风格就写 image；不为"召回记忆"额外改写任何值。
>    - 不 bump `CONFIG_VERSION` / `schema_version`：这是纠错分支，不是新 schema 迁移；沿用 `{**DEFAULTS, **data}` 补默认的既有机制。
>    - 不得采用"保留 `piece_style=cartoon` 但渲染 glyph"的中间态：那会产生「设置显示 A、棋盘/图谱为 B」，违反 `e2ccd78^:docs/QA_PIECE_ATLAS.md:89` 的 B-3 验收原文「任何时刻不得「设置显示 A、棋盘/图谱为 B」」。
>
> 2. **兜底：仅当无法原样保留（原值已被旧版本落盘冲掉、或该风格资源缺失而必须回退）时，一次性提示，不自动替用户改。** 机制与轻量档一致：本地标记键（如 `piece_style_intro_shown`，只提示一次、落盘、不进云同步映射），提示后原值/回退态照实保留，用户可在设置里自行改。

**B 项裁决原文 · B-4 新键策略（7 条，标题逐字）**

> 1. **规则类键**：一律进 `rule_options`，由 `RuleOptions.merged()` 的白名单/别名表裁决；不在 `config` 顶层另开第二份定义
> 2. **纯新增偏好键**：`DEFAULTS` 声明默认值，**不 bump `schema_version` / `CONFIG_VERSION`**，由 `{**DEFAULTS, **data}` 补缺
> 3. **用户显式选择过的存在值**：**只补缺、不改写**。缺键才写默认值；有值且合法 → 原样保留；非法/未知值 → 不静默改成默认，按第 5 条处理。判据是"这个值是不是用户选的"，**不是**"新键的默认值看起来更合理"。特别注意：由新键自动补出来的默认值**不构成用户意图**（本项正是栽在这里）。
> 4. **派生字段**（如 `piece_render` 由 `piece_style` 派生）：可以重算派生值，但**不得用派生逻辑回写覆盖源值**；派生结果与源值冲突时，优先保留用户可见的一致性（三处一致：棋盘 / 设置 / 图谱），必要时按第 5 条提示。
> 5. **确实需要改变用户可见状态**：走一次性提示 + 本地标记键，不改用户值、不自动迁移、不进云同步映射（零采集）。
> 6. **已下线/已移除的 UI 选项**：移除入口 ≠ 改写存量值。存量值要么继续被尊重，要么明确回落并提示
> 7. **一次性引导/提示标记**：纯本地，不进云同步映射，不 bump schema

**补裁原文块（commit `94289e4`，逐字照贴——覆盖上面 A-4 的文案与落点）**

> ### 补-1 采用哪一句：**保留现有三端同句，撤回 A-4 新句**
>
> 最终文案（中英各一，逐字）：
>
> - 中文：`（仅分析前 {n} 手）`
> - English: `(first {n} plies only)`
>
> 原 A-4 的两条新句 `（仅分析前 {n} 手，浅层参考；未分析的手不判断好坏）` / `(First {n} plies only — a shallow reference; later moves are not judged.)` **撤回，不再作为待落地文案**。

> ### 补-2 A-1 是否需要替换：**不需要，原文维持**
>
> A-1 原文「**统一到 120 手。** Web 服务端按 120 手分析，Web 客户端补「真被截断才出现」的覆盖提示；桌面与 Webapp 行为与文案不改。」**逐字有效**，无需替换。
>
> 为消除今后被误读的空间，在 A-1 后**追加**（不是替换）以下澄清段，可直接粘贴：
>
> > 澄清：此处「文案不改」指桌面与 Webapp 沿用当前逐字同值的截断句——中文「（仅分析前 {n} 手）」、英文 `(first {n} plies only)`（桌面 `dialogs.py:900` + `texts.py:275`；Webapp `webapp/js/i18n.js:321,659`）。Web 旧树没有该键，由实现方新增同值键；三端承载机制不同但字面同一句。

> ### 补-3 A-4 落点约束的处理：**改为「Web 新增同值键」**
>
> 其中「文案替换既有 `analysis.capped` 的值」**撤销**，替换为以下整段（其余约束——`{n}` 来源、生成物不得手改——继续有效）：
>
> > 落点约束：`{n}` 必须来自单一上限常量，不得写死 `120`；三端截断句沿用当前逐字同值的现有句——中文「（仅分析前 {n} 手）」、英文 `(first {n} plies only)`——桌面与 Webapp 文案**不改**；`web/js/i18n.js` 目前没有 `analysis.capped` 键（`:149-151` 只有 shallow/shallow_hint），由实现方**新增**该键并写入与桌面/Webapp 逐字相同的值。本轮不改桌面 `texts.py` / `locales`、不改 Webapp i18n，因此**不触发 S1–S6 重生成**；生成物（`webapp/dist/`、`online/public/`、`webapp/.edgeone/assets/`）不得手工编辑，也不必随本项重生成。

> ### 补-4 对架构侧意见的评价（含一处落点更正）
>
> 3. **一处需要更正的落点（否则实现方会改错文件）。** 架构异议 1 写「必须在 `locales` 两语加 `analysis.capped` 键、并把 `dialogs.py:900` 改为读该键」。实测桌面翻译走 `texts.py` 的 `dlf()` / `TEMPLATES`（`:222,275,329-338`），**不读 `locales`**（`locales/zh-CN.json:615-624` 本就没有 `capped` 键，这是设计如此，不是漏配）。若将来主理人另行裁定要换桌面文案，正确落点是 `dialogs.py:900` 的调用点 + `texts.py:275` 的 `TEMPLATES` 条目，而不是 locales。**本轮二者都不动。**

### D-A. A 项（分析覆盖面 200→120）的落地规格

**D-A.0 现状取证（逐条可核对）：**

| 端 | 上限来源 | 证据 |
|---|---|---|
| 服务端 | `analyze_game(..., max_plies: int = 200)`，`/api/analysis` 不传 → 走 200 | `core/analysis.py:45-50`；`service/app.py:706-712`（`:710` `analyze_game(game, request.difficulty)`）；`AnalyzeRequest` 只有 `document`+`difficulty`（`app.py:213-215`） |
| 桌面 | `ANALYSIS_PLY_CAP = 120`，真截断时注入 `cappedPlies` | `desktop/ui/workers.py:32,127,130-131`；提示 `dialogs.py:897-900` |
| Webapp | `const CAP = 120`，`results.length > CAP` 才提示 | `webapp/js/ui/app.js:158-160,890`；文案 `webapp/js/i18n.js:321,659` |
| Web 旧树 | 无本地上限、无 `analysis.capped` 键 → 实现方**在 `locales/*.json` 新增同值键**（`b307c68` 覆盖落点） | `web/js/app.js:324-325`；`web/js/i18n.js:149-151`；补裁 `94289e4` 补-3；主理人 `b307c68` |

**D-A.1 `{n}`「单一上限常量」放哪一层——裁定：放 `core/analysis.py`，其余两端「派生」而非「另立」**

三个现状常量是独立字面量，但**只有 `core/analysis.py` 是服务端与桌面共同 import 的层**（`service/app.py:29` `from xionghan_chess.core.analysis import analyze_game`；桌面 `workers.py` 亦 import `analyze_game`）。收敛方案：

| 步骤 | 动作 | 依据 / 理由 |
|---|---|---|
| ① 唯一真源 | 在 `core/analysis.py` 定义模块常量 `ANALYSIS_PLY_CAP = 120`（紧邻 `analyze_game`），把 `analyze_game` 的 `max_plies: int = 200` 改为 `max_plies: int = ANALYSIS_PLY_CAP` | 服务端与桌面都从这一处取；与 `DEFAULT_INITIAL_MINUTES`(`game.py:26`)、`RULE_VERSION`(`profiles.py:29`) 同范式 |
| ② 服务端 | `service/app.py::analysis` 显式传 `ANALYSIS_PLY_CAP`：`analyze_game(game, request.difficulty, ANALYSIS_PLY_CAP)`；并把 `AnalyzeRequest` **保持两字段不变** | 显式传参让上限在调用点可见、可测；**不动请求模型**是下面 D-A.2 契约判断的关键 |
| ③ 桌面 | `workers.py:32` 删除本地 `ANALYSIS_PLY_CAP = 120`，改为 `from xionghan_chess.core.analysis import ANALYSIS_PLY_CAP`；`:127/:130-131` 调用与 `cappedPlies` 注入不变 | 消灭第二份字面量；行为零变化（值仍 120） |
| ④ Webapp | `webapp/js/ui/app.js:160` 的 `const CAP = 120` **保留**（JS 离线端无法 import Python），但加一条 codegen 守卫：让 `gen_web_profiles.py::payload()` 增加 `"ANALYSIS_PLY_CAP": ANALYSIS_PLY_CAP` 下发到 `webapp/js/core/profiles.js`，`app.js` 从该模块取值替代本地常量；`gen_web_profiles.py --check` 现成的 8 条读回断言（`:287-360`）已能防「JS 常量漂移」，无需新机制 | 真正让三端共用一个数；`profiles.js` 本就是 core→JS 的下发载体（`:1-5`）。若排期不允许碰 codegen，退路是加一条 Python 测试断言 JS 文本里的 `const CAP` 等于 core 常量（照 `test_default_minutes_single_source.py` 范式），但它只能「漂移即红」、不能「自动同源」——首选仍是 codegen |

**D-A.2 为什么这不牵动第 2 节（原任务 B）的 service 契约判断**

第 2 节裁定的是**建房请求默认值**：`Room.initial_minutes` 改引用 `DEFAULT_INITIAL_MINUTES`，HTTP 契约面是 `CreateRoomRequest`（`service/app.py:149`）。A 项改的是**分析函数默认上限**与**`/api/analysis` 的调用实参**，落在 `AnalyzeRequest`（`app.py:213-215`，两字段，无 `max_plies`）与 `analyze_game`（`core/analysis.py:45-50`）。两者是**不同端点、不同请求模型、不同常量**：

- A 项不新增/不删除 `AnalyzeRequest` 字段（步骤②只改调用实参），因此**不产生新的 HTTP 契约字段**，与第 2 节「`Room` 是内部 dataclass、契约在请求模型」的判据互不交叉；
- A 项不碰 `CreateRoomRequest` / `Room` / `DEFAULT_INITIAL_MINUTES` / `desktop/config.py:129` 的任何一行，建房口径（用户侧 10 分钟）原样保留；
- 若实现时有人「顺手」给 `AnalyzeRequest` 加 `max_plies` 让客户端传 → 那才会产生契约面变更，且会让上限重新变成「客户端可覆盖的三份值」，**明令禁止**。裁定：`max_plies` 不作为请求字段，服务端单点持有。

**D-A.3 Web 补 `analysis.capped` 键：bundle/fixtures 要不要重生成、按什么顺序**

先给结论：**Web 侧补键（落点为 `locales/*.json` + 必要的 `web/js/i18n.js` 登记行）不在 S1–S6 产物链上，不触发任何 bundle/fixtures 重生成。** 依据：

- S1–S6 的输入是 `webapp/js/core/profiles.js`、`rules.js`、`online/core/*`、`online/public/index.html`（`README.md:86-103`；`gen_rule_fixtures.py:87-96` 的 `SOURCE_DIGEST_FILES` 五个文件），**不含 `web/js/i18n.js`，也不含 `locales/*.json`**。`web/` 是服务端直托的旧树（`service/app.py` 的 `WEB_DIR`），`locales/` 由 `service/app.py:759` 挂成 `/locales` 静态目录；改这两处都不涉及任何 codegen 产物（主理人 `b307c68` 复算确认）。
- 产品裁决自己也在「与调度方判断不一致」第 3 条区分了「受控 `web/`」与「未跟踪生成树 `online/public/`」；后者 `:6292/:7023` 已有本地分析 `const CAP=120` 与提示，但**不调 `/api/analysis`**（走本地 worker），不是分歧方，**不得手改**。

Web 侧完整改动清单（供实现方）：

| 位置 | 动作 | 备注 |
|---|---|---|
| `locales/zh-CN.json` + `locales/en.json` 的 `analysis` 段（`:615` 附近） | **真正补键的落点**：两语各新增 `capped` 键（主理人 `b307c68` 覆盖更正） | **文案逐字照补裁 `94289e4` 补-1 的现有同句**：中文 `（仅分析前 {n} 手）`、英文 `(first {n} plies only)`——与桌面 `texts.py:275`、Webapp `webapp/js/i18n.js:321,659` 逐字同值。**关键依据**：`web/js/i18n.js:19-27` 的 `fetchCatalog()` 从 `/locales/{lang}.json`（`service/app.py:759` 挂载）加载 catalog，`t()` 查 catalog 后 `?? key` 兜底——在 `web/js/i18n.js` 里加键值**没有读取者**，界面会显示裸键（与 2.2.1 修掉的 `fix-naked-key` 同类缺陷） |
| `web/js/i18n.js`（仅登记，不补词） | 仅当提示节点需要随语言切换时，在 `:149-151` 附近加一行 `setText(选择器, 'analysis.capped')` | 这是**把 DOM 节点登记到键**，不是加文案；不写键值。`t(key, params)` 的插值在 `:25-27`，无需额外机制 |
| `web/js/app.js::renderAnalysis`(:325) | 用 `result.analyzedPlies` 与上限比较，真截断才渲染该提示；`{n}` 取服务端下发的上限值 | 上限来源见下 |
| `service/app.py::analysis` 响应 | 在 `analyze_game` 返回字典里带 `plyCap`（值 = `ANALYSIS_PLY_CAP`），Web 用 `result.plyCap` 插值 | **响应多一个键是加法式兼容**，老客户端忽略即可；不改请求模型 |

顺序裁定：若实现方**同时**执行了 D-A.1 步骤④（`gen_web_profiles.py` 加 `ANALYSIS_PLY_CAP` 下发），则 `profiles.js` 变了，必须按 `README.md:90-103` 的**固定顺序**跑 `S1 --write → S2 --check → S3 → S4 --check → S5 --write → S6`，因为 `gen_rule_fixtures.py:87-96` 的 `sourceDigest` 把 `profiles.js` 与 bundle 产物纳入哈希，乱序会被 `verify-rules.mjs` 的 `build-order` 拦下。**这与第 1 节 A 项的禁令是两回事**：C-1 不动 core 规则口径所以禁跑 S1–S6；A 项若改 codegen 下发常量则**必须**重跑全链。若步骤④走「测试断言」退路，则不改产物、不跑 S1–S6。

### D-B. B 项（棋子美术偏好）的落地规格

**D-B.0 现状取证：**

- `config.py:97` `DEFAULTS["piece_style"]="glyph"`；`:99-100` `DEFAULTS["piece_render"]="glyph"`，注释逐字「新增键不 bump CONFIG_VERSION：`{**DEFAULTS, **data}` 会自动给旧配置补上默认值」。
- `migrate()`(`:305-323`) 的迁移循环**既不读也不写** `piece_style`/`piece_render`，只处理 `schema_version`；`migrated` 与 `raw` 在这两个键上等价。
- `load_config()`:356 读原始 `raw`；`:361` `migrated, changed = migrate(raw)`；`:362` `merged = {**DEFAULTS, **migrated}` ← **此处把缺失的 `piece_render` 补成 `"glyph"`**；`:369` 调 `_normalize_piece_style(merged.get("piece_style"), merged.get("piece_render"))`；`:340-341` `render=="glyph"` → 无条件返回 `("glyph","glyph")`；`:370-372` 不一致 → 改 `merged` 且 `changed=True`；`:377-383` `changed` 为真 → `save_config(merged)` 落盘。
- `save_config()`(`:387-388`) 是整份 `json.dumps` 覆盖写。

**D-B.1 精确判据插入点与「写回还是只改内存」裁定**

**插入点：`config.py:362` 与 `:369` 之间**（`merged` 已补全、但 `_normalize_piece_style` 尚未调用之前）。**判据必须以原始 `raw` 为准，不能用 `merged`**——这是整项最容易踩的坑：`:362` 已经把 `piece_render` 补成 `"glyph"`，若判据写成 `"piece_render" not in merged`，则**任何配置都判定为「键缺失」**，把全体 2.x 用户也卷进来。同样不要用 `migrated`（它虽在本键上与 `raw` 等价，但语义上是「迁移后」，与裁决「加载时键缺失」的原始含义不符）。

伪规格（只描述判据与动作，不写实现代码）：

```
在 :362 后、:369 前插入：
  IF ("piece_render" NOT IN raw) AND (raw.get("piece_style") IN {"traditional","modern","cartoon"}):
      # 1.6.x 存量：程序补出的 render="glyph" 不代表用户意图
      merged["piece_style"]  = raw["piece_style"]     # 原样保留用户显式选择
      merged["piece_render"] = "image"                # 派生：三套美术均为 image
      跳过后面对这两键的 _normalize_piece_style 调用（否则 :340 又把 render 改回 glyph）
  ELSE:
      保留 :369-372 现有 _normalize_piece_style 逻辑，一个字不改
```

**判据为真时：改内存 + 必须写回（`changed = True`）。** 理由：
- 写回的是**被程序自己补错的派生字段** `piece_render`（`glyph → image`），而**用户选的 `piece_style=cartoon` 被原样保留**——改的是程序的错，不是用户的选择，不违反「用户选择不被静默替换」；
- 写回让纠错成为**一次性动作**：落盘后 `raw` 带 `piece_render="image"`，下次启动走 ELSE 分支（2.x 现状口径），不会每次都重判；
- 不写回则每次启动都要重判，且内存值与磁盘值长期不一致，违背裁决 B-4.3「有值且合法 → 原样保留」；
- 落盘沿用 `save_config(merged)` 既有机制，**不 bump `CONFIG_VERSION`/`schema_version`**（裁决 B-3.1 明令），`raw` 里的 `schema_version` 由 `migrate()` 照旧处理。
- 注意 `changed` 只在**该纠错分支或既有归一化分支真的改了值**时置真；`_coerce_numeric`(:367-368) 刻意不置 `changed`（:365-366 注释），此设计不动。

**D-B.2 两套判据的边界（这是实现最容易错的地方）：**

| 判据 | 触发条件（看 `raw`） | 动作 | 用户可见效果 |
|---|---|---|---|
| 纠错（1.6.x 存量） | `"piece_render" not in raw` **且** `piece_style ∈ {traditional, modern, cartoon}` | 保留 style 原值，派生 render=image，写回 | 棋盘/下拉/图谱三处回到用户当初看到的风格；**不提示** |
| 现状（2.x 配置） | `"piece_render" in raw` | 走原 `_normalize_piece_style`：明确 glyph→glyph，明确风格→image | 执行用户当下选择；不为「召回记忆」改写任何值 |
| 无法原样保留（兜底） | 原值已被旧版本落盘冲掉，或该风格资源缺失（`piece_assets.preload` 返回 0，参照 `tests/test_desktop_piece_settings.py:97-104`） | 一次性提示 + 本地标记键 `piece_style_intro_shown`，不改用户值、不进云同步映射 | 照 B-3.2 文案；用户可自行到设置改 |

边界的三个易错点，写进实现验收：
1. **不能看 `merged` 判缺失**（`:362` 已补键，会把 2.x 全卷入纠错分支）——必须在 `:362` 之前缓存 `raw` 的键存在性，或用 `raw` 直接判；
2. **「选过 glyph 又想召回 cartoon 记忆」的 2.x 用户**不可能命中纠错分支：1.7+ 的四值互斥（`tests/test_desktop_piece_settings.py:80-83`「选了书法字形就等于 style=glyph，不再保留旧美术偏好」）会在他选 glyph 时把 `piece_style` 写成 `"glyph"`，而纠错判据的 style 白名单**不含 `glyph`**——这正是裁决 B-1 第 4 条「记忆位只对另一类人成立、而这类人不会被命中」的代码级落点；
3. **禁止中间态**：纠错分支把 render 改成 image 时，style 必须同步保持为三套美术之一，不得出现「style=cartoon 但 render=glyph」（棋盘与下拉不一致），这是 `e2ccd78^:docs/QA_PIECE_ATLAS.md:89` B-3 验收原文的红线。

**D-B.3 回归门禁（供 QA）：** `tests/test_desktop_piece_settings.py` 现有 4 条（`:66/:75/:87/:97`）覆盖下拉/互斥/资源缺失，**不覆盖加载时纠错**；须补：① 造一份 `{"schema_version":2, "piece_style":"cartoon"}`（无 `piece_render`）→ `load_config()` 返回 `cartoon/image` 且磁盘回写；② 同一份再读一次 → 仍 `cartoon/image` 且不重复提示；③ `{"piece_style":"glyph","piece_render":"glyph"}` → 维持 glyph/glyph；④ 资源缺失时走兜底提示且标记键只提示一次。参照 `test_desktop_config.py:71-82` 的「老配置不被覆盖」写法。

### D. 对产品裁决的技术异议

以下不是反对裁决，是实现前必须澄清的技术事实，按纪律如实写入。**异议 1/2 已由补裁 `94289e4` 裁定并消解，保留原文存档、状态改为「已裁定」；异议 3/4/5 仍开放。**

1. ~~**A-4「替换既有 `analysis.capped` 的值、保持三端同一句」的措辞与代码不符。**~~ → **✅ 已裁定（补裁 `94289e4` 补-1/补-2）**：原异议成立——原 A-4 新句与 A-1「桌面与 Webapp 文案不改」字面冲突，实测只有 Webapp 有 `analysis.capped` 键（`webapp/js/i18n.js:321,659`），桌面走 `dlf()`→`texts.py:275` 不读 `locales`。**裁定结果**：撤回 A-4 新句，**三端沿用现有逐字同句** `（仅分析前 {n} 手）` / `(first {n} plies only)`；桌面与 Webapp 文案一律不改，只有 Web 旧树新增同值键；「浅层参考」由三端常驻标注承担（桌面 `report.py:159` / Web `index.html:173` / Webapp `analysis.shallow`）。**我原异议里写的「必须在 locales 两语加键、把 `dialogs.py:900` 改为读该键」是错的，已按补裁补-4 更正**：桌面承载机制是 `texts.py:222,275,329-338` 的 `TEMPLATES` + `dlf()`，`locales` 本就无此键（设计如此，非漏配）；若将来另有裁定要换桌面文案，正确落点是 `dialogs.py:900` 调用点 + `texts.py:275` 模板条目，**本轮二者都不动**。
2. ~~**A-4「文案替换」若落到 Webapp 与 `online/public` 会触发重生成链。**~~ → **✅ 已裁定（补裁 `94289e4` 补-3/补-4.2）**：方向成立但**本轮不再发生**——保留现有句后 Webapp 零改动，`webapp/js/i18n.js` 不碰 ⇒ **不触发 S1–S6、不碰任何生成物**；我在 D-A.3 关于「Web 侧补键不在 S 链、不触发重生成」的判断同时成立、照用。补裁明确：这条成本被完全避免，不需要实现方在「换三端文案」与「跑全链重生成」间二选一。
   **追加落点更正（主理人 `b307c68`，见本节第 6 条）**：补裁说的「在 `web/js/i18n.js` 补键」本身落错了文件——该文件 `t()` 从 `/locales/{lang}.json` 取词（`:19-27`），不持词表；正确落点是 `locales/zh-CN.json` + `locales/en.json` 的 `analysis` 段。两处（web 与 locales）都不在 S 链，重生成结论不变。
3. **D-A.1 步骤④（codegen 下发上限到 Webapp）的成本可能被低估。** 它不是「加一个字段」那么简单：`gen_web_profiles.py` 的 8 条读回断言（`:287-360`）是按固定 payload 键集写的，新增顶层 `ANALYSIS_PLY_CAP` 会让 `check()` 的「产物逐字节 == generated_source()」(①) 与 manifest hash(末尾) 双双变化，必须整套 `--write → --check` 并重跑 S1–S6；且 `webapp/js/ui/app.js:160` 改为 import 后，bundle 的内嵌模块文本也变（S3/S4）。**若排期紧，建议走 D-A.1 的退路**（Python 测试断言 JS 常量 == core 常量），成本从「全链重生成」降为「一条测试」，代价是不自动同源。这是排期与自治度的取舍，需主理人拍板。
4. **B-3 兜底「风格资源缺失时回退」的判据在本仓可测但不完备。** `tests/test_desktop_piece_settings.py:97-104` 用 monkeypatch `piece_assets.preload` 返回 0 来模拟缺失，说明测试能覆盖；但生产路径里「资源缺失」的真实返回值与判据（是 0？是 None？是文件存在性？）我未在本次取证中确认（`preload` 实现未读）。实现方须先读 `piece_assets.preload` 的真实签名与返回值，再定兜底触发条件——**不要照抄测试里的 monkeypatch 值当生产判据**。
5. **B 项纠错分支与「不 bump schema」的边界要说清。** 裁决 B-3.1 不 bump `CONFIG_VERSION`，但纠错会**改写磁盘内容**（`piece_render: glyph → image`）。这与 `migrate()` 的「`schema_version` 未变则不写盘」(`:323`, `changed = raw_version != CONFIG_VERSION`) 是两套不同的写盘理由。实现时 `changed` 必须由**纠错分支独立置真**，不能依赖 `migrate()` 的返回值——否则 `raw_version == CONFIG_VERSION` 的 1.6.x 残留（若存在）会 `changed=False`，纠错只改内存不落盘。已在 D-B.1 写明，此处作为风险提示。
6. **⚠️ 第三处前提更正（主理人 `b307c68` 覆盖，已并入 D-A.3）：Web 补键的文件落点从 `web/js/i18n.js` 更正为 `locales/*.json`。** 这是批次内第二次落点更正：游有方补裁 `94289e4` 先纠正了「桌面不读 locales、走 `texts.py`」，主理人 `b307c68` 再纠正「Web 也不在 `web/js/i18n.js` 持词、走 `locales`」。技术依据实读确认：`web/js/i18n.js:19-27` 的 `fetchCatalog()` 从 `/locales/{lang}.json`（`service/app.py:759` 挂载）加载 catalog，`t()` 查 catalog 后 `?? key` 兜底；`:145-151` 的 `setText` 只做 DOM 节点登记、不持文案。若按补裁原话在 `web/js/i18n.js` 加键值，无任何读取者，`t('analysis.capped')` 仍走兜底显示裸键——与 2.2.1 的 `fix-naked-key` 同类缺陷。我此前 D-A.3 表格写「在 `web/js/i18n.js` 的 analysis 段新增键」已按此更正。两处落点（web/js 登记行、locales 词表）都不在 S1–S6 链，重生成结论不变。

**D 节汇总：**

| 项 | 裁定 | 关键落点 | 阻塞 / 需裁定 | 责任角色 |
|---|---|---|---|---|
| A 分析覆盖面 | 统一 120；上限常量唯一真源放 `core/analysis.py`，服务端显式传参，桌面 import，Webapp codegen（或退路测试守卫）；**文案三端沿用现有同句，只给 Web 旧树补 `analysis.capped` 同值键**（补裁 `94289e4`），**落点为 `locales/*.json`**（主理人 `b307c68`） | `core/analysis.py:45-50`+新常量、`service/app.py:710`、`workers.py:32`、`locales/zh-CN.json`/`en.json` 的 `analysis` 段、`web/js/app.js:325`；桌面 `dialogs.py:900`+`texts.py:275` 与 Webapp `i18n.js:321,659` **均不动**；`web/js/i18n.js` 仅必要时加 `setText` 登记行 | 异议 1/2 **已由补裁消解**（不再有桌面文案改动与 S 链重跑）；异议 6（Web 落点）**已由主理人覆盖更正**；仅异议 3（codegen vs 测试守卫）仍由主理人按排期定；走 codegen 才需 S1–S6 全链 | 主理人排期 → 主程序 → QA 同谱三端核对（含 `fix-naked-key` 式真取词断言） |
| B 棋子偏好 | 1.6.x 存量（看 `raw` 键缺失）保留 style + 派生 image + 写回；2.x 现状；兜底一次性提示 | `config.py:362` 与 `:369` 之间插入判据，`raw` 为准；`:369-372` ELSE 分支不动 | 异议 4（资源缺失判据未实测）须实现前读 `piece_assets.preload`；异议 5（写盘理由独立于 migrate） | 主程序定判据 → QA 补 4 条回归 |

> 本节与前文一样：只出规格，不实现、不改源码/测试/版本源；生成物不得手改。
