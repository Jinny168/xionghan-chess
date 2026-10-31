# 匈汉象棋 桌面端运行期几何审计（2026-10-31）

> 审计人：美术总监 甄塑之（art-model-director-2）
> 基准：工作区 `48cd24f`（1.7.5 打包提交），工作树干净，实测即在当前源码上做
> 方法：`QT_QPA_PLATFORM=offscreen` 实例化真实窗口 → 遍历控件树 → 比较 **实际 geometry / sizeHint / minimumSizeHint / 父容器矩形**
> 性质：**只读**。本文不含任何源码改动，也不提交。
> 上一轮（审美/一致性）见 `docs/UI_AUDIT_2026-10-31.md`；本文只谈**几何**：挤压、重叠、溢出。

---

## 0. 结论摘要

1. **P0 只有一条缺陷（G-01，三档尺寸各一个测量点 G-01/b/c），但足够致命**：主窗口侧栏的内容最小宽是 **388px**（`app.py:163` 每个动作按钮 `setMinimumWidth(182)` × 2 列），而侧栏本身被 `setMaximumWidth(330)` 卡住（`app.py:151`）——**在默认 1260×850 下就已经横向溢出 99px，两条滚动条常驻，右侧「暂停/提和/翻转」按钮只露出 92/182px（50%）**（截图 `build/geom/main_default.png`）。
2. 五个对话框把 `setMinimumSize` 直接设成 `minimumSizeHint`，而 Qt 对列表/文本控件的 `minimumSizeHint` 极小 —— 拖到最小后：题库列表 **70px**（约 3 行）、棋谱库列表 **70px**、规则正文 **80×70**（每行约 2 个汉字）、让子对话框两个列表 **102×70 / 96×70**。
3. 棋盘控件**从来不是正方形**：903×737（默认）/ 711×587（中间）/ 637×567（最小），绘制按 `min(cw,ch)` 取格 → 长边两侧**在正常留白之外**各多出 83 / 62 / 35px 空带（实测：默认左留白 36+83=119px，右侧同）。
4. **负向结论（测了没问题，不必再查）**：暂停/思考遮罩文字在最小窗口下仍放得下（126×72 vs 637×567）；横幅长文本不裁切（最长 608px vs 可用 866px）；上一轮在 760×560 下发现的自绘棋盘重叠（38px）与溢出（9px）**已不可复现**——`setMinimumSize` 提到 900×640 后消失。

---

## 1. 总表

> 判定类型：**挤压** = 实际 < 需求；**重叠** = 同级 geometry 相交 > 4×4px；**溢出** = 超出父容器 ≥2px。
> 「需求」优先取 `minimumSizeHint`（硬下限），无则取 `sizeHint`；两者皆 -1 时标「无法测量」。

| 编号 | 严重度 | 窗口 | 控件 | 实测值 | 需求值 | 差多少 | 判定 |
|---|---|---|---|---|---|---|---|
| **G-01** | **P0** | 主窗口 1260×850 | 侧栏 `QScrollArea` 内容 vs 视口 | 内容 388×737 / 视口 289×707 | 视口需 ≥388 宽 | **横溢出 99px、纵 30px**，两条滚动条常驻；第二列按钮从 x=197 起，只露出 92/182px（**50%**） | 溢出（可滚动，但右列按钮被切） |
| G-01b | P0 | 主窗口 1000×700 | 同上 | 388×737 / 221×557 | ≥388 | **横 167px、纵 180px** | 溢出 |
| G-01c | P0 | 主窗口 900×680 | 同上 | 388×737 / 195×537 | ≥388 | **横 193px、纵 200px** | 溢出（几乎半个侧栏出画） |
| G-02 | P1 | 主窗口 默认 | `BoardWidget` | 903×737 | 正方形（差值即死区） | **长边多 166px**（两侧各 83px 额外留白） | 非正方 → 绘制死区 |
| G-02b | P1 | 主窗口 中间 | `BoardWidget` | 711×587 | 正方形 | 124px（两侧各 62px） | 同上 |
| G-02c | P1 | 主窗口 最小 | `BoardWidget` | 637×567 | 正方形 | 70px（两侧各 35px） | 同上 |
| G-03 | P1 | TrainingDialog 最小 274×158 | `QListWidget`（残局题库） | 252×**70** | 192（sizeHint） | 高度只剩 **36%**（约 3 行） | 挤压 |
| G-04 | P1 | GameLibraryDialog 最小 360×150 | `QListWidget`（本地棋谱） | 338×**70** | 192 | **36%** | 挤压 |
| G-05 | P1 | DocumentDialog 最小 102×125 | `QTextBrowser`（规则正文） | **80×70** | 256×192 | 宽只剩 **31%**（每行约 2 字） | 挤压 |
| G-06 | P1 | HandicapDialog 最小 274×221 | 左右两个 `QScrollArea`（让子勾选） | **102×70 / 96×70** | 256×192 | 宽 40%、高 36% | 挤压 |
| G-07 | P1 | ReplayDialog 最小 639×500 | `QListWidget`（着法列表） | **134**×377 | 256×192 | 宽少 **122px**，长着法被省略号截断 | 挤压 |
| G-07b | P1 | ReplayDialog 最小 639×500 | `BoardWidget`（复盘盘面） | 461×420 | 正方形 | 41px 死区 | 非正方 |
| G-08 | P2 | PieceAtlasDialog 900×640 | 整窗 vs 自然尺寸 | 900×640 | sizeHint **1431×596** | 宽少 **531px**（内容整体压缩） | 低于自然尺寸 |
| G-08b | P2 | PieceAtlasDialog | 演示 `BoardWidget` | 302×378 | 正方形 | 76px 死区 | 非正方 |
| G-09 | P2 | SettingsDialog 720×760 | 内容 | 469×593（natural） | — | 空白面积 **49%**（宽多 251、高多 167） | 过度开窗 |
| G-09b | P2 | ReplayDialog 960×820 | 内容 | 708×500 | — | 空白面积 **55%** | 过度开窗 |
| G-09c | P2 | TrainingDialog 760×560 | 内容 | 278×280 | — | 空白面积 **82%** | 过度开窗 |
| G-09d | P2 | GameLibraryDialog 700×520 | 内容 | 360×272 | — | 空白面积 **73%** | 过度开窗 |
| G-09e | P2 | DocumentDialog 760×680 | 内容 | 278×247 | — | 空白面积 **87%** | 过度开窗 |
| G-09f | P2 | HandicapDialog 720×620 | 内容 | 379×607 | — | 空白面积 **49%** | 过度开窗 |

**没有检出的项**（明确写出来，避免重复排查）：
- 同级控件**重叠**：全窗口 0 处（每窗口遍历 5–80 个控件）。
- 非滚动容器的**子控件溢出**：0 处（G-01 是滚动区内容，属"可滚动"类，单列）。
- **文字裁切**（QLabel 文本宽 > 控件宽）：0 处；横幅做了 4 组压力测试（见 §4）。

---

## 2. 逐条复现

> 所有片段都基于同一个最小骨架：
> ```python
> import os, sys; os.environ["QT_QPA_PLATFORM"]="offscreen"; sys.path.insert(0,"src")
> from PySide6.QtWidgets import QApplication
> from xionghan_chess.desktop.app import MainWindow
> app=QApplication([]); w=MainWindow(); w.show(); app.processEvents()
> ```

### G-01 侧栏在默认尺寸就溢出（P0）

```python
w.resize(1260,850); app.processEvents()
sa=w.side; print(sa.widget().width(), sa.viewport().width())      # 388 vs 289
print(sa.horizontalScrollBar().maximum())                          # 99  → 必须横向滚动
print(sa.verticalScrollBar().maximum())                            # 30
```

根因链（两行代码的乘积）：
- `app.py:163`：`for i,b in enumerate((undo,pause,resign,draw,resurrect,flip)): b.setMinimumWidth(182); actions.addWidget(b,i//2,i%2)` → 2 列 × 182 + 间距 6 + 边距 18 = **388**；
- `app.py:151`：`self.side.setMaximumWidth(330)` → 侧栏永远 ≤330 < 388。

结果：`QScrollArea.widgetResizable(True)` 想缩小内容，但内容 `minimumSizeHint` 是 388，缩不动 → 横向滚动条常驻，右列按钮出画（`build/geom/main_default.png` 可直接看到「暂」「提」「翻」只剩半个字）。

### G-02 棋盘非正方形（P1）

```python
from xionghan_chess.desktop.ui.board_geometry import cell_layout
for size in ((1260,850),(1000,700),(900,680)):
    w.resize(*size); app.processEvents()
    print(size, w.board.width(), w.board.height(), "差", abs(w.board.width()-w.board.height()))
```

`BoardWidget.sizeHint()` 返回 **-1×-1（无法测量）**——它的尺寸完全由 QSplitter 分配；因此本项用「实际宽高差」判死区，用 `minimumSizeHint()=420×420` 判是否被压（三档均 ≥420，未触发下限）。

### G-03 ~ G-06 对话框把最小尺寸设成 minimumSizeHint（P1）

```python
d = TrainingDialog(); d.show(); app.processEvents()
d.resize(d.minimumWidth(), d.minimumHeight()); app.processEvents()
print(d.size().toTuple(), d.findChild(QListWidget).height())   # (274,158) → 70
```

同一模式命中 4 个：Training 70 / Library 70 / Document 80×70 / Handicap 102×70-96×70。
这些对话框的 `natural`（sizeHint）分别是 280 / 272 / 247 / 607 高，最小尺寸只给了 158 / 150 / 125 / 221 —— **给的是 Qt 的"能画出来"下限，不是"能用"下限**。

### G-07 复盘对话框最小尺寸下着法列表过窄（P1）

```python
d = ReplayDialog(Game("desktop_complete"), dict(DEFAULTS)); d.show(); app.processEvents()
d.resize(639,500); app.processEvents()
print(d.findChild(QListWidget).width(), "需要", d.findChild(QListWidget).sizeHint().width())  # 134 vs 256
```

### G-08 棋子图谱整窗被压 531px（P2）

```python
d = PieceAtlasDialog(dict(DEFAULTS)); d.show(); app.processEvents()
print(d.width(), d.sizeHint().width())        # 900 vs 1431
print(d.findChild(QTextBrowser).size().toTuple())   # 356×192
```

team-lead 已实测「右侧详情在 900 宽下只有 218（需 432）」；本项不重复，仅补充**整窗**口径：自然宽 1431，实际 900，缺 531px——说明被压的不只是详情栏，而是三栏一起压。

### G-09 对话框开得远大于内容（P2）

```python
for cls in (SettingsDialog, TrainingDialog, DocumentDialog):
    d=cls(...); d.show(); app.processEvents()
    print(cls.__name__, d.size().toTuple(), "natural", d.sizeHint().toTuple())
```

---

## 3. 最小尺寸建议

> 原则：`setMinimumSize` 不得小于 `minimumSizeHint`（硬约束），也不应等于它（软约束——Qt 的 minimumSizeHint 对列表/文本控件近乎无意义）。建议取 **`max(minimumSizeHint, min(当前声明值, 自然尺寸))`**。

| 窗口 | 现 `setMinimumSize` | 实测 `minimumSizeHint` | 建议最小值 | 依据 |
|---|---|---|---|---|
| MainWindow | 900×680 | 526×541 | **900×680（保持）** | 已满足 `≥ minimumSizeHint`；现状真正的问题是侧栏内容 388 > 侧栏上限 330（G-01），不是窗口太小。修完 G-01 后 900 宽下棋盘仍有 ~500px ≥ 420 下限 |
| SettingsDialog | 469×593 | 469×593 | **469×593（保持）** | 恰好等于自然尺寸，已是内容驱动 |
| PieceAtlasDialog | 900×640 | 876×483 | **1000×640** | 自然宽 1431 太宽；1000 时三栏各得 ~333/300/340，P2 可接受 |
| HandicapDialog | 274×221 | 274×221 | **520×480** | 自然 379×607；两列让子列表各需 ≥200 宽、≥240 高 |
| ReplayDialog | 639×500 | 639×500 | **820×560** | 列表需 256 宽 + 盘面 420 + 边距 |
| TrainingDialog | 274×158 | 274×158 | **560×420** | 列表需 ≥192 高（6 行）+ 按钮行 |
| GameLibraryDialog | 360×150 | 360×150 | **560×380** | 同上 |
| DocumentDialog | 102×125 | 102×125 | **420×360** | 正文 256×192 是最低可读，加标题/按钮 |

补充：**MainWindow 的 900×680 不是"内容装不下"，而是"侧栏装不下"**（G-01）。若按现状修 `app.py:163` 的 182 宽下限，把侧栏内容压到 ≤290，则 900×680 可以保持不动——**优先改按钮宽度，而不是继续抬窗口最小尺寸**。

---

## 4. 负向结论（已测，无需再查）

| 检查项 | 实测 | 结论 |
|---|---|---|
| 暂停遮罩两行文字（19pt 粗） | 126×72 vs 棋盘 637×567 | 放得下（最小窗口） |
| 思考遮罩单行（18pt 粗） | 120×36 vs 637×567 | 放得下 |
| 横幅「红方行棋」 | 60px vs 可用 866px | 放得下 |
| 横幅「将军 · 红方行棋」 | 112px | 放得下 |
| 横幅（中文题目最长示例） | 365px | 放得下 |
| 横幅（英文题目最长示例） | 608px | 放得下 |
| 上一轮 `PieceAtlasDialog` 760×560 下的重叠/溢出 | 现在 900×640 下 0 处 | 已随 `setMinimumSize` 提高而消失（回归记录） |

**遮罩的几何说明**：暂停/思考/结果遮罩是 `QPainter` 直接画在 `BoardWidget` 上的，**没有控件几何**，因此只能用「文字包围盒 vs 棋盘矩形」评估；上表即为该口径。它们不参与重叠/溢出判定。

---

## 5. 方法学备注（便于复核与复跑）

- 遍历范围：`findChildren(QWidget, FindDirectChildrenOnly)` 递归；只统计 `isVisible()` 且非窗口的控件。
- **排除项**（否则会产生大量假阳性，首轮实测出现过 14 条）：
  1. `QAbstractScrollArea` 内部（滚动内容本来就大于视口）——但**滚动区的 `widget()` vs `viewport()` 单列**（G-01）；
  2. `QAbstractSpinBox` / `QComboBox` 的内部 `QLineEdit`（Qt 自绘，恒比 `minimumSizeHint` 矮 3px）；
  3. `QSizeGrip`（状态栏右下角把手，几何上必然压边）。
- 重叠判定只比较**同一个 QLayout 管理**的兄弟，并跳过 `QStackedWidget`（各页天然重叠）。
- 判定阈值：重叠 > 4×4px、溢出 > 1px、挤压 < -1px，避免抗锯齿/取整噪声。
- 复现脚本：`build/geom/audit_geom2.py`（检出）、`build/geom/audit_geom4.py`（内容占比/压力测试）。截图：`build/geom/main_default.png`、`build/geom/main_min.png`。

---

## 6. 与上一轮文档的关系

- `docs/UI_AUDIT_2026-10-31.md` 的 **U-06（最小窗口 760×560 vs minHint 740）已随 1.7.5 修复**：现在 `setMinimumSize` 是 900×680、侧栏已包进 `QScrollArea`、`minimumSizeHint` 降到 526×541。**但修复方式留下了一个新问题，就是本文的 G-01**——侧栏能滚了，可内容比视口宽 99–193px，滚动条常驻。
- U-09（棋盘非正方形）在本文用三档实测坐实（G-02），严重度维持 P2→P1（因为最小窗口下死区仍有 70px）。
