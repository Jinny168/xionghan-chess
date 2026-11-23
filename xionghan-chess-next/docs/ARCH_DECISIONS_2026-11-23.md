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
| 桌面① | `src/xionghan_chess/desktop/ui/piece_atlas.py` 模块级 `PIECE_OPTION_KEYS`(:91-115) | **删除整块常量**；使用处改为 `from xionghan_chess.core.profiles import piece_option_groups` 并按 `PieceType` 取值 | 该文件的说明文本/图谱逻辑不动 |
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
