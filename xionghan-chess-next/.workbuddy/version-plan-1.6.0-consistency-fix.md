# v1.6.0 一致性修复说明（供版本规划 / F-10 评审直接引用）

> 本段由技术架构侧撰写，用于 `docs/VERSION_PLAN_1.6.0.md` 的 F-10「不改规则语义」条目。
> 每条主张均附可复现的代码级证据。

---

## 0. 一句话结论

本轮修复**不改变任何象棋规则语义**，只补齐实现与已发布文档之间的缺口，并把「2 套规则引擎」的一致性从人工同步转为测试保障。

---

## 1. 规则引擎实际是 2 套，不是 3 套（修正排期成本）

「三端完全独立实现」这一约束，在当前代码里**只有 2 套真实规则引擎**：

| 端 | 规则来源 | 证据 |
|---|---|---|
| 桌面端 | Python core（同进程 import） | `desktop/app.py:22-32` 直接 `from xionghan_chess...` |
| Web 端 | **服务端 Python core**（本地零规则） | `web/js/app.js` 中 `pseudoLegal`/`legalAll`/`function Rules` 命中数 = **0**；`app.js:198` 走棋直接 `send('move', payload)` 上传，合法性由服务端 `Game.move()` 裁决 |
| Android 在线 | 同 Web 端（`MainActivity.cs:186` 直接 `LoadUrl(serverUrl)`） | 壳应用，无本地规则 |
| **Android 离线** | **offline.js（独立 JS 引擎，127 行）** | `android/Resources/assets/offline/offline.js:64-83` |

**对排期的直接影响**：
> 任何规则层修复的同步成本是 **+M（仅 offline.js 一处）**，而非 +2M。
> 需要"独立实现同步"的只有 **Python core ↔ offline.js** 这一对。

---

## 2. 风险框架修正：当前风险是「2 套一致地错」，不是「三端分叉」

两个已确认的 P0（详见 §3）在 `core/rules.py` 与 `offline.js` 中**逐行等价地同时存在**：

```
Python  rules.py:192-202  in_check   → for piece in opponent.pieces: Move(piece.position, king.position) → pseudo_legal
offline.js:69            inCheck    → for(const p of probe.pieces) ... {from:pos(p.row,p.col), to:pos(king.row,king.col)} → pseudoLegal
offline.js:66            armorCaptures ≡ Python rules.py:464-484
offline.js:67            applyUnchecked 三分支 ≡ Python rules.py:164-187
```

**推论**：`tests/test_cross_engine.py` 对这两个 bug **永远 PASS**。5/5 通过只证明「镜像一致」，不证明「规则正确」。

> **这是本轮最重要的认知修正**：跨引擎对拍是**防分叉**的次要防线，**防不了共错**。主防线必须是规则层自身的正确性验证。

### 因此，probe 对拍维度必须扩容（优先级已调整）

现有 `scripts/offline_rules_probe.cjs:31` 只输出 2 个字段：
```js
process.stdout.write(JSON.stringify({moves, check: rules.inCheck(state, state.turn)}));
```

| 维度 | 能抓什么 | 优先级 |
|---|---|---|
| ① `legal_moves` 集合 | 分叉 | 已有 |
| ② `check` 布尔 | 分叉 | 已有（**但本轮 P0 在此维度完全不可见，实测均为 False**） |
| ③ **`applyUnchecked` 后完整棋盘** | **共错的移除逻辑**——本轮 2 个 P0 都在这里 | **最高** |
| ④ 终局 `winner` + `resultReason` | 共错的胜负判定 | 高 |

**为什么③优先于②**：本轮 P0 在 `check` 布尔上不可见，扩②也抓不到。必须比对「走完一步后两端棋盘是否一致」——棋盘一致即移除逻辑一致。

**成本**：S 级。probe 脚本已存在且已有 Node 加载机制，扩 3 个输出字段 + `test_cross_engine.py` 增3 组断言即可。**这是防止同类事故复发的唯一自动化手段。**

---

## 3. 修复项与「一致性修复」定性

### P0-A｜甲连线吃子 / 刺兑子吃王是「隐形杀」

**现象**：`in_check()` 只做单子攻击探测，但 `apply_unchecked()` 有三条**不经过 in_check** 的移除路径：
```
core/rules.py:164-168  ARMOR    → _armor_captures()   甲三子连线吃子
core/rules.py:170-179  ASSASSIN → 拖拽兑子（反向格 dragged）
core/rules.py:181-187  PROMOTION（改 captured 池，不杀王）
```
后果：`in_check` 返回 `False`，但落子后黑王被移除，`core/game.py:208` 直接判 `king_captured` 胜。AI 评估（`root_scores`/`captured_by_move`）与人类均不可见，UI 无将军提示。

**定性依据（这是「非语义变更」的论证）**：
1. `docs/PIECE_RULES.md:85` 已写明甲连线要吃子——**文档定义了护栏，实现漏了护栏**
2. `docs/PIECE_RULES.md:98` 已写明盾保护邻子
3. `core/rules.py:34-36` 类文档自述 *"Authoritative, side-effect free move validation for **every delivery target**"*——**代码自己声明「三端共用同一套判定」是设计契约，当前实现违反了自己的契约**

⇒ 按已发布文档与既有代码契约修复，属**实现缺陷修复**，不改变规则语义。

**方案（O-1，采纳 GDD 提案）**：引入单一攻击源集合 `capturable_squares(state, color)`，供 `in_check` / `legal_moves` 将军高亮 / AI 的 SEE / `captured_by_move` **全部复用**。使「攻击源集合」在代码上**只存在一份**。

**三条实现约束（防止修复过程中再次分叉）**：

> **约束 1｜返回值必须携带目标属性，不能只返回 `set[Position]`**
> ```python
> def capturable_squares(state, color) -> dict[Position, CaptureSpec]
> # CaptureSpec: {by, requires_isolated, blocked_by_shield, ...}
> ```
> 理由：檑/甲/刺对目标的要求不同。若只返回格集合，AI 的 SEE 无法区分「能吃但对方有盾」与「能吃且可吃」，**P0-B 的护栏仍会漏**。
> 覆盖范围须含：甲连线可吃格全集（`_armor_captures`）、刺兑子反向格（`source - (target - source)`，条件同 `rules.py:175`）。

> **约束 2｜offline.js 必须从同一份数据取数**
> 现状 JS 端 `armorCaptures`(L66) / `applyUnchecked`(L67) 各写一遍。若只统一 Python 侧，等于没统一——须让 JS 端也从 `capturableSquares()` 取数。

> **约束 3｜加运行时自检断言（零成本，比注释更硬）**
> ```python
> if DEBUG:  # 仅测试/CI 开启
>     assert king_still_exists(next_state)   # 己方王凭空消失 ⇒ apply_unchecked 漏了 in_check
> ```
> 本次事故若有此断言会立刻暴露。

> **约束 4｜签名中不得出现 `captured`；素材池归「动作可用性」层**
> `capturable_squares` 必须是**纯函数、幂等、可重复查询**（AI 的 SEE 会对同一局面反复调用）。判据是**读写不对称**：
>
> | 操作 | 对 `captured` 池 | 语义类别 |
> |---|---|---|
> | 甲连线吃子 | **只读** | 攻击源 → 进 `capturable_squares` ✅ |
> | 刺兑子 | **只读** | 攻击源 → 进 `capturable_squares` ✅ |
> | **升变**（`rules.py:181-187`） | **写**（`captured[color].remove(dead)`） | 资源池操作 → **不进** ❌ |
>
> 升变会改变池，若塞进同一函数，**AI 每查询一次就消耗一次素材** —— 那不是「攻击源查询」，是「执行动作」。
>
> **三层结构**：
> ```
> ① 棋盘 pieces              —— 位置与类型
> ② 素材池 captured[color]   —— 独立资源状态，影响【升变/复活】的可用性
> ③ 攻击源 capturable_squares —— 只读 ①，决定【吃子/将军】
> ```
> ② 影响「能不能做这个动作」（`legal_moves` 枚举），③ 影响「这个格能不能被吃」（`in_check`/SEE）。二者都是合法性，但**层次不同**。
>
> 若实现时发现 `capturable_squares` 需要读池 → 说明该逻辑属第 ② 层，应放在 `legal_moves`/`pseudo_legal` 的 promotion 分支（`rules.py:86-93`），**不得污染攻击源集合**。
>
> 同时：**O-10（`position_key` 纳入 `captured`）必须执行**，理由见 P0-E。

**范围严格限定（避免与待拍板语义冲突）**：
- ✅ 统一攻击源集合（含 `CaptureSpec` 目标属性）
- ✅ 同步 offline.js 取数路径
- ✅ `rules.py:192`（`in_check` 正上方）加契约注释 + 自检断言
- ❌ 不碰 `river_row` / `pawn_home_row` 等行号常量
- ❌ 不碰兵卒/相象过河判定

> O-9（河界抽常量）、`position_key` 纳入 `captured`、孤立/保护口径统一，**全部押后到 C-1~C-4 拍板之后**。这样 O-1 与 C-x 语义拍板**零冲突，可并行**。

**不采用 O-5（只补 in_check）的原因**：
> O-5 是在逻辑分叉的那一侧打补丁，`apply_unchecked` 侧的甲连线/刺兑子逻辑**一行都不动**。
> **修完逻辑分叉依然存在**——下次再加一条攻击路径，开发者仍需记得改两处，漏一处就是新的隐形杀。

**配套：契约注释必须写在 `in_check` 正上方，而非类文档串**

`apply_unchecked`（`rules.py:152-190`）与 `in_check`（`rules.py:192-202`）物理邻接，`apply_unchecked` 就在 `in_check` **上面 10 行**，同在 `RulesEngine` 类内。任何维护者读到这里都会认为「两段是同一件事的连续代码」。

而实际是：`apply_unchecked` 处理 **3 条**移除路径，`in_check` 只处理 **1 类**探测——**两者差 2 条路径，且这 2 条恰好就是本次的 2 个隐形杀**。

> **代码的物理邻接度与逻辑耦合度完全脱钩** —— 典型的「结构诱导误读」。读者是在读到 `in_check` 时才最需要这个警告，所以注释位置本身就必须是防复发的一部分，而非可选的文档工作。

### P0-B｜刺兑子绕过楯(SHIELD)邻位保护

**现象**：`core/rules.py:175` 只排除「dragged 本身是 SHIELD」，**不检查 dragged 是否被自家盾保护**。而 `pseudo_legal`（`rules.py:95` → `rules.py:459-462`）是有盾保护的。

实测：车直吃被盾保护的卒 `pseudo_legal=False`（保护生效），刺反向兑子同一目标 `pseudo_legal=True` 且真吃掉→ **UI 显示不可吃但实际能被吃**。

**对照**：甲的连线吃子**有**考虑敌方盾（`rules.py:480` `_adjacent_enemy_shield`），故甲不吃被盾保护的子。**这是刺的单点遗漏。**

**定性依据**：`docs/PIECE_RULES.md:98` 已写明盾保护邻子。

**方案**：`rules.py:459-462` 提取为 `_is_protected_by_shield(state, piece)`，在 `rules.py:175` 后补一次调用。（S 级，性价比最高）

### P0-C｜offline.js 在 desktop_* 档案下`pawn_resurrection=true` 但无复活动作（潜伏的引擎能力缺口）

> **定性质疑已解决**：本条最初被表述为「配置欺骗」，经两轮复核后**该表述被推翻**，最终定性为**潜伏的引擎能力缺口**。以下为实测证据链。

**实测证据（Node 直接加载 offline.js 求值，非文本匹配）**：
```
$ node -e "加载 offline.js 的 PROFILES，逐个打印 options.pawn_resurrection"
desktop_complete   pawn_resurrection=true     ← overrides 缺省，继承 DEFAULT_OPTIONS
desktop_classic    pawn_resurrection=true     ← 同上
web                pawn_resurrection=false    ← 显式 overrides
traditional        pawn_resurrection=false    ← 显式 overrides
```

关键机制（`offline.js` 档案表与 `profile()` 签名）：
```js
function profile(id,title,rows,cols,pieces,enabled,overrides={}){
  const options={...DEFAULT_OPTIONS,...overrides};   // overrides 缺省 = {}
```
```js
['desktop_complete', profile('desktop_complete','完整模式',13,13,[...],TYPES)]                          // 第7参缺省
['desktop_classic',  profile('desktop_classic','经典模式', 13,13,[...],CLASSIC)]                        // 第7参缺省
['web',profile('web','精简模式',13,13,[...],WEB,{pawn_resurrection:false,pawn_promotion:false})],      // 显式关闭
['traditional',profile('traditional','传统象棋',10,9,[...],STANDARD,{...})]                              // 显式关闭
```

**与 Python 侧完全一致**（`core/profiles.py:203`/`:208` 同样用 `RuleOptions()` 默认值）。

**功能缺失证据**：
```
offline.js 中 resurrectPawn / resurrect( 方法定义 = 0 处
offline-locales.js  'resurrect' / '复活' = 0
offline/index.html  'resurrect' / '复活' = 0
offline/welcome.html 'resurrect' / '复活' = 0
```

**玩家影响：零。** 离线端 UI 从未暴露复活（四个文件命中均为 0），玩家无从触发。对照桌面端 `app.py` 有 7 处、`web/js/app.js` 有 4 处复活引用。

**综合定性**：
> `desktop_complete` / `desktop_classic` 下引擎能力缺口—— 开关与 Python 对齐为true，但既无 `resurrectPawn` 方法、也无任何 UI 入口。
> **当前是潜伏 bug，不是活跃 bug。** 真实风险是**未来扩散**：一旦有人给离线端补复活按钮、或对齐 `desktop_*` 完整能力，缺口立即变成用户可见的「点了没反应」。

**处置**：本迭代**不修**，但必须留触发条件避免降级后丢失：

> **触发条件（命中任一即升级为必修）**
> 1. 给离线端补复活按钮 / 复活选项文案
> 2. 离线端开始对齐 `desktop_*` 档案的完整能力
> 3. 用户明确要求离线端功能与桌面端一致

**若触发，方案**：在 `offline.js` 补 `resurrectPawn`，落点行号**必须从 profile 读取，禁止硬编码**（与 P0-D 同源），落点合法性校验与 `core/game.py:152-156` 逐条对齐。

### P0-D｜复活落点行号硬编码

**现象**：
```
core/game.py:151        home_row = 8 if RED else 4
web/js/app.js:224       {row: turn==='red'?8:4, col}
```
traditional 是 10 行档案，红兵实际在**第 6 行**（`profiles.py:181` flip = 9 - row）。目前被 `pawn_resurrection=False` 掩盖。

**方案**：抽为 `RuleProfile.pawn_home_row`，三端统一读取。**但需在 C-1~C-4 拍板后执行**（与 O-1 零冲突，但 O-1 期间不碰）。

### P0-E｜`position_key` 不含素材池 → 规则不等价局面被判为同一局面

> 本条由架构侧**独立实测复现**（非引用），证据如下。

**现象**：升变是唯一「**不改变棋盘、但改变合法走法集合**」的状态变量。

实测（`desktop_complete`，红兵(1,0)，双方王异列以排除 `kings_facing` 干扰）：
```
池空        兵(1,0) 合法走法 = [(0,0,None), (1,1,None)]
池有车 rook  兵(1,0) 合法走法 = [(0,0,'rook'), (1,1,None)]
池有马horse 兵(1,0) 合法走法 = [(0,0,'horse'), (1,1,None)]

池空 vs 池有车 走法不同 = True
池有车 vs 池有马 走法不同 = True      ← 池不仅决定「能否升变」，还决定「升变为什么」

棋盘签名相同           = True
position_key(空)==(车) = True      ← ★ 关键
position_key(车)==(马) = True
```

**后果**：`position_key`（`rules.py:210-212`）只序列化 `pieces` 与 `turn`，**不含 `captured`**。上述三个局面棋盘完全相同却被判为同一局面 → `game.py:215` 的三次重复判和会**在规则不等价的局面上误触发**。

#### 严重性升级：AI 评估对素材池完全无感（**根因比缓存碰撞更深**）

GDD 提出「`position_key` 作为 AI 评估缓存键（`ai.py:363`）会发生碰撞」。**该现象成立，但架构侧实测发现根因比这更深一层**：

```python
# core/ai.py:363
cache_key = (game.rules.position_key(game.state), color)   # ← 确实不含 captured
```
缓存碰撞**属实**（两局面共用一个键）。但实测发现：

```
池=[]                评估=156.55
池=[rook]            评估=156.55
池=[rook]×7          评估=156.55
池=[king,king,king]  评估=156.55        ← 连王的素材都不影响评分
```
**清空缓存后分别评估，差异仍为 0.0。** AST 核查确认 `_evaluate`（45 行）**从不出现 `captured` 字样**——它遍历 `game.state.pieces` 累加 `VALUES[piece.type] + positional`，再加 activity / mobility / king_safety / in_check，**没有一项读素材池**。

> **因此：缓存碰撞只是症状，根因是评分函数对池完全无感。**
> **这意味着只修 `position_key` 不足以修复 AI ——** 修好缓存键后，AI 依然会把「池空」与「池有 7 车」评估为同一分数。

**受影响范围已核查**：
| 模块 | 是否读池 | 说明 |
|---|---|---|
| `core/ai.py:_evaluate` | ❌ **否** | 45 行，AST 确认无 `captured` |
| `core/ai_see.py` | ❌ 否 | 9 处 `captured` 均为局部变量 `captured_by_move`，非池 |
| `core/mcts.py` | ❌ 否 | 2 处同为 `captured_by_move` |
| `training/*.py` | ❌ 否 | 4 个文件全部 0 命中 |

**即 MASTER 档（MCTS）与传统档（alpha-beta）共享同一缺陷**，只是路径不同。

**对 v1.6.0 的影响（这是本条最重要的一点）**：
> GDD 原报告的主题是「AI 进化」。**AI 对素材池无感，意味着「多攒素材换大子」这条核心策略在 AI 眼中不存在**——AI 不会因为手里有 7 车素材而主动保留兵、也不会为了素材而容忍小损失。
> 这不是「棋力偏弱」，而是**策略空间缺了一块**。

**方案（分两级，请team-lead 裁决）**：
- **P0-E（必做，S）**：修 `position_key` 纳入池 → 修复三回合计数 + 缓存键正确性
- **P0-F（新，P1→建议升级）**：在 `_evaluate` 中**显式计入素材池价值**。此项**独立于 P0-E**，修完 P0-E 仍然需要它

⚠️ 两项**都需同步 `offline.js` 的 `positionKey`**（2 处命中），否则三回合计数会分叉。
⚠️ P0-E 与 P0-F **互不替代**，请勿只做其一。


**与约束 4 的关系**：约束 4 规定 `capturable_squares` 不读池；P0-E 规定 `position_key` 必须读池。**两者不矛盾**——它们分属第 ③ 层（攻击源）与第 ② 层（动作可用性/局面等价性）。

### 已撤回：升变导致净增子力（原 P0，误判）

GDD 原报告怀疑「升变回收素材会净增子力」，**该 P0 已由提出方主动撤回**，架构侧复核确认**子力守恒成立**：

```
载体（兵）只消耗一次：升变后 type≠PAWN，rules.py:88-90 限制其不能再升变✓
素材（池）每次升变消耗一个 ✓
⇒ 7 兵 + 7 车素材 → 7 车 + 池空
```

池中素材是「**曾属我方、被对手吃掉**」的子，故升变本质是**回收**，总子力上限天然受已阵亡子数约束，**不存在无限增子**。

#### 定性：升变 = 固定成本 1 兵的损失补偿机制（**设计优势，维持不修**）

> ⚠️ **本节曾包含一处错误推导，已更正。** GDD 初稿写「送车换车白赚1 兵」，**该结论错误**——错在把升变当成了凭空创造。架构侧复核发现并要求更正，此处保留更正记录以免误引。

**精算（GDD 修正后，架构侧复核确认）**，用 `ai.py:46-51` 真实 VALUES（车 900 / 兵 120）：
```
起始（7兵2车）    = 7×120 + 2×900 = 2640
车被吃（7兵1车）  = 7×120 + 1×900 = 1740← 已损失 900
升变后（6兵2车）  = 6×120 + 2×900 = 2520

相对「车被吃后」= +780   ← 回收，不是套利
相对「起始」    = −120   ← 净损失 1 个兵
```

**正确结论：不存在「白赚 1 兵」。** 升变的净效果恒等于**损失一个兵**——因为素材是你**已经失去的**子，回收它只是把损失从「900 分的车」压缩到「120 分的兵」。

**四条判据（架构侧复核）**：

| 判据 | 结论 |
|---|---|
| 是否净增子力？ | ❌ 否，上限受已阵亡子数约束（7兵+7车素材 → 7车，实测） |
| 是否存在套利循环？ | ❌ 否。**素材必须先被对手吃掉**，AI 无法主动「送」自己的车来换升变 |
| 相对起始的净损失 | −120（1 个兵），**固定成本**，与素材价值无关 |
| 玩家体验 | ✅ **正向**：损失大子后有补偿路径，心理上「这局还没输」 |

**这是设计意图的正确体现，不是待修问题**：
> 升变成本固定为 1 个兵（120 分），收益是把**已损失的大子拿回来**。因此它是一个「损失越大、补偿越划算」的机制——**缩小方差、增加翻盘可能**，符合「小而美、傻瓜式」的产品定位。玩家只需理解「大子没了可以用兵换回来」，不需要学习复杂子力模型。

**文档建议（P2）**：在 `docs/PIECE_RULES.md:55` 升变说明处补一句「升变是**素材回收**，消耗自身兵与一份阵亡素材，不会增加总子力」，避免玩家误以为可无限造子。**不阻塞 1.6.0。**

### P1-F｜AI 升变评估未计入「阻挡格损失」（AI 侧，backlog）

**代码位置**：`core/ai_see.py:84-87`
```python
def _promotion_gain(piece, move, values):
    if piece.type is PieceType.PAWN and move.promotion is not None:
        return values[move.promotion] - values[PieceType.PAWN]
    return 0
```

> ⚠️ **GDD 对此条的表述有误，架构侧已更正。** GDD 写「AI 把升变当作 +780 的纯收益，**完全没有评估失去这个兵的成本**」——**这不准确**：`780 = 900 − 120` **已经扣除了兵的材料价值**。若按其表述实现，会**重复扣一次兵**。

**真实缺陷是「阻挡格价值为 0」**：
- 升变后该兵**离开原格**，实测原格变空（`(1,0)` 升变后 `piece_at(1,0) is None`）
- 失去的**阻挡/牵制效应**在评分体系中**没有任何项**
- 材料成本 120✅ 已计入；**位置性成本 ≈ 0** ❌ 未计入

**后果**：AI 会不惜代价把兵推到底线升变，**即使该兵是残局中唯一的阻挡子**。在 `traditional`（10×9，兵少、空间紧）尤其明显。

**修复方向（P1，AI 侧，不阻塞 1.6.0）**：在 `_promotion_gain` 之外补一项阻挡价值评估。廉价近似二选一：
```python
# 方案A：残局打折（简单，推荐先做）
### P1-F｜AI 升变评估的次级问题（**已降级为待观察，非必修**）

> **本节结论已两次修正，当前为最终版。**

**第一处更正（GDD 表述有误）**：GDD 写「AI 把升变当作 +780 的纯收益，**完全没有评估失去这个兵的成本**」——**不准确**。`ai_see.py:84-87` 的 `values[move.promotion] - values[PieceType.PAWN]`（= 900−120 = 780）**已扣除兵的材料价值**。若按其表述实现会**重复扣一次兵**。

**第二处更正（更关键）**：曾推断「真实缺陷是阻挡格价值为 0」，**该推断也已撤回**。理由：
- 升变是「移动+变身」，源格腾空在任何走子中都会发生
- Negamax 搜索会评估新局面，**搜索层本就会处理位置性后果**
- 「位置性成本缺失」这一提法**偏弱**

**GDD 已主动撤回其方案 A**（`_is_sole_blocker(...) * 0.3` 系数无依据 —— 该系数实为随手给出）。

**当前结论**：
> 升变的材料成本**已正确计入**；「位置性评估」由搜索层承担，**不构成独立缺陷**。
> **本迭代不修 AI 启发式。** 若日后实测发现 AI 在残局有明显升变误判，再以「实测数据」驱动立项，而非凭假设引入系数。
>
> 若将来确需残局调整，合规形式是放进 `RuleOptions`（如 `endgame_promotion_discount: float = 0.7`）——
> **理由：它是「规则变体参数」不是「AI 强度参数」**，玩家可按喜好关闭，调 AI 强度时也不会误改。
> **不放 `VALUES`**（那是固定子力表），**不放 `_evaluate`**（会被当作可调参数，实际编码的是玩法判断）。

⚠️ **而真正该修的 AI 问题是 P0-F（`_evaluate` 对素材池无感）**，见前节——那才是确定性 bug，不是启发式之争。

---

## 4. 本轮修复范围与工作量（架构侧修订）

| 项 | 量 | Python 侧 | offline.js 侧 | 备注 |
|---|---|---|---|---|
| O-1 统一攻击源集合（含 `CaptureSpec`） | L | L | **M（必须）** | 同步成本已按「2 套引擎」修正；含约束 1/2/3/4 |
| O-2 刺兑子盾保护 | S | S | S（单点） | 不改 in_check 语义；**依赖 O-1 的 `CaptureSpec`** |
| probe 扩至 **5** 维 | S | S | — | 防共错关键；**第5 维 = `positionKey`**（见下） |
| **P0-E `position_key` 纳入池** | **S** | S | **S（必须）** | 已实测复现；修三回合计数 + 缓存键 |
| **P0-F `_evaluate` 计入素材池** | **S** | S | — | **独立于 P0-E**；两引擎共享缺陷；**建议本迭代做**（v1.6.0 主题是 AI 进化） |
| **测试 helper：双方王强制异列** | **S** | S | — | 写入 `tests/`，**根治 `kings_facing` 伪影** |
| P1-F AI 升变阻挡值 | — | — | — | **已降级为待观察，非必修**（两次修正，见§3） |
| P0-C 离线端复活缺口 | S | — | S | **本迭代不修**，潜伏 bug + 三条触发条件 |
| P0-D 复活落点硬编码 | S | S | S | 押后到 C-1~C-4 拍板后 |
| 升变语义文档说明 | S | — | — | P2 文档项，**表述已按精算更正** |

**probe 的 5 个对拍维度**（前4 项见 §2，第 5 项为本轮新增）：
| # | 维度 | 能抓什么 |
|---|---|---|
| ① | `legal_moves` 集合 | 分叉 |
| ② | `check` 布尔 | 分叉 |
| ③ | `applyUnchecked` 后完整棋盘 | **共错的移除逻辑**（本轮 P0-A 在此） |
| ④ |终局 `winner` + `resultReason` | 共错的胜负判定 |
| **⑤** | **`positionKey`** | **三回合计数口径分叉**（P0-E 同源） |

**测试 helper 建议**（S 级，GDD 与架构侧各踩一次同样的坑）：
```python
def state(*pieces, turn=Color.RED, profile="desktop_complete"):
    """建立测试局面。强制校验双方王不同列——
    否则 kings_facing 恒为 True，is_legal 会把所有走法判非法，
    使被测走法凭空消失（架构侧与 GDD 各踩一次）。"""
```

**若 F-10 认为 O-1 风险过高**，架构侧建议的折中方案（仍能防住共错事故）：
> 本迭代做 **O-2 + probe 扩 5 维 + 测试 helper + P0-E**，用测试把 O-1 的目标固化成可执行断言，O-1 排 v1.7。
> 理由：probe 扩 5 维后，**即使 in_check 尚未修复，跨引擎共错也能被立即发现**——这本身就是一层有效防护。

---

## 5. 与本轮其他工作的排期约束

- **GDD 的 O-8**（星点/环带/孤立子/偶数格 四处可视化）会改 `web/js/app.js` 与 `offline.js`。
- **架构侧 O-13**（拆 `app.js`）若同期执行，建议**先做 O-8 再拆**，避免刚写完的教学提示被重构冲掉。
- 架构侧的产物清理、maintenance 异常隔离、日志引入等与本轮**无文件重叠**，可完全并行。
