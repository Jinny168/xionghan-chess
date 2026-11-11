# 匈汉象棋 v1.3.0 全栈审计与安卓重构方案

> 角色：资深跨端棋牌测试 & 全栈开发审计工程师
> 范围：仅 `xionghan-chess-next/`（桌面 PySide6 / Web FastAPI+JS / Docker / 安卓 .NET9 WebView）
> 基准：`docs/QA_v1.3.0.md`（含 QA_REPORT + QA_REMEDIATION + QA_AUDIT + QA_AUDIT_REMEDIATION + DELIVERY 五段）+ 本次代码全量复核
> 编写时间：2026-08-13
> 约束：不自行修改游戏规则；安卓独有问题与多端通用问题分开记录

---

## 交付物一：QA 审核报告逐条缺陷汇总清单

### 1.1 总览统计（源自 QA 报告 + 本次复核）

| 状态 | 数量 | 占比 | 说明 |
|------|------|------|------|
| ✅ 已修复 / 确认无需修改 | 26 | 55.3% | 代码验证通过，含 64 项自动化测试全绿 |
| ⏳ 等待规则确认 | 4 | 8.5% | C-01/C-03/C-04/C-11/C-12，会改规则，未自行修改 |
| 🧱 架构限制保留 | 1 | 2.1% | A-01 离线 JS 引擎 vs Python 等价性 |
| ⚠️ 未修复（低优先级） | 16 | 34.1% | 不影响核心功能，保留合理 |
| 🆕 本次审计新发现 | 3 | — | 双击音效、统计重复计数、离线错误串未国际化（见交付物二/四） |
| **合计（QA 原始）** | **47** | 100% | C-15 / S-15 / W-8 / A-9 |

**阻断级（P0）已全部修复**：S-01/S-02/S-03/S-06/A-02；高优先级（P1）S-04/S-05/S-07/S-13 全修。**当前无阻断级遗留**，上线风险集中在"需手动验证的桌面端联机场景"与"本次新发现的双击音效"。

### 1.2 仍需处理项逐条清单（未修复 / 待确认 / 架构限制）

| Bug ID | 终端 | 严重 | 状态 | 代码位置 | 根因要点 | 修复建议 | 回归要点 |
|---|---|---|---|---|---|---|---|
| C-01 | Core(三端) | 中 | ⏳待规则确认 | `core/rules.py:432-438` | PATROL 行号硬编码 `{5,7}`，依赖 13×13 | 与产品确认 PATROL 在 9×10 traditional 档案的巡线定义后再改 | traditional+PATROL 走法不崩 |
| C-02 | Core(三端) | 低 | ✅二次已修 | `core/rules.py:117-129` | `legal_moves()` 漏升变 | 已枚举升变类型（二次审计修） | 升变着法不遗漏 |
| C-03 | Core | 低 | ⏳待规则确认 | `core/rules.py:331-334` | GUARD 跳板不区分敌我 | 与产品确认 GUARD 跳板阵营规则 | — |
| C-04 | Core | 低 | ⏳待规则确认 | `core/rules.py:447-450` | SHIELD 切比雪夫距离斜对角保护 | 与产品确认保护范围 | — |
| C-06 | Core | 中 | ⚠️未修复 | `core/ai.py:233-267` | `_tactical_moves()` 对 ARMOR/ASSASSIN 生成全盘 169 位置 | 增加位置裁剪（仅生成与己方/敌方棋子相关的战术走法） | 多 ARMOR 局面 AI 思考 ≤ time_limit×2 |
| C-10 | Core | 低 | ⚠️未修复 | `core/storage.py:30` | 仅接受 formatVersion==1，无版本兼容 | 预留版本协商（当前不影响） | 未来 v2 旧棋谱可迁移 |
| C-11 | Core | 中 | ⏳待规则确认 | `core/game.py:183-198` | 无长将/长捉检测 | 与产品确认责任方与处罚方式 | AI 不无限长将拖延 |
| C-12 | Core | 低 | ⏳待规则确认 | `core/game.py:200-206` | 13×13 大棋盘 120 步阈值可能过早 | 与产品确认大棋盘阈值 | 大棋盘调动型对局不误判和 |
| C-13 | Core | 中 | ⚠️部分缓解 | `core/game.py:36-43` | `_snapshots` 无上限 | 增加上限或滚动窗口（联机复盘已靠 `replay` 恢复） | 300+ 回合内存 <50MB |
| C-15 | Core | 低 | ✅二次已修 | `core/protocol.py` | protocolVersion 不校验 | 已限制为版本 1，不兼容以 1002 关闭 | — |
| A-01 | 安卓离线 | 严重 | 🧱架构限制 | `offline.js` vs `core/rules.py` | 离线 JS 引擎独立实现，无等价性测试 | 建立离线/在线规则等价性自动化测试（长期） | 同一走法离线/在线判定一致 |
| A-04 | 安卓 | 中 | ✅二次已修 | `MainActivity.cs:73-96` | 沉浸模式异常静默吞掉 | 已写 Logcat，不再静默 | MIUI/ColorOS 可诊断 |
| A-05 | 安卓离线 | 中 | ✅复核无需改 | `offline.js:99` | 翻转坐标空间 | 二次审计确认 `viewPos()` 显示 + `boardPosition()` 输入同逻辑空间 | 翻转拖拽命中正确 |
| A-06 | 安卓离线 | 低 | ⚠️未修复 | `offline.js:97-98` | `geometry()`/`syncCanvasSize()` 每次 draw 重算 + 多重监听 | 合并计算，单一 ResizeObserver | 低配设备渲染压力 |
| A-08 | 安卓 | 低 | 🧱保留 | `AndroidManifest.xml:3` | cleartext HTTP | 用户自建局域网服务器所需，保留并仅申请 INTERNET | 生产 HTTPS |
| A-09 | 安卓 | 低 | 🧱保留 | `csproj:11-12` | Trim/AOT 关闭 | 影响 WebView bridge 反射保留，未验证真机矩阵前不开 | — |
| W-03 | Web | 低 | ⚠️未修复 | `app.js:28` | `data-background` 冗余值 | 无功能影响，保留 | — |
| W-05 | Web | 低 | ⚠️未修复 | `app.js` | Audio/Map 资源清理不完整 | 长生命周期设计，低影响 | — |
| W-06 | Web | 低 | ⚠️未修复 | `app.js:239` | 浅拷贝冗余代码 | 无功能影响，保留 | — |
| W-07 | Web | 低 | ⚠️未修复 | `app.js:213` | `prompt()` 同步阻塞 | 边界场景，保留 | — |
| NEW-01 | Core(联机) | 低 | ✅二次已修 | `core/game.py:71` | 走棋后未清 `pending_undo_offer` | 已在走棋/复活时清除 | 旧悔棋请求不作用后续局面 |
| NEW-02 | 服务端 | 低 | ✅二次已修 | `service/app.py:42` | tick 超时终局不递增 revision | 已单次递增 | 终局通知一致 |

### 1.3 已修复关键项（追溯，便于回归对照）

P0/P1 关键修复：S-01 连接风暴（按连接实例隔离 + 指数退避≤3）、S-02 桌面重连、S-03 AI 暂停竞态（落子前复检 paused/turn/history）、S-04/S-05 draw/undo 先应用状态再响应 + revision_independent、S-06 AI token 随机化、S-07 maintenance 加锁、S-08 broadcast 锁内快照、S-09 PING 直接 return、S-10 AI 房间 30min 回收、S-11 断线判负锁内即广播、S-13 偏好增量合并 + 桌面补齐 15+ 字段、C-14 联机复盘从 `replay` 恢复、A-02 离线棋谱导入入口、A-07 WebView 资源清理。

> 完整 47 条逐项核对表见 `docs/QA_v1.3.0.md` 第一/三章；本清单聚焦"仍需处理"与"本次新发现"。

---

## 交付物二：安卓双击音效故障专项分析报告

### 2.1 故障现象
安卓客户端（**离线同机模式**）选中己方棋子时，"选中音效"（`sounds/choose.wav`）被重复播放两次；Web 端与安卓在线模式（复用 Web 前端）不复现。

### 2.2 触发逻辑与代码定位

故障**仅存在于 `android/Resources/assets/offline/offline.js`**，根因为"回调重复执行"——同一次点击的 `pointerdown` 与 `pointerup` 各调用一次 `selectPiece()`，而 `selectPiece()` 内无条件 `playSound('select')`。

| 调用点 | 代码位置 | 行为 |
|---|---|---|
| `selectPiece()` 定义 | `offline.js:102` | `selected=piece; legal=...; capturable=...; playSound('select'); draw()` —— **无"同棋子不重复播音"守卫** |
| 触发点① pointerdown | `offline.js:112` | `if(piece&&piece.color===game.state.turn) selectPiece(piece)` —— 手指按下即选中并播音 #1 |
| 触发点② pointerup | `offline.js:113` | 走棋分支未命中（点击的是棋子自身格，非合法走法目标）→ 落入 `if(p&&p.color===game.state.turn){selectPiece(p)}` —— 手指抬起再次选中同一棋子并播音 #2 |

**对照（正确的实现）**：Web 在线端 `web/js/app.js` 已有双重守卫，故不复现：
- `app.js:213` pointerdown：`if(canControl(piece)&&(!app.selected||app.selected.row!==pos.row||app.selected.col!==pos.col))` —— 同棋子不重选；
- `app.js:192` `selectOrMove()`：`if(piece&&app.selected&&piece.row===app.selected.row&&piece.col===app.selected.col){draw();return}` —— 同棋子直接返回不播音。

### 2.3 四类根因排查结论

| 根因类别 | 结论 | 证据 |
|---|---|---|
| ① 点击事件重复绑定 | **否** | offline.js 仅各绑定一个 `pointerdown`/`pointerup`/`pointercancel`，无重复 addEventListener |
| ② UI 多次渲染 | **否** | `draw()` 被多次调用但只重绘画布，不触发音频 |
| ③ 回调重复执行 | **是（根因）** | 一次点击 = pointerdown + pointerup，两者均调用 `selectPiece()` → 两次 `playSound('select')` |
| ④ 触摸事件冒泡 | **否（但建议防御）** | offline.js 未绑定 mouse/click 兼容事件；但 Android WebView 对触摸会合成兼容鼠标事件，建议在 pointerdown 调用 `event.preventDefault()` 抑制合成事件，作为二级保险 |

### 2.4 修复代码示例

**主修复（推荐）**：让 `selectPiece` 对"同一棋子"幂等，仅在选择真正变化时播音。对齐 Web 在线端语义，最小改动、覆盖所有调用路径：

```js
// offline.js:102 原实现
function selectPiece(piece){
  selected=piece;
  legal=game.rules.legalFor(game.state,piece);
  capturable=[...new Map(legal.flatMap(move=>game.rules.capturedByMove(game.state,move))
      .map(p=>[`${p.row},${p.col}`,pos(p.row,p.col)])).values()];
  playSound('select');   // ← 每次 selectPiece 都播
  draw()
}
```

```js
// 修复后
function selectPiece(piece){
  const changed=!selected||selected.id!==piece.id;   // 选择是否真正变化
  selected=piece;
  legal=game.rules.legalFor(game.state,piece);
  capturable=[...new Map(legal.flatMap(move=>game.rules.capturedByMove(game.state,move))
      .map(p=>[`${p.row},${p.col}`,pos(p.row,p.col)])).values()];
  if(changed) playSound('select');                    // 仅变化时播音
  draw()
}
```

**附带加固（可选，对齐 Web pointerup 守卫 + 防合成事件）**：

```js
// offline.js:113 pointerup 内，重选前判断同棋子
const p=game.state.pieces.find(x=>x.row===target.row&&x.col===target.col);
if(p&&p.color===game.state.turn){
  if(!selected||selected.row!==p.row||selected.col!==p.col) selectPiece(p);  // 同棋子不再 selectPiece
}else{selected=null;legal=[];capturable=[];draw()}

// offline.js:112 pointerdown 内防合成鼠标事件
canvas.addEventListener('pointerdown',event=>{event.preventDefault(); /* …原逻辑… */});
```

> 说明：主修复已足够消除双击音；附带加固用于提升健壮性与跨 WebView 一致性。

### 2.5 回归验证用例

| 用例ID | 步骤 | 预期 |
|---|---|---|
| AU-SND-01 | 离线模式点击己方棋子（首次选中） | 选中音效**仅响一次** |
| AU-SND-02 | 选中 A 后再点 A（同棋子） | 不再播音，选中态保持 |
| AU-SND-03 | 选中 A 后点另一己方棋子 B | 切换选中，播音一次 |
| AU-SND-04 | 选中 A 后点合法落点走棋 | 选中音一次 + 走棋/吃子音一次 |
| AU-SND-05 | 走棋后点空格再点己方棋子 | 选中音一次 |
| AU-SND-06 | 快速连续点不同己方棋子 ×5 | 播音次数 = 切换次数，不漏不叠 |
| AU-SND-07 | 关闭音效开关后选中棋子 | 完全无声 |
| AU-SND-08 | 安卓在线模式（服务器）选中棋子 | 选中音一次（验证未引入回归） |

---

## 交付物三：安卓界面分层重构完整方案

### 3.1 现状与问题
- `MainActivity.cs:56` 直接 `SetContentView(webView)`，整个 App 只有一个 WebView 容器。
- 离线模式加载 `offline/index.html`：**模式选择 / 规则 / 语言 / 计时 / 皮肤 / 音效 / 棋盘 / 走棋操作 / 悔棋提和认输 / 棋谱 全部堆叠在单一滚动页**（`<section class="controls">` + `<section class="board-panel">` + `<section class="record">` 同级并存）。
- 在线模式加载 `web/index.html`（与 Web 浏览器共用），同样为单页工作台。
- 后果：对局进行中设置项与棋盘抢屏，操作学习成本高，不符合天天象棋/lichess/JJ 象棋"首页→对局页"的分层习惯。

### 3.2 竞品对标
| 产品 | 首页（欢迎/大厅） | 对局页 | 关键交互 |
|---|---|---|---|
| 天天象棋 | 模式入口（人机/联机/残局/学棋）+ 公告 + 头像 | 纯棋盘 + 计时 + 操作栏 + 聊天 | 首页点模式 → 进入对局页，返回回首页 |
| lichess | 大厅（创建/加入/题库/赛事） | 棋盘 + 计时 + 走子列表 + 聊天 | 大厅与对局分离，观战独立 |
| JJ 象棋 | 大厅 + 段位 + 好友 | 棋盘 + 计时 + 悔棋/求和/认输 | 标准两层 |

### 3.3 双页面职责划分

**① 欢迎主界面 `welcome.html`（首页/大厅）**
- 顶部品牌 + 版本公告条（离线时提示"服务器不可用，离线可用"）。
- 模式选择入口卡片：双人同机（离线可玩）/ 人机对战（需服务器，离线灰显）/ 网络对战（需服务器，离线灰显）/ 残局训练 / 复盘棋谱库。
- 设置区（折叠）：规则模式、语言、每方时限、读秒提醒、先手、棋盘主题、棋子样式、可行落点/吃子提示/音效开关、音量。
- 皮肤与题库入口（设置内或独立卡片）。
- 账号登录入口（仅在线模式可用，离线隐藏或灰显）。
- 关于入口。
- "开始对局"主按钮（携带所选模式与设置进入对局页）。

**② 棋盘对战界面 `game.html`（对局页）**
- 顶部精简栏：返回首页 + 当前模式/档案 + 翻转 + 重连（离线时）。
- 棋盘 + 棋子 + 走棋操作（选中/拖拽/合法落点/吃子提示/动画）。
- 对局信息：回合提示、双方计时、读秒、将军/将死/和棋结果。
- 操作栏：悔棋 / 暂停-继续 / 重开 / 提和 / 认输 / 保存 / 读取。
- 棋谱列表（可折叠）。
- 实时聊天（**仅联机模式**；离线无对手，隐藏）。
- 设置入口（轻量弹层，仅对局期可调项：音效/翻转/提示，避免离开对局）。

### 3.4 页面跳转逻辑
- 维持单一 `MainActivity` + WebView 外壳，**在离线资源内拆为两个 HTML 页** + 一个极简路由，降低原生层改动与风险。
- `welcome.html → game.html`：用户点"开始对局"，将所选 `mode/profile/options/clocks/language` 写入 `sessionStorage`（或 `XionghanAndroid.startGame(payload)` 桥），`location.replace('game.html')`。
- `game.html → welcome.html`：点"返回"或对局结束"回首页"，`location.replace('welcome.html')`。
- **Android 返回键**：`MainActivity.OnBackPressed` 当前只做 `webView.GoBack()`（`MainActivity.cs:305-309`）。改为：若当前在对局页且对局进行中，先弹"是否认输返回"确认；若已结束或首页，则 `GoBack()` 退出。可用 `webView.EvaluateJavascript` 查询当前页标记（如 `window.__page==='game'`）。
- 在线模式：服务器模式仍加载 `web/index.html`，建议 Web 端同步做"大厅/对局"视图拆分（与离线页结构对齐），安卓仅负责承载；本轮可先拆离线页，在线页作为后续与 Web 一致的迭代项。

### 3.5 资源拆分与代码解耦
- 新增 `android/Resources/assets/offline/welcome.html` 与 `game.html`，原 `index.html` 改为路由入口（按 `?page=` 或默认 `welcome`）。
- 共享层抽出 `offline-common.js`：`Rules` / `OfflineGame` / `NAMES` / `PROFILES` / `I18N` / `tr()` / `playSound` / `persistPreferences` / `boardPosition` / `geometry` / `draw` 等纯逻辑与渲染。
- `welcome.js`：仅负责设置表单、模式入口、公告、账号入口、`startGame(payload)`。
- `game.js`：仅负责棋盘交互、走棋、操作栏、棋谱、聊天占位（在线时由 Web 端接管）。
- CSS 拆 `welcome.css`（表单/卡片）与 `game.css`（棋盘/操作栏），公共变量放 `offline.css`。
- 音频 `sounds/*` 由 `offline-common.js` 统一加载，两页共享同一 `Audio` 实例池（避免重复实例）。
- 原生桥 `XionghanAndroid`（`MainActivity.cs:356`）保持，新增 `startGame`/`exitToWelcome` 可选方法；服务器检测逻辑（`CheckServerAsync`）不变，检测到在线后在欢迎页高亮"人机/联机"入口。

### 3.6 UI 交互规范（对标竞品）
- 首页采用"卡片+主按钮"纵向布局，单手可达；模式入口根据离线/在线状态显隐禁用（当前 `modeSelect` 的 disabled option 已有，迁移为卡片态）。
- 对局页棋盘占主视口，操作栏置于棋盘下方或底部固定栏（悔棋/提和/认输/暂停为一组，保存/读取为次要）。
- 计时器双栏置于棋盘上下（红/黑），读秒高亮（已有 `countdown` 类，沿用）。
- 聊天（联机）为可折叠抽屉，默认收起，不抢棋盘空间。
- 沉浸模式（`EnterImmersiveMode`）保持，欢迎页与对局页均触发 `RequestGameRedraw`。
- 国际化沿用 `offline-locales.js`，两页共享词条；新增 `welcome.*` / `game.*` 分组 key。

---

## 交付物四：全端新增隐性 Bug 排查清单

> 结合 QA 报告 47 条 + 本次代码复核，下列为**QA 报告未单独列出**的隐性 Bug。区分【安卓独有】与【多端通用】。

### 4.1 安卓独有

| 新ID | 严重 | 代码位置 | 问题 | 根因 | 修复建议 | 关联 |
|---|---|---|---|---|---|---|
| AU-NEW-01 | 中 | `offline.js:102,112,113` | 选中棋子双击音效 | pointerdown+pointerup 均调 selectPiece，无同棋子守卫 | 见交付物二 | — |
| AU-NEW-02 | 低 | `offline.js:105,106,108` | 加载已结束的存档会**重复计入统计** | `loadGameDocument()` 置 `game.recorded=false`，随后 `update()→recordFinished()` 见 winner 已设再次入统计 | 加载存档时若已终局，`recorded=true`（不重计） | — |
| AU-NEW-03 | 低 | `offline.js:80,84,96` | 离线错误/提示串仍硬编码中文（如 `'对局已暂停'`/`'非法走棋'`/`'没有可悔的棋'`/`'解题成功'`） | i18n 仅覆盖 UI 文案，未覆盖运行时抛错与解题 toast | 统一走 `tr()` / `reasonText()`，补 `error.*` 词条 | QA 称 i18n 完整，实为遗漏 |
| AU-NEW-04 | 低 | `offline.js:121` | `setInterval` 250ms 永久运行，即使终局仍每 250ms 调 `updateClocks()` | 定时器无终局停止 | 终局后 `clearInterval` 或 `setPaused` 式短路 | A-06 同源 |
| AU-NEW-05 | 低 | `offline.js:96,111` | `newGame()` 未重置 `activePuzzle`，新开对局仍触发残局提示 toast | 残局会话未随新局清理 | `newGame()` 内 `activePuzzle=null` | — |

### 4.2 多端通用（Web / 桌面 / 服务 / Core）

| 新ID | 严重 | 代码位置 | 问题 | 根因 | 修复建议 | 关联 |
|---|---|---|---|---|---|---|
| MT-NEW-01 | 低 | `core/ai.py:233-267` | 多 ARMOR/ASSASSIN 局面静态搜索走法爆炸（QA C-06 未修） | 战术走法未裁剪 | 仅生成与近邻棋子相关的战术走法 | C-06 |
| MT-NEW-02 | 低 | `core/game.py:36-43` | `_snapshots` 无上限，超长对局内存增长（QA C-13 仅缓解） | 设计无上限 | 滚动窗口或按回合抽样 | C-13 |
| MT-NEW-03 | 低 | `service/` 单进程内存房间 | 房间为单进程内存态，重启即丢（DELIVERY 已述） | 架构 | 长期：持久化房间或 Redis | — |
| MT-NEW-04 | 低 | `web/js/app.js:213,214` | Web 在线 pointerup 对"拖拽未超阈值"也走 `selectOrMove`，逻辑等价但冗余 | 拖拽阈值未真正使用 | 合并分支或保留（无功能影响） | — |
| MT-NEW-05 | 信息 | `offline.js`/`web/js/app.js` | 离线与 Web 共享 `names`/`NAMES` 棋子字面量，维护两份 | 双轨引擎 | 抽共享 `pieces-names.js` | A-01 同源 |

### 4.3 已在 QA 报告中、但需重点回归的项（避免遗漏）
- **A-01 离线规则等价性**（严重·架构）：特色棋子 ARCHER/THUNDER/ARMOR/ASSASSIN 边界最易分歧，建议优先建等价性自动化测试。
- **NEW-01/NEW-02**：已二次修复，建议补一次联机端到端回归（悔棋后走棋再接受、超时终局通知）。
- **桌面端 S-02/S-04**：代码正确但无自动化测试，上线前**必须手动验证**（断线重连 3 次、draw+走棋同时到达）。

---

## 交付物五：修复后三端一致性校验标准

### 5.1 校验矩阵（核心维度）
| 维度 | 桌面 | Web | 安卓离线 | 安卓服务器 | 校验方法 |
|---|---|---|---|---|---|
| 14 棋子走法 | 同局面一致 | 同 | 同(JS引擎) | 同(复用Web) | 自动化规则套件 |
| 胜负判定 | 同局面一致 | 同 | 同 | 同 | 将死/困毙/和棋快照对比 |
| AI 四档(固定种子) | 一致 | 一致 | N/A | 一致 | AI 回放 |
| 棋谱往返 | 导出=导入 | 同 | 同 | 同 | 二进制/状态对比 |
| 翻转坐标 | 命中正确 | 同 | 同 | 同 | 点击映射测试 |
| 暂停冻结 | 计时不走 | 同 | 同 | 同 | 计时快照 |
| 偏好同步 | 增量不覆盖 | 同 | N/A | 同 | 字段对比 |
| 国际化 | 全文案切换 | 同 | 同 | 同 | 翻译 key 对比 + 错误串扫描 |
| 音效 | 选中=1次 | 选中=1次 | **选中=1次（本次修复后）** | 选中=1次 | AU-SND 用例集 |

### 5.2 本次修复必须通过的回归项
| 项 | 验证标准 | 优先级 |
|---|---|---|
| 双击音效(AU-NEW-01) | 离线选中棋子音效仅一次（AU-SND-01~08 全过） | P0 |
| 统计重复计数(AU-NEW-02) | 加载已结束存档不重复入统计 | P1 |
| 离线错误串 i18n(AU-NEW-03) | 英文下错误/toast 不出现中文硬编码 | P1 |
| 桌面断线重连(S-02) | 短暂断网自动重连≤3次，状态正确 | P0 |
| 桌面 draw 并发(S-04) | 提和+走棋同时到达，状态不回退 | P0 |
| 离线规则等价(A-01) | 同一走法离线/在线判定一致（特色棋子全覆盖） | P0(长期) |

### 5.3 上线前手动验证清单（QA 报告交接项）
- [ ] 桌面端联机断线重连 3 次场景（S-02）
- [ ] 桌面端 draw/undo 请求与走棋同时到达（S-04）
- [ ] Docker 单实例部署联机全流程（CT-13）
- [ ] Android 离线棋谱导入端到端（A-02）
- [ ] Android 离线选中音效单次（AU-NEW-01，本次新增）

### 5.4 后续迭代建议（不阻断上线）
1. `core/game.py:move()` 已清 `pending_undo_offer`（NEW-01 已修），建议补单测固化。
2. `core/ai.py` C-06 战术走法裁剪 + C-13 快照上限（性能与内存）。
3. 离线/在线规则等价性自动化测试（A-01 长期）。
4. 安卓界面双页拆分（交付物三），与 Web 在线页"大厅/对局"拆分对齐推进。

---

*本方案所有结论均标注代码位置，可直接交付研发整改。规则相关项（C-01/C-03/C-04/C-11/C-12）须产品确认后修改，未自行篡改规则。*
