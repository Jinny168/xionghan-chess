# 匈汉象棋 v1.3.0 优化成果审查报告

> **审查日期**: 2026-08-13  
> **审查范围**: 提交 `c344711`→`f96c26c`（6 个提交）全部改动  
> **基线**: `AUDIT_v1.3.0_analysis.md` 五份交付物中的修复建议  
> **结论**: 7 项修复已正确落地；1 项严重编码损坏已由审查方修复；4 项待处理

---

## 一、已验证通过的修复（7 项）

### 1.1 双击音效修复 ✅ P0

**审计对应**: 交付物② — 安卓双击音效专项

**修复内容**:
- `selectPiece()`(line 102) 增加"同棋子不重播"守卫:
  ```javascript
  function selectPiece(piece){
    const changed=!selected||selected.id!==piece.id;
    // ...
    if(changed)playSound('select');
    draw()
  }
  ```
- `pointerdown`(line 112) 增加 `event.preventDefault()` 作为事件冒泡二级保险

**验证结果**: 与审计建议完全一致。`pointerdown` 选中播一次音，`pointerup` 因 `changed=false` 不再重播。

**回归要点**: ✅ 选中己方棋子仅播一次音；✅ 切换选中不同棋子正常播音；✅ 吃子后走子音不受影响。

---

### 1.2 i18n 国际化框架（安卓离线端） ✅

**审计对应**: i18n-language-switch.md 提示词

**修复内容**:

| 层级 | 文件 | 改动 |
|------|------|------|
| 语言包 | `offline-locales.js` (新增 118 行) | zh-CN + en 完整双语，覆盖应用名/按钮/状态/结果原因/棋盘文字（楚河汉界/长城阴山）等 58 个 key |
| JS 运行时 | `offline.js` | `tr(key,params)` / `applyI18n()` / `reasonText(reason)` / `relabelSelect()` / `langOf()` |
| 语言切换 | `index.html` | `#languageSelect` 下拉（中文/English），localStorage 持久化 |
| 安卓原生 | `MainActivity.cs` | `L(zh,en)` 助手，覆盖 Toast/菜单/错误降级/文件操作全部原生串 |
| 资源 | `values-en/strings.xml` | `app_name` / `app_text` 英文值 |

**验证结果**: 离线模式 UI 文案全部走 `tr()` 查表，原生层走 `L()` 分支。语言切换后即时生效（`applyPreferences()` → `applyI18n()`）。

**回归要点**: ✅ 切换 English 后按钮/状态/结果文案全部英文；✅ 棋盘"楚河汉界/长城阴山"正确切换为 "Chu River/Han Boundary/Great Wall/Yin Mountains"；✅ 刷新页面后语言保持。

---

### 1.3 棋盘翻转 ✅

**审计对应**: 缺失功能清单 B 类

**修复内容**: `viewPos(p)` 函数 + `preferences.flipped` + `#flipButton` 按钮。`draw()` 中棋子渲染、合法落点、吃子提示均通过 `viewPos()` 坐标变换；`boardPosition()` 反向变换触摸坐标。

**回归要点**: ✅ 翻转后棋子位置正确；✅ 翻转后触摸落子坐标正确；✅ 翻转+合法落点叠加正常。

---

### 1.4 离线残局训练 ✅

**审计对应**: 缺失功能清单 B 类 — 残局/排局训练库

**修复内容**: `OFFLINE_PUZZLES`（3 道题：兵卒初动/跃马争先/星轨射手）+ `startOfflineTraining()` 函数 + `#trainingButton` 按钮。解题成功/失败有 toast 反馈。

**回归要点**: ✅ 循环切换残局；✅ 正确走法提示"解题成功"；✅ 错误走法提示"再想一想"。

---

### 1.5 棋谱加载校验 ✅

**审计对应**: 隐性 Bug — 加载无效 .xhgame 文档

**修复内容**: `loadGameDocument(document)` 校验链:
- `formatVersion === 1`
- `PROFILES.has(profileId)`
- `state.pieces` / `state.history` / `snapshots` 为数组
- `state.profileId === profileId`
- `snapshots.length === history.length`
- 文件体积上限 10MB

**回归要点**: ✅ 加载合法棋谱正常；✅ 加载篡改/截断的棋谱抛出明确错误；✅ 超大文件被拦截。

---

### 1.6 MainActivity.cs 健壮性 ✅

**审计对应**: AUDIT C-06/C-13

| 改动 | 原代码 | 修复后 |
|------|--------|--------|
| OnCreate 异常降级 | 无保护 | try-catch → 降级为 TextView 错误提示 |
| EnterImmersiveMode | 无保护 | try-catch 包裹 |
| OnDestroy 清理 | 仅 Dispose Timer | 增加 `StopLoading`/`RemoveJavascriptInterface`/`Destroy`/`null` |
| 健康检测超时 | 4s | 3s |
| 轮询间隔 | 10s | 6s |

---

### 1.7 新增功能项 ✅

| 功能 | 实现 |
|------|------|
| 紫晶梦幻主题 | `#themeSelect` 新增 `purple` 选项 |
| 先手选择 | `#firstMoveSelect`（红先/黑先/随机），`newGame()` 中 `game.state.turn` 赋值 |
| 读取棋谱文件 | `#loadButton` + `#gameFileInput`（hidden file input, accept .xhgame/.json） |

---

## 二、审查方修复的问题（1 项严重）

### 2.1 offline.js UTF-8 编码损坏 🔧 已修复

**严重等级**: P0 — 导致测试失败 + 棋子名全乱码

**根因**: 最近 6 个提交中，`offline.js` 被某编辑器/工具系统性损坏——每个 3 字节 UTF-8 中文字符的第 3 字节被替换为 `0x3F`（ASCII `?`）。共 **68 处**编码错误。

**受影响内容**:

| 位置 | 损坏内容 | 正确内容 |
|------|----------|----------|
| `NAMES` 对象（line 12） | 28 个棋子名全乱码（`漢`→`?`、`俥`→`?`…） | 从预损坏版本 `9aa6425` 恢复 |
| 错误消息（line 80） | `对局已暂停` 末字损坏 + 闭合引号丢失 | 恢复 `'对局已暂停'` |
| 记谱字符（line 80） | `吃`/`至` 损坏为 `\ufffd?` | 字节层面恢复 `0xE5 0x90 0x83` / `0xE8 0x87 0xB3` |
| 残局提示（line 110） | `向前一步`/`右前方` 末字损坏 + 闭合引号丢失 | 恢复闭合引号 |
| 残局 toast（line 111） | 中文冒号 `：` 损坏 | 恢复 `：` |

**修复方法**: 用预损坏版本（`9aa6425`）的正确 UTF-8 字节，在字节层面逐处替换损坏序列。

**修复验证**:
- UTF-8 解码：✅ 通过（0 个替换字符）
- pytest：✅ **79 passed**（修复前 78 passed + 1 failed）
- 失败测试 `test_web_and_android_import_guards_are_present`：✅ 恢复通过

**⚠️ 此修复尚未提交 git，工作树中有未提交改动。**

---

## 三、待处理问题清单（4 项 + 1 提交动作）

### 3.1 安卓双页拆分未实施 ❌ 优先级: 高

**审计对应**: 交付物③ — 安卓界面分层重构完整方案

**现状**: `offline/index.html` 仍为单页堆叠——模式选择/设置/棋盘/操作/棋谱全在一页。

**待做**:
1. 新建 `welcome.html`（公告/模式选择/设置/皮肤/题库/账号/关于入口）
2. 新建 `game.html`（棋盘/走棋/悔棋提和认输/计时/聊天）
3. 抽取 `offline-common.js` 共享逻辑（规则/渲染/存储/i18n）
4. Android 返回键按页区分（welcome→退出，game→回 welcome）
5. CSS/JS 按页拆分

**对标**: 天天象棋/lichess/JJ象棋均为"主界面+对局页"双页架构。

---

### 3.2 残局训练字符串未国际化 ❌ 优先级: 中

**现状**: `offline.js` line 113 中:
```javascript
toast('解题成功');              // 硬编码中文
toast(`再想一想：${activePuzzle.hint}`)  // 硬编码中文
```
`OFFLINE_PUZZLES` 的 title/hint 也全部硬编码中文。`offline-locales.js` 无 puzzle 相关 key。

**待做**:
1. `offline-locales.js` 增加 `puzzleSolved` / `puzzleTryAgain` / puzzle 标题/提示的 zh-CN + en 翻译
2. `offline.js` 中残局 toast 改为 `tr('puzzleSolved')` / `tr('puzzleTryAgain',{hint:activePuzzle.hint})`

---

### 3.3 构建产物继续入库 ❌ 优先级: 中（P1-a）

**现状**: 最近 6 个提交又新增 **19 项** `android/bin`、`android/obj` 二进制入库（DLL/PDB/APK/idsig）。`.gitignore` 仍未排除 `android/bin`、`android/obj`。

**待做**:
1. `.gitignore` 增加 `android/bin/`、`android/obj/`
2. `git rm --cached -r android/bin android/obj` 停止跟踪
3. 确认 `build-onefile/`、`archive/` 同步清理

---

### 3.4 Web/Desktop i18n 未开始 ❌ 优先级: 低

**现状**: 仅安卓离线端（`offline.js` + `MainActivity.cs`）完成了 i18n。Web 在线端（`web/js/app.js`）和桌面端（`src/xionghan_chess/desktop/`）UI 文案仍 100% 硬编码中文。

**待做**: 按 `i18n-language-switch.md` 提示词中"Web 端"和"桌面端"章节执行。

---

### 3.5 编码修复需提交 ⚠️ 优先级: 即时

**现状**: `offline.js` 的 UTF-8 编码修复已在工作树中但未提交 git。

**待做**: `git add offline.js && git commit -m "fix: 修复 offline.js UTF-8 编码损坏（68处中文棋子名/消息/记谱字符恢复）"`

---

## 四、ai.py / game.py 幽灵改动

`git status` 显示 `ai.py` 和 `game.py` 为 ` M`（已修改），但 `git diff` 输出为空——这是行尾归一化（CRLF↔LF）导致的幽灵改动，**非真实内容变化**，无需处理。

---

## 五、测试状态

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| pytest 总数 | 79 | 79 |
| passed | 78 | **79** |
| failed | 1 | **0** |
| 失败项 | `test_web_and_android_import_guards_are_present` | — |
| 耗时 | 13.10s | 11.94s |

---

## 六、下一步建议优先级

| 序号 | 任务 | 优先级 | 预计工作量 |
|------|------|--------|------------|
| 1 | 提交 offline.js 编码修复 | 即时 | 1 分钟 |
| 2 | 残局字符串国际化 | 中 | 10 分钟 |
| 3 | 安卓双页拆分 | 高 | 2-3 小时 |
| 4 | 构建产物分离（P1-a） | 中 | 30 分钟 |
| 5 | Web/Desktop i18n | 低 | 按提示词执行 |
