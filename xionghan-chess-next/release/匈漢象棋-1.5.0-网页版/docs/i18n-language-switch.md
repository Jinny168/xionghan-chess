# 匈汉象棋 · 中英文切换（i18n）功能规划与 AI 提示词

> 范围：仅 `xionghan-chess-next/`（三端共享同一套 Python 核心）  
> 目标：为游戏增加"中 / 英文"语言选项，支持运行时切换并持久化  
> 编写时间：2026-08-11

---

## 一、现有功能总结（xionghan-chess-next）

基于全代码树核查，当前功能如下。重点提示：**全项目无任何 i18n 机制，UI 文案 100% 硬编码中文。**

### 1. 游戏核心（`src/xionghan_chess/core/`）

- **棋盘**：默认 13×13 扩展棋盘（匈汉模式），另支持 10×9 传统象棋模式。
- **棋子**：14 种（7 标准：将/车/马/相/仕/炮/兵 + 7 特色：尉/卫、射/䠶、檑/礌、甲/胄、刺/伺、楯/碷、巡/廵），名称硬编码于 `profiles.py:117-130`。
- **规则**：马直走三格、兵快速行军/升变、射手星轨走法、甲胄夹击、刺客反向兑子、盾不可被吃、巡边界横移、将帅照面、夹逼等。
- **胜负**：将死 / 困毙 / 三次重复 / 长将无进展 / 超时 / 认输 / 断线超时。
- **规则档案**：`desktop_complete` / `desktop_classic` / `web` / `traditional` 四套。
- **对局模式**：online（联机）/ ai（人机）/ local（双人同机）。
- **AI**：alpha-beta 搜索，4 档难度（BEGINNER/EASY/MEDIUM/HARD）。
- **棋谱**：`.xhgame` 序列化（`storage.py`）。

### 2. 共享服务（`src/xionghan_chess/service/`，FastAPI + WebSocket）

- REST：`/api/health`、`/api/profiles`、`/api/rooms`（创建/加入/导入）、`/api/rooms/{id}/legal`（合法走法校验）。
- 房间：6 位房间号、断线重连宽限 90s、AI 座位名"匈汉棋灵"。
- 对局服务：计时、暂停/继续、悔棋、提和、认输、复活兵卒、聊天、棋谱导入导出。
- 中文错误串硬编码于 `rooms.py`（如"房间不存在或已过期""现在不是你的回合"）。

### 3. Web 端（`web/`，原生 HTML + JS + Canvas）

- 页面：对弈、棋谱库（localStorage `xh-replays`）、统计、设置、帮助/规则/关于对话框。
- `<html lang="zh-CN">`，菜单/按钮/提示全部中文硬编码（`index.html`、`js/app.js`）。

### 4. 桌面端（`src/xionghan_chess/desktop/`，PySide6）

- 功能：人机/双人同机/联机、规则设置面板、主题/字体/背景/棋子风格、动画、走子提示、复盘、本地棋谱库、统计、全屏。
- 中文硬编码密集（`app.py` 约 153 行含中文），文档 `resources/docs/*.md` 全中文。

### 5. 安卓端（`android/`，.NET 9 原生 WebView + JS 桥）

- 离线同机对弈（自包含 `Resources/assets/offline/` HTML/JS）、在线恢复、导入/导出（系统文件选择器）、`GameBridge` 桥（`saveGame`/`retryServer`/`openServerSettings`/`getServerUrl`）。
- 中文 Toast/Hint 硬编码（`MainActivity.cs` 约 23 行），`strings.xml` 仅 `app_name` 等。

### 6. 国际化（i18n）现状 —— 关键结论

- **无 i18n 框架/库**：无 gettext / Babel / i18next / vue-i18n / QTranslator 等。
- **无语言包/ locales 目录**：无 `.po/.mo/.qm/.resx/.arb/.json` 翻译文件。
- **无翻译函数 / 语言切换入口**：无 `t()` / `_()` / `gettext()` 调用，无任何"语言/English/中文"切换 UI。
- 文案分布在 6 类位置：核心 `profiles.py`/`game.py`、服务 `rooms.py`、Web `index.html`/`app.js`、桌面 `app.py`/`docs/*.md`、安卓 `MainActivity.cs`/`strings.xml`/`offline/*`。

---

## 二、AI 提示词（直接复制给 AI / 开发者即可执行）

> 下面这段提示词用于驱动 AI 为"匈汉象棋"实现中英文切换。已包含目标、范围、方案、验收标准。

```markdown
# 任务：为匈汉象棋（Xionghan Chess）增加"中文 / 英文"语言切换

## 背景
匈汉象棋是一个三端（Web / 桌面 / 安卓）共享同一套 Python 核心逻辑的象棋游戏，
代码主树在 `xionghan-chess-next/`。当前所有 UI 文案 100% 硬编码为中文，没有任何
i18n 机制。现需要增加语言选项，支持中文（zh-CN）与英文（en）运行时切换并持久化。

## 目标
1. 用户可在"设置"中切换 中文 / 英文，切换后无需重启即可生效（Web 即时、桌面即时、
   安卓在线即时 / 离线重绘后生效）。
2. 语言偏好自动保存，下次打开沿用。
3. 默认语言为中文（zh-CN），缺失翻译时回退到中文。

## 范围与方案
请按"集中抽取翻译 + 各端消费"的方式实现，不要逐条改文案而保留硬编码：

1. **翻译资源**：新建 `xionghan-chess-next/locales/` 目录，提供 `zh-CN.json` 与 `en.json`
   两份语言包，采用分层 key（如 `menu.file`、`common.save`、`settings.appearance`、
   `error.room_not_found`、`piece.king`、`rule.horse_straight_three`）。
   所有用户可见文案（菜单、按钮、对话框、提示、错误串、棋子显示名、规则说明）都进语言包。

2. **核心层（core）**：把 `game.py` 的 `GameError` 中文串、`profiles.py` 的 14 种棋子名称
   抽到语言包。注意：棋子的"汉字字形"（如漢/汗）是棋面本体，可保留字形但需补充英文
   显示名（建议：将→Rook、车→Rook、马→Knight、相→Minister、仕→Guard、炮→Cannon、
   兵→Soldier；特色棋子 尉/卫→Captain、射/䠶→Archer、檑/礌→Catapult、甲/胄→Armor、
   刺/伺→Assassin、楯/碷→Shield、巡/廵→Patrol，英文命名可由你按语义微调）。

3. **服务层（service/rooms.py）**：中文异常串改为从语言包按当前语言取值；对外 JSON
   仍用英文 key（保持 `to_dict()` 驼峰键不变，不影响协议）。

4. **Web 端（web/）**：用轻量 i18n（一个 `i18n.js` + `locales` JSON，或 i18next），
   把所有 `index.html` 文案与 `app.js` 的 `labels/pieceLabels/names` 对象、toast、
   连接状态提示都改为 `t('key')`。`app.js` 的 `toLocaleString('zh-CN')` 改为按语言
   选择 locale。`app.js` 绘制的"楚河汉界/长城阴山"棋盘文字：中文保留，英文可改为
   "Han River / Boundary" 与 "Great Wall / Yin Mountains"（二选一，保持可读）。

5. **桌面端（desktop/，PySide6）**：引入 `QTranslator` 或简单的 `t(key)` 字典查表，
   把所有 `QAction`/`QMessageBox`/`QInputDialog`/`drawText` 的中文替换；
   `config.py` 增加 `language` 配置项并持久化到 `settings.json`；设置对话框加语言下拉。
   `resources/docs/*.md` 增加对应英文文档或改用语言包内的说明文本。

6. **安卓端（android/）**：在线模式复用 Web 的语言包与切换（保证一致）；
   离线包 `Resources/assets/offline/*.js|html|css` 内中文也抽到一个 `offline-locales`
   或复用同一 JSON；`strings.xml` 增加 `values-en/strings.xml`（app_name 等）；
   `MainActivity.cs` 的 Toast/Hint 改为按语言取值（可通过注入 JS 变量或资源切换）。

7. **切换入口**：三端"设置"页都加"语言：中文 / English"选项；切换即写偏好并重新渲染。

## 约束
- 不得改变任何游戏规则、走法、胜负判定、协议字段名与 `.xhgame` 格式。
- 棋盘坐标/棋子字形的游戏语义保持稳定，仅 UI 文案国际化。
- 不引入重型框架（桌面端避免强依赖 Qt Linguist 工具链，优先字典查表）。
- 保持现有 pytest 测试通过，新增翻译缺失的单测（key 在 zh-CN/en 中成对存在）。

## 验收标准
- [ ] `locales/zh-CN.json` 与 `en.json` 覆盖三端全部用户可见文案，key 成对。
- [ ] Web / 桌面 / 安卓在线 切换语言即时生效，无需重启。
- [ ] 语言偏好持久化，重启后沿用。
- [ ] 默认中文，缺失翻译回退中文（无空白/无 KeyError）。
- [ ] 核心 `GameError`、棋子英文名已抽取且中英一致。
- [ ] `pytest` 全绿；新增"翻译 key 成对"校验测试通过。
- [ ] 安卓离线模式同样支持语言切换。
```

---

## 三、联网调研：与同类产品对比的"缺失功能"清单

> 来源：en-croissant（i18next 架构）、MyChess（gettext 双语）、lichess（100+ 语言、  
> 功能矩阵）、xiangqi_pyqt、天天象棋/中国象棋竞技版等公开资料。下列为"相对这些产品的  
> 缺失项"，按"与本次 i18n 强相关"和"通用功能"分两类。

### A. 与"中英文切换 / 国际化"强相关的缺失（建议本任务一并纳入）

- [ ] **缺失正式 i18n 框架**：当前无任何翻译层，所有文案硬编码（本次任务核心）。
- [ ] **缺失语言自动检测 / 回退机制**：同类产品（lichess/MyChess）均按系统 locale 自动选语言 + 缺失回退英文（本项目应默认中文回退）。
- [ ] **缺失日期/数字本地化**：`app.js` 固定 `toLocaleString('zh-CN')`，英文环境应切换 locale。
- [ ] **缺失棋子英文命名规范**：象棋惯例"车=Rook、马=Knight、炮=Cannon"（见 Flutter 象棋规范），本项目特色棋子（尉/卫/射/䠶…）无英文命名，需定义。
- [ ] **缺失可扩展的多语言架构**：同类产品用 key 化语言包（en-croissant 的 `Common.Save` 分层 key），本项目无任何 key 体系，未来加第三语言成本高。
- [ ] **缺失"跟随系统"选项**：多数成熟产品提供"跟随系统/中文/English"三态，本项目仅做二选一即可，但建议预留跟随系统。

### B. 通用象棋游戏功能缺失（对比天天象棋 / xiangqi_pyqt / lichess）

- [ ] **棋谱格式互通**：仅自有 `.xhgame`，缺 PGN / FEN / XQF / CBL 导入导出（竞品普遍支持，便于分享与研究）。
- [ ] **PGN/FEN 标准记谱**：缺标准代数记谱与局面（FEN）导入导出（xiangqi_pyqt、中国象棋竞技版均支持）。
- [ ] **棋局分析 / 引擎复盘**：缺 Stockfish 类深度分析与"走子质量评分/失误检测"（天天象棋"智能复盘"、lichess 分析面板）。
- [ ] **残局 / 排局库与训练**：缺内置残局题库与"猜大师着法"练习（天天象棋 6 万+ 习题、中国象棋竞技版数千残局）。
- [ ] **段位 / ELO 评级与排行榜**：缺棋力评级体系与好友/全球排行榜（天天象棋 42 段、lichess Glicko-2）。
- [ ] **棋盘翻转 / 视角切换**：缺红黑视角翻转（xiangqi_pyqt、giteebingo/Chess 均有）。
- [ ] **观战 / 赛事（Spectator / Tournament）**：缺观战模式、竞技场/瑞士制锦标赛（lichess 核心功能）。
- [ ] **战术谜题（Puzzles）**：缺自适应战术题训练（lichess Puzzle Storm/Racer）。
- [ ] **棋谱研究与变着标注**：缺可分享的"研习"、变着箭头、文字注释（lichess Studies、竞品打谱注释）。
- [ ] **键盘操作 / 无障碍**：缺键盘走子与读屏支持（lichess 强调无障碍，本项目三端均无）。
- [ ] **明暗主题细化 + 自定义棋盘/棋子皮肤**：已有主题/字体，但缺成熟的浅色/深色与多套棋盘棋子皮肤体系（lichess 支持）。
- [ ] **让子 / 让先**：联机缺"让子/让先"设置（中国象棋竞技版支持）。
- [ ] **在线账号与云同步**：当前联机为临时房间，缺账号体系与对局云存储（竞品标配）。

### 优先级建议

1. **本次必做**：A 类全部（即中英文切换 + 自动检测/回退 + 棋子英文命名 + key 化架构）。
2. **近期高价值**：B 类中的 PGN/FEN 互通、棋盘翻转、棋局分析复盘、残局库。
3. **中长期**：评级排行榜、观战赛事、谜题、账号云同步、更多语言。

---

*附：本文件为规划文档，不在本次代码提交范围内。实现时请按"二、AI 提示词"执行，并  
将 A 类缺失项纳入同一轮改造。*
