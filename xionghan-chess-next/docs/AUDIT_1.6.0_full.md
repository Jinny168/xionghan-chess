# 匈汉象棋 v1.6.0 全面审计报告

>审计角色：游戏研发工作室 · 制作人（主理人）
> 审计日期：2026-10-04
> 审计对象：`xionghan-chess-next` @ `67fabf6 1.6.0筹备`
> 审计维度：玩法与体验（游有方）+ 技术架构与工程质量（柯桥良）+ 制作人实测基线
> 回归红线：`pytest tests/ -q` = **108 passed**（迭代后必须仍全绿）

---

## 一、审计基线（制作人亲自实测，可复现）

| 项 | 实测值 | 取证 |
|---|---|---|
| git HEAD | `67fabf6 1.6.0筹备`，工作区干净 | `git log`/`git status` |
| 声明版本 | 1.6.0 | `pyproject.toml` |
| 仓库体积 | **1.9 G** | `du -sh` |
| 测试基线 | **108 passed / 38.34s** | `pytest -q` |
| v1.5.0→v1.6.0 | 187 文件，+1365 / **−20123** | `git diff --shortstat` |
| Python 核心 | 5505 行 | `wc -l` |
| Web 端 | 729 行（app.js 300 + i18n.js 244 + index.html 185） | `wc -l` |
| 规则开关 | **32 个**（17 行为 + 15 棋子显隐） | `profiles.py` |
| 棋子种类 | **14 种** | `rules.py` |
| profile | 4 个（desktop_complete/classic/web/traditional） | `profiles.py:199-227` |

### 代码卫生（正面）
- 裸 `except:` = **0**；`TODO/FIXME/XXX/HACK` = **0**
- 规则引擎**无状态可重入**（`apply_unchecked` 返回克隆，注释明言side-effect free）
- 胜负判定**5 级 elif 优先级链清晰**（`game.py:203-217`）
- 服务端并发正确：`asyncio.Lock` + AI 计算用 `asyncio.to_thread` 卸载（`rooms.py:359`），**无事件循环阻塞**
- 协议已统一：`PROTOCOL_VERSION=1`，17 种MessageType

---

## 二、P0 阻断项（3 项，均已实测确认）

### P0-1 服务端后台任务无异常隔离
**位置**：`service/app.py:36-42`
```python
async def maintenance() -> None:
    while True:
        await asyncio.sleep(5)
        for room in list(manager.rooms.values()):
            await manager.tick(room)      # 任一房间抛异常 → 整个后台任务死亡
            await manager.broadcast(room)
        await manager.cleanup()
```
**影响**：单个房间的异常会导致**所有房间**停止计时与广播，且无日志、无自愈。
**方案**：per-room `try/except` 隔离，异常日志带 `room_id`。

### P0-2 构建产物与规则源码副本污染版本库
**实测**：`git ls-files | grep -c "core/rules.py"` = **13**
- 历史发布版 1.0.0 ~ 1.5.0 各自的 `core/rules.py` 副本
- `archive/release-before-1.0.0/` 与 `build-onefile/` **未被 .gitignore 覆盖**
- 249 个 PNG 已入库（含根目录散落的 `desktop-*.png` 调试截图）
**影响**：① 仓库膨胀至 1.9G ② 规则修改时极易误改历史副本 ③ clone 成本高。
**方案**：`git rm --cached`（**磁盘保留，可逆**）+ 补全 .gitignore + 截图移`docs/assets/`。

### P0-3 规则引擎存在人工双实现
**位置**：`android/Resources/assets/offline/offline.js`（127 行）

JS侧用**逐方法镜像**方式重写了Python 规则引擎：

| offline.js | 内容 | Python 对应 |方法名对应 |
|---|---|---|---|
| :12 | `TYPES` 14 种棋子 | `model.py` PieceType | — |
| :13 | `NAMES` 红黑棋名 | `profiles.py` | — |
| :14 | `DEFAULT_OPTIONS` **18 开关硬编码** | `profiles.py:12-30` | — |
| :18 | `side()` 初始摆位 | `setup.py` | — |
| :21-27 | 4 个 profile 逐字段重定义 | `profiles.py:199-227` | — |
| :29 | `FEN_PIECES` 棋谱映射 | — | — |
| :32+ | `class Rules` 走法校验 | `rules.py` 34-494 | `diagonalPathPinched` ↔ `_diagonal_path_pinched` 等一一对应 |

**重要澄清（纠正此前的误判）**：三端**并非各自实现规则**。
- profile 选择**由服务端统一解析**（`rooms.py:104` `get_profile`），Web/桌面均从服务端拉取 → 规则唯一真相源在服务端
- 真正的第二份实现**只有 Android 离线副本**一处

**产品价值**：该副本是**服务器不可用时的降级兜底**（`MainActivity.cs:143/195/299` 触发同机pass-and-play），有真实价值，不能简单删除。
**治理方向**：薄壳化 —— 规则判定收敛到服务端，副本只做 UI 兜底；中期方案为「从 Python 自动生成 JS 规则表」。

**当前防护**：已有`scripts/offline_rules_probe.cjs`（31 行，vm 沙箱加载 JS 规则段）
+ `tests/test_cross_engine.py`（**仅 5 用例**：4 参数化初始局面 + 1 条 6 步序列），
实测 `5 passed`（node 在 PATH，**未skip**，门禁真实生效）。
**缺口**：未覆盖 14 类棋子手工局面、18 开关组合、和棋边界。

---

## 三、P1 问题清单

| ID | 问题 | 位置 | 影响 |
|---|---|---|---|
| P1-1 | `_patrol` 硬编码 `row not in {5,7}` | `rules.py:445` | 13 棋盘专属；traditional 10×9 无PATROL 故不出错，但语义不显式 |
| P1-2 | `_nearest_archer_star_distance` 用 `max(rows, cols)` 当搜索上限 | `rules.py:385` | 语义不清晰 |
| P1-3 | 未使用参数（`piece` 传入未用） | `rules.py`多处 | 签名噪音 |
| P1-4 | **`test_game.py` 仅 1 个用例**，而 `game.py` 含 5 级胜负判定 + 3 类和棋 | `tests/test_game.py` | 覆盖严重不足 |
| P1-5 | **「巡」PATROL 零测试覆盖**（14 类中唯一） | `tests/test_rules.py` | 实测 `grep` 确认 |
| P1-6 | 32 开关仅少数被变体测试触及 | `tests/` | `RuleProfile(` 显式构造 0 次；`test_profiles.py` 测的是**键名映射层**，非走法行为层 |
| P1-7 | i18n 未收尾：`web/js/app.js` **41 处中文硬编码** | `app.js` | 英文界面下棋子规则说明显示中文；桌面端另有 8 处 |
| P1-8 | 广播全量推送：`broadcast()` 每次 `room.snapshot(token)`含 replay | `rooms.py:406-415` | 长对局广播体积累积 |
| P1-9 | 明文流量：`usesCleartextTraffic="true"` | `AndroidManifest.xml:4` | 安全 |
| P1-10 | 根目录 README 严重过期 | `README.md` | 仍描述 v2.0「PyGame + Flask」旧架构，与当前「PySide6 + FastAPI + .NET Android」不符 |

---

## 三·五、规则层 P0（创意总监审计 + 制作人独立复现）

> 复现方式：制作人编写临时脚本在内存中构造局面直接调用 `RulesEngine`，
> **脚本已删除，未留在仓库**。以下为真实输出。

### ✅ P0-R1 甲（ARMOR）连线吃王，全程无将军提示
构造：红甲(6,3) + 红相(6,5) + 黑王(6,6)，红走 6,3→6,4
```
in_check(BLACK) before any move : False
armor 6,3->6,4 pseudo_legal    : True
black king still on board      : False     ← 王被吃
captured_by_move               : [('king', 'black')]
```
**根因**：`rules.py:192-202` `in_check` 仅以 `pseudo_legal(opponent, Move(king_pos))` 试吃，
而甲的连线吃在 `apply_unchecked:164-168` 才发生，`_armor` 验证器（:435-436）无法感知。
**后果**：对局在**沉默中结束**，玩家看不到任何将军/将死提示 —— 属规则实现与文档不一致
（`PIECE_RULES.md` 已写明甲可吃王），修复不违背「不擅改规则」约束。

> **已修复（2026-10-04 晚，提交 `bb26c68`）**：`in_check` 追加一次间接威胁扫描，
> 候选落点按甲/刺各自规则收紧（甲须与王同线且相距 1~2 格、刺只有一个镜像格），
> 再统一回放 `apply_unchecked` —— 与执行移除的是同一段代码，所以不会长出甲/刺规则的第二份副本。
> 修复后上述复现场景 `in_check(BLACK)` 由 False 变 True，对照组保持 False。

### ✅ P0-R2 刺（ASSASSIN）兑子吃王，刺同时消失
构造：黑王(5,4) + 红刺(5,5)，红走 5,5→5,6
```
in_check(BLACK) before         : False
black king still on board      : False
captured_by_move               : [('king', 'black')]
```

### ✅ P0-R3 刺兑子绕过 SHIELD 保护
构造：黑盾(6,3) + 黑兵(6,4) + 红车(5,0) + 红刺(6,5)，红刺 6,5→6,6
```
is pawn protected by shield    : True
ROOK eats protected pawn       : False     ← 直吃被正确拦阻
protected pawn removed anyway  : True      ← 但刺兑子照样吃掉
```
**裁定**：这是**真规则冲突**（`PIECE_RULES.md` 明写刺"不能吃被盾保护的棋子"），
但修法涉及玩法裁定 → **本轮只补测试固化现状 + 记入 audit，修法留 v1.7.0 由产品拍板**。

### ⚠️ P0-R4 / P0-R5 待复现
复活写谱（缺 `RESURRECT` 谱条）与终局后复活，首版构造未触发路径，
已交由主程序用更精确路径（先形成 `captured[RED]` 池再走复活）复现。

### ✅ P0-E `position_key` 漏掉升变素材池 → 三回合计数误判和棋
**制作人独立复现**（构造：黑王(0,6) / 红王(12,3) 异列 + 红兵(1,0)，只改素材池）：
```
池空        兵→(0,0) 合法走法 = [(0,0,None)]
池有车      兵→(0,0) 合法走法 = [(0,0,'rook')]
池有马      兵→(0,0) 合法走法 = [(0,0,'horse')]

moves 池空 vs 池有车  不同 = True   position_key 相同 = True
moves 池有车 vs 池有马 不同 = True   position_key 相同 = True
```
**根因**：`rules.py:210-212` 的 `position_key` 只吃 `(color, type, row, col) + turn`，
**完全不含 `captured`**。而升变是唯一「不改变棋盘、但改变合法走法集合」的状态变量
—— 池里是车就只能升车。**且比"能否升变"更严重：池决定"升变成什么"，
即整个升变目标集被漏掉。**

**后果**：三回合计数把**规则上不等价的局面**判为同一局面 → 误判和棋。
属「用户会感知的结果错误」，且**无法自查**（对局中无人察觉，直到判和那一刻）。

**修法约束（关键）**：追加素材池的**类型多重集**，
**绝不可追加 `Piece.id`** —— id 每次生成都不同，会导致 `position_key` 永不相等、
**永远判不了和棋**，那比现在更糟。

**跨端同步**：`offline.js` 的 `positionKey` 有 2 处命中（三回合计数逻辑本身被镜像），
**必须同步**，否则两端合计数分叉。

---

## 三·六、本次审计的「集体误判」记录（方法论价值）

审计过程中，**制作人与两名成员各踩一次同一类错误**：摆子不当导致误判。

| 成员 | 误判 | 根因 |
|---|---|---|
| 创意总监 | 误报「升变导致子力膨胀」为 P0 | 摆子只放 1 个兵、无合法着法 → 误读空列表 |
| 技术架构总监 | 一度认为 GDD 的 P0-E 无法复现 | 双方王同在第 6 列 → `kings_facing` 为 True → `is_legal` 全 False |
| 制作人 | 误判「池空不给升变是正确守恒」 | 同第一类：把空列表误读为 bug 缺失 |

**由此固化为团队纪律**（已写入 R-7 交付要求）：
1. 摆子类测试：**双方王必须异列**，否则 `kings_facing`（`rules.py:491-494`）返回 True，`is_legal` 全 False
2. 摆子类测试：至少 2 个王 + 1 个待测子，且待测子必须在**有合法着法**的位置
3. 统一抽 `tests/helpers.py` 的 `make_board()` 供所有摆子类测试复用

**另一条元教训**：「跨引擎对拍只能防**分叉**，不能防**共错**」——
本次 4 个 P0（R-1/R2/R3/E）**全部是两侧同时错**，对拍全程绿灯。
根因是对拍维度不足（仅 `moves` + `check`）。故 R-5 扩维是本轮**最高性价比**的投入。

---

## 四·五、第二次集体误判：「升变套利」也是误报

创意总监自查后**主动撤回**了「送车白赚 1 兵」这个 P2 战术悖论，理由是**升变池供给有界**：

```
若 A（10）吃掉 B 的车（8），B 的被吃子池只增加一个「车」素材（按类型，不按子力）
→ B 升变消耗 1 兵 + 1 车素材 = 回收 8-1 = 7 点，而 B 先损失了 8 点
→ 净亏 1 点，与「送车白赚 1 兵」相反
```
**结论成立**：升变是**固定成本（1 兵）的素材回收**，供给受「已阵亡子数」约束，
**不存在无限增子**。我复核确认此撤回正确。

**方法论价值**：这与上节的「摆子误判」同源 ——
**在缺少边界条件（王异列 / 升变池有界）时做的推演都会失真**。
两次误判方向相反（一虚报 bug、一漏报 bug），但根因相同。

## 四·六、技术架构总监的两处纠正（我均已实测确认采信）

### 1.「送车白赚 1 兵」第二次算错：升变等式把「素材成本」重复计了一次
游有方第二次修订给出的等式是 `+8 −(8−1) = +1`（即「白赚 1 兵」），
柯桥良指出这**把升变素材的成本重复计算了**：

```
兵(1,0) 底线升车 → 兵消失(+1)、车出现(−8)  → 自身−7
                  → 车素材入池(+8) → 池素材当8 点用
                  → 再升变时兵消失(+1)、车出现(−8) → 自身再 −7
```
**正确算法是「等量回收」**：素材入池应记为**负债 −8**，
使用时释放负债 +8，两者相消，**总净 = −7（升变一次的总代价）**。
**正确结论是「送车反而净亏 7 点」，不存在任何套利。**
我复核：升变的净收益就是「目标子力 − 兵(1) − 池中已消耗的素材净值」，
在**等量回收下净 = −7**，与游有方第二次结论相反。**柯桥良正确。**

### 2. AI 升变估值 800 应为 900（会导致实现走偏的陷阱）
实测 `ai.py:46-53` 与 `ai_see.py:84-87`：
```
VALUES[PieceType.ROOK] = 900   VALUES[PieceType.PAWN] = 120
_promotion_gain = values[promotion] - values[PieceType.PAWN]   # 车 900−120 = 780
```
**780 已扣掉兵的价值。** 游有方原始描述中的「800 − 120 = 680」对应错误的 800 估值。
**若按 680 写测试期望/实现，会引入 20 分误差** —— 已转达主程序纠正。

**这两条的意义**：升变机制是本项目最复杂的规则（素材池 + 兵消耗），
**是全项目最容易被"算错"的地方**。三次修订才收敛，说明它值得专门的测试覆盖。

---

### P0-F AI 评估缓存以漏池的 key 为键（R-8，最高优先）
**实测确认**：`ai.py:361-365`
```python
def _evaluate(self, game: Game, color: Color) -> float:
    cache_key = (game.rules.position_key(game.state), color)   # ← 漏池的 key
    cached = self.evaluation_cache.get(cache_key)
```
且 `_evaluate` 的计分循环（`ai.py:367-371`）只累加 `state.pieces`，同样不读素材池。

**影响范围（精确版，已实测确认 `evaluation_cache` 生命周期）**：
- `ai.py:118-124` 显示 `evaluation_cache.clear()` 在**每次搜索开始时**执行
  → 缓存**不跨搜索存活**，仅在一次 `search()` 内复用
- ❌ **不构成**「跨局棋力污染」
- ✅ **构成**：「同一次搜索内」两次到达同布局但升变池不同的局面 → 缓存碰撞
  → 置换表/剪枝会重复访问同一布局，实战中升变消耗素材后池会变，**同一搜索内完全可能命中**

**为何仍必须修**：`position_key` 服务的**不只是** `_evaluate` 复用 ——
`game.py:215` 的三回合计数用它判和（**这是 P0-E 的真实 bug**）。
AI 缓存这条是「顺手免疫」：若将来 `_evaluate` 要把「可升变的车」计入子力，
漏池的 key 会立刻变成真 bug。**故 R-8 的核心价值是修 P0-E。**

### P0-G AI 静态估值不感知「升变潜力」（技术架构总监报，实测确认）
`_evaluate` 源码实测（45 行）：
```
含 'captured' 字样 : False
含 'piece_type' 字样: False
```
**它连 `piece_type` 都不读**，只按 `PieceType` 查 `VALUES` 表、算位置分与中心分。
故 AI **完全不感知「我还有兵可以升变」**：
- 兵到底线前，AI 认为它只值 120
- 升变后棋盘上出现车，AI 认为值 900
- 但 AI **从未把「我有升变权」计入估值** → 兵该不该冲底线与真实收益脱节

**与 P0-F 的关系（关键区分）**：
- **P0-F 是「键」的问题** → 修 `position_key` 即可，零平衡影响
- **P0-G 是「值」的问题** → 改 `_evaluate` = **估值口径变更 = 新平衡问题**

**分层结论（避免笼统说「AI 漏算」）**：
| 层 | 素材池感知 | 状态 |
|---|---|---|
| `rules.captured_by_move`（`rules.py:143-150`） | ✅ 准确 | 已正确实现甲连线/刺兑子间接吃子 |
| `ai_see.py:23-24` SEE 层 | ✅ 准确 | `sum(values[piece.type] for piece in captured)` |
| `ai._evaluate`（`ai.py:361-405`） | ❌ **缺失** | 只读 `pieces`，漏升变潜力 |

**本轮裁定（制作人）**：
- ✅ 修 `position_key`（R-8）—— 因 `game.py:215` 三回合计数**真的读它**，是 P0-E 真实 bug
- ✅ 加 `test_ai_paths_never_mutate_state_captured` 护栏（R-9a）——
  把「AI 只读不写素材池」这个**隐式约定变成可执行护栏**（实测当前 `ai_see.py:23/42/65`
  的 `captured` 均为局部变量，安全）
- ❌ **不改 `_evaluate` 估值**（R-9b 延期 v1.7.0）——
  **理由：v1.6.0 的 master 棋力基线尚未建立**（VERSION_PLAN 记为"50 局非截断对弈未完成"）。
  **在基线缺失时改估值，会让后续棋力验收失去参照系。**

---

## 四、已确认修复的项（正面）

- **F-9 衍生缺陷疑似已修复**：`pending_undo_offer` 在 `game.py:75/131/165` 三处正确清除；`revision` 在 `rooms.py` 有 6+ 处递增
- **版本倒挂已消除**：M0 已 `git rm --cached` 2.0.0 孤儿发布树（147 文件）
- **master 档已接入**：纯 UCB1 MCTS，50 局筛查单步均 0.417s（但均为 2 ply 截断局，**正式胜率未验收**）
- **防漂移门禁已建立且生效**：`test_cross_engine.py` 实测 5 passed
- **AI 性能可控**：单步 1.2s（master/hard），桌面端已用 `AIWorker(QRunnable)` 异步

---

## 五、本次迭代范围裁定

### 5.1 关键决策：R-1 必须「双写」而非单改Python
制作人已实测确认：`offline.js` 的 `inCheck` 与 Python `in_check`（:192-202）**逐行等价**，
且 `armorCaptures` 只在 `applyUnchecked` 内被调用，`inCheck` 同样看不到它。

**因此：若只改 Python 的 `in_check`，分叉会从 0 处变成 2 处 —— 亲手制造刚建立的门禁要防的漂移。**
这使 R-1 从「后置项」升为**发布门槛**：R-1a（Python）与 R-1b（offline.js）**必须同批次交付**。

### 5.2 对拍门禁的能力边界（技术架构总监主动纠正）
「等价性测试只能防**分叉**，不能防**共错**」——
P0-R1/R2 这类漏洞两侧**同样错**时，对拍会显示绿色。
故R-1a 修完**必须再加 3 类黄金用例**（`test_p0_rules.py`）断言期望值本身，
否则测试仍会给假绿灯。对拍维度同步从 2 维扩到 5 维
（`legalAll` / `inCheck` / `capturedByMove` / `checkmate` / `stalemate`）。

### 5.3 本轮做（v1.6.0 收口）
| ID | 内容 | 理由 |
|---|---|---|
| **O-1** | maintenance 异常隔离 | P0，改动极小、风险极低、收益明确 |
| **O-2** | rules.py 魔法数字提取 + F841 | P1，行为等价零风险 |
| **O-3** | 仓库卫生清理 | P0，已积累 1.9G，且规则副本有误改风险 |
| **O-4** | 跨引擎等价性测试补全（含「巡」） | P1，低成本高回报 |
| **R-1a/b** | 将军判定纳入间接吃子（**双写**） | P0，已复现，**发布门槛** → **已交付**（`bb26c68`，Python + offline.js 同批） |
| **R-2** | 补 `test_game.py` 覆盖 | P1，1 用例 vs 5 级胜负链 |
| **R-3** | 补「巡」PATROL 单元测试 | P1，14 类唯一零覆盖 |
| **R-4** | 刺兑子绕过盾 | P0，与文档直接冲突的 bug，**零跨端同步成本** |
| **R-5** | 对拍维度 2→5 | S 级，让 R-1a 在 JS 侧同步被测 → **已交付**（探针增 `capturedByMove` / `checkmate` / `stalemate` 三腿，`check` 腿支持显式 `checkFor`；全量 151 passed） |

### 5.4 明确不做（留 v1.7.0+）
| ID | 内容 | 理由 |
|---|---|---|
| O-5 | offline.js 薄壳化 | 触及产品降级路径，需完整测试预算，单独版本做 |
| O-6 | 统一 `capturable_squares` | **L 级跨三端**；R-1a 已覆盖 P0 症状（`rooms.py:320-325` 漏间接吃子随之解决） |
| O-7 | 广播增量推送 | 性能优化，需压测基线，非阻断 |
| O-8 | F-5 安全加固 | 涉及部署形态与文档，需先定生产拓扑 |
| O-9 | i18n 收尾（41 处） | P2；且**需**先重译 `PIECE_RULES.md`（E-02），否则会固化错译 |
| O-10 | 规则语义调整（C-01~C-12） | `VERSION_PLAN_1.6.0.md:82` 明确「不擅改规则」，需产品拍板 |
| O-11 | master 正式棋力验收 | 需 50 局非截断完整对弈，属独立验收任务 |
| O-12 | README 全面重写 | 工作量 M，改前应先合并 `xionghan-chess-next/README.md` |

### 5.5 范围蔓延风险控制
初版审计的 7 项一度膨胀到 16 项。本轮最终锁定 **9 项**（上表 5.3），
砍掉 3 项规则语义改动、2 项重写类任务，理由均为「需产品拍板」或「应独立版本做」。
**裁定原则**：本轮只做「改动可控 + 收益明确 + 不改产品行为」的项，
对齐 1.5.0→v1.6.0 净减 18758 行的克制基调，守住 108 passed 红线。

---

## 六、制作人实测推翻的两个流传错误

审计过程中发现两处「项目内部长期流传但与代码不符」的认知，已用实测推翻：

### 6.1 星点是 **13 个**，不是 25 个
**实测**（直接调用 `archer_star_points(get_profile('desktop_complete'))`）：
```
星点数: 13
坐标: (0,0) (0,6) (0,12) (3,3) (3,9) (6,0) (6,6) (6,12)
      (9,3) (9,9) (12,0) (12,6) (12,12)
```
`rules.py:18-27` 的 `(row//3 + col//3) % 2 == 0` 在 5×5 索引网格（0/3/6/9/12）上筛出
**13 个菱形点**，并非 25 个（25 需要 `(row//3)%2==0 and (col//3)%2==0`，是另一种算法）。
**以代码为准**：13 个，成菱形/棋盘对称。

**订正记录（2026-10-04 下午二次复核）**
1. 本审计初稿称「`handoff.md:9` 与项目记忆均记载 25 个星点」——**引用有误**。
   `handoff.md` 全文 grep「星点」「25」均 0 命中，`:9` 实为「## 2. 初始目标 & 需求范围」标题行。
   「25 个星点」这一说法的来源是项目记忆而非仓库文档。
2. 初稿称「`docs/PIECE_RULES.md`、`docs/RULES.md`、`HELP.md` 需同步订正」——**这个方向是错的**。
   复核结果：两份 `PIECE_RULES.md`（`docs/` 与 `src/xionghan_chess/desktop/resources/docs/`）
   的 `:66-67` 都写的是「有效星点以 3 格为间距，并按交错棋盘格分布……仅保留行列索引和为
   偶数的点」，`docs/RULES.md:20-21` 写的是「交错棋盘格分布；只绘制至少属于一条有效斜轨的点」，
   **三者描述的都是 13 点，本来就是对的，无需订正**；`docs/HELP.md` 全文无「星点」字样。
3. **真正的 25 点实现在代码里，且只有一处**：`web/js/core/game-rules.js:809`
   （`if (r % 3 === 0 && c % 3 === 0)`）与 `:759`（强化模式吃子门槛）。
   该处 `_findNearestStarPointDistance` 按 25 点判定，而同目录
   `web/js/ui/chess-board-renderer.js:752-758` 的渲染常量画的是 13 个——**Web 端自己自相矛盾**，
   且与 `rules.py` / `offline.js` 两侧的真分叉。详见 6.3。

#### 6.1 补记（2026-10-04 晚）：那份 25 点文件**不在活体的依赖链上**，C-2 由此收口

本节 3 的事实（外层 `web/js/core/game-rules.js` 用 25 点）仍然成立，但它**不影响任何实际渲染**。
四条实测证据：

| # | 实测 | 结论 |
|---|---|---|
| 1 | `service/app.py:34` `WEB_DIR = Path(__file__).resolve().parents[3] / "web"` 运行期解析为 `xionghan-chess-next/web`（**内层**），`WEB_DIR/'js'` 只有 `app.js`、`i18n.js`，`js/core` 不存在；服务只挂载 `/assets`、`/css`、`/js` 三个前缀，全部指向内层 | 外层 `web/**` 无法经 HTTP 抵达 |
| 2 | 外层 `web/index.html` 全文仅 1 个 `<script>`，是内联背景图脚本，**无 `src`**；外层 `web/game.html:350` 的确加载 `js/core/game-rules.js`（行号引用准确，共 23 个 script 标签），但它在静态目录之外，直接访问 `/game.html` 也会 404 | 活体入口页不加载该文件 |
| 3 | 活体树全量扫描（js/html/py/json/md/cjs/cs/ps1/bat/yml/toml）中，内容出现 `game-rules.js` 或 `web/game.html` 的**只有本文档自己**，无构建、无部署脚本、无入口引用 | 它是迁移前的历史快照，不是活代码 |
| 4 | 活体侧三条链路**本来就都是 13 点菱形**：`rules.py:26` 过滤 `(row//3 + col//3) % 2 == 0` → `public_state["profile"]["archerStarPoints"]`；`web/js/app.js:180 drawStarPoints()` 直接读该字段作画；`offline.js:20 starPoints()` 用同条件 | C-2「按代码 13 个菱形」在活体侧**已满足** |

**处置**：C-2 判定为 **✅ 已完成（无需改代码）**。不再按原计划去改
`web/js/core/game-rules.js:759/:809`——改它既不会到达浏览器，又会让它与历史快照产生无意义的分叉。
改为新增回归测试 `tests/test_rules.py::test_archer_star_points_are_thirteen_diamonds_not_twenty_five`
把活体侧的 13 点菱形钉死；该测试经变异测试验证敏感（把 `rules.py:26` 的过滤临时改成恒真，
用例立即失败并把 `test_archer_invalid_star_is_not_a_strong_mode_attack_origin` 一并带崩）。

#### 6.1 收口后的含义

「3 套引擎」的表象要降一档：**活体只有 2 套**（Python 权威 + offline.js 镜像），
`web/` 的第三套是历史遗留，仅在 file:// 直接双击 `web/game.html` 时才可能跑到。
规则同步成本仍是「改 2 处」，治理重点依旧是 offline.js。详见 6.2 / 6.3。

### 6.2 不是「三端各自实现规则」，而是「2 套引擎 + 1 套投影」
项目一贯强调「三端完全独立实现」。**实测**：

| 端 | 规则实现 | 证据 |
|---|---|---|
| 服务端 / 桌面 | `core/rules.py` | 唯一权威引擎（14 种棋子） |
| **Android 离线** | `offline.js` | **第二套真引擎**（127 行人工镜像，14 种棋子） |
| **Web 端** | **第三套残缺引擎** | `web/js/core/game-rules.js`，**仅 9/14 种棋子**，见 6.3 |

> **订正记录（2026-10-04 下午）**：初稿称「Web 端零规则、判定全在服务端」——**这个结论是错的**。
> `web/game.html:350` 显式加载了 `js/core/game-rules.js`，该文件提供 9 个 `isValidXxxMove`
> （Ju/Ma/Xiang/Shi/King/Pao/Pawn/She/Lei），并由 `:130-173 isValidMove` 按棋子类型分发。
> Web 端确实存在本地走法判定，不是纯投影。相应地，初稿「同步成本是改 2 处而非 3 处」的
> 结论一并作废——实际是 **3 套引擎**（Python 权威 + offline.js + game-rules.js）。

**含义（修正后）**：修复规则时的同步成本是「**改 3 处**」，其中 Web 端只覆盖 9/14 种棋子，
因此它的缺口不是"同步"而是"补齐"。治理重点仍是 offline.js 一处（14 种全量镜像）。

### 6.3 第三套引擎：`web/js/core/game-rules.js` 覆盖 9/14 棋子

| 项 | 内容 |
|---|---|
| 入口 | `web/game.html:350` 加载；`game-rules.js:130-173 isValidMove` 按类型分发 |
| 已实现 | Ju 车 :184、Ma 马 :221、Xiang 象 :281、Shi 仕 :385、King 王 :421、Pao 炮 :547、Pawn 兵 :593、She 射 :712、Lei 檑 :822 |
| **缺失** | **Jia 甲（armor）、Ci 刺（assassin）、Dun 楯（shield）、Wei 尉（guard）、Xun 巡（patrol）** —— 源码 `:169` 自注释「已移除: Jia, Ci, Dun, Wei, Xun」 |
| **已知分叉** | 星点判定用 25 点（`:809` `:759`），Python/Android 用 13 点菱形 |

**这一条推翻了初稿 6.2 的核心结论**，也是「三端完全独立实现」这句项目信念在 Web 端仅存的一处真实体现
（Python 与 offline.js 虽是双实现，但都是 14 棋子全量；只有 Web 端是半套）。

> **对拍方法论警示**：这次用「射在星点 (3,3)」做对拍时，强弱模式结果相同，差异被聚合比对吃掉了；
> 换到非星点 (4,4) 才暴露。`tests/test_cross_engine.py` 的 `expected_targets` 单子目标集断言
> 必须保留，不能退回只做全集比对。

### 6.4 对拍用例 10 个红的根因：测试通道丢 `options`，不是引擎分叉

主程补的 11 个跨引擎对拍用例中，10 个当时为红。经制作人独立复现，**根因全部在测试通道，
两侧引擎逻辑一致**。

**根因**：`tests/test_cross_engine.py:44-56` 的 `_offline_result()` 这样下发选项：

```python
"options": game.state.to_dict().get("options", {}),
```

而 `src/xionghan_chess/core/model.py:112-137` 的 `GameState.to_dict()` 输出的是
`profileId/turn/pieces/history/captured/winner/...`，**不含 `options` 字段**
（整个 model.py  grep `options` 命中 0），于是 `.get()` 恒返回 `{}`。
`scripts/offline_rules_probe.cjs:23` 收到空 options 后退回 profile 默认档，
使 `archer_enhanced_mode`、`horse_straight_three`、`elephant_can_cross_river`、
`pawn_fast_move_before_enemy_territory`、`king_can_leave_palace` 等所有 toggle 用例必然分叉。

**实测对照**（射置于 (4,4)，`archer_enhanced_mode=True`）：

| 通道 | JS 侧给出的目标数 |
|---|---|
| 现有通道（options 空） | 3 |
| 补传 `asdict(game.rules.options)` | **12**，与 Python `equal: True` |

**结论**：`offline.js:58` 的 `archer_enhanced_mode` 分支本来就是对的，**不需要为「射」改 JS**；
修复点只有测试通道一处。若当时据此去改 offline.js，会把一个正确的实现改坏。

> **纪律沉淀**：这是本轮第 5 次出现「引用他人结论未复算」。涉及引擎对拍的结论，
> 必须先跑一遍真实通道再下判断；修复前要先验证「移除该缺陷后问题是否真的消失」，
> 而不是找到一个可疑点就直接改。

---

## 七、需用户拍板的决策项（本轮不擅改）

| ID | 决策 | 背景 | 取舍 |
|---|---|---|---|
| **复活** | ✅ **已拍板：补完，不是摘掉规则** | 初稿依据「UI 无入口」降级 P1-C，**依据有误**：`web/js/app.js:224` 的 `#resurrectButton` onclick 真绑着 `send('resurrect',{row,col})`，协议/服务端/桌面/Web 四段全通 | 落地=`core/game.py:146-165` 补 history + 终局判定 + position_counts + 出生行去硬编码；`offline.js` 补 `resurrectPawn`；`web/app.js:224` 与核心同源 |
| **C-2** | ✅ **已完成：活体侧本就是 13 个菱形，无需改代码** | 初稿以为不一致在文档，实测不一致在 `web/js/core/game-rules.js:759/809`（25 点）；复测发现该文件的静态目录在活体之外（服务 `WEB_DIR` 指向内层 `web/`，`/js` 无 `js/core`），改它到不了浏览器；见 6.1 补记 | 落地=**不做**代码改动，改为加回归测试 `test_archer_star_points_are_thirteen_diamonds_not_twenty_five` 钉死活体 13 点菱形；Python 与 offline.js 不动。遗留文件 `web/js/core/game-rules.js` 保留为历史快照，不归档删除（避免 228 条 tracked path 的破坏性改动） |
| **C-1** | 夹逼是否拦「根线」第一格 | `rules.py:407-422` 从 `range(distance)` 循环含起点格，而 `_rook`/`_cannon` 的 `_clear` 从第二格起 | 越线夹击/夹逼的判定口径 |
| **C-3** | 「炮」是否改读夹击类定义 | 文档说读「本方任一棋子」，实现是标准隔一子炮 | 传统象棋玩家的认知适配 |
| **C-4** | 「甲」三子连线可斜可直 | `rules.py:466` 含 4 个方向 | 连线方向的取舍 |
| **C-5** | 「刺」是否受「路被护子完全阻断」限制 | 文档明写该限制，实现**完全没有** | 文档与实现冲突，需择一 |
| **C-6** | 「兵卒到底线四向移动」是否等于「将」限制 | `rules.py:322-323` + `profiles.py` 开档 → 兵到底线即可获胜 | 胜势膨胀 |
| **C-7** | 「象」是否受「象眼被阻则整条斜线不可走」约束 | `rules.py:255-277` 只查象眼，未查路径 | 文档明写该限制 |
| **C-8** | 无进展和棋阈值 | 硬编码 120 ply 而非可配置 | 长局体验 |
| **C-9** | 单方无「主动认输」按钮 | 请求 `resign` 返回 `error.resignUnavailable` | 交互缺口 |
| **C-10** | 无 AI 悔棋/认输组合按钮 | 需连点两次，易误触 | 交互缺口 |
| **C-11** | 单方在线 1200ms | 与本地离线不一致 | 体验一致性 |
| **C-12** | 32 个开关缺 14 个（`invasion_victory` 等）的 UI 与文案 | 规则层与 UI 层不对齐 | 规则透明度 |

---

## 八、审计方法说明

- 本报告所有数字均来自制作人**亲自执行的命令**或**亲自 Read 的文件**，非成员转述
- 成员间的行号引用已交叉复核（发现并修正了技术架构总监 3 处行号偏差）
- 对创意总监报的 5 个 P0 规则漏洞，制作人独立编写临时脚本在内存中构造局面复现：
  **3 个确认成立**（P0-R1/R2/R3），2 个待主程序用更精确路径复现
- 临时验证脚本已删除，仓库保持干净


