# 5 主题渲染基线

5 张 PNG（classic / green / blue / purple / dark，1260×850），是 `scripts/theme_pixel_baseline.py`
的 `--check` 基线，服务 A-2/B 阶段的"零视觉变化"判据。

## 存储：走 Git LFS
根 `.gitattributes` 已有 `*.png filter=lfs` 规则（52 条 LFS 规则之一），
所以仓库里存的是**指针**，2 MB 不进主历史：
```
$ git check-attr diff merge text -- benchmarks/theme_pixels/classic.png
diff: lfs / merge: lfs / text: unset
$ git show HEAD:…/classic.png | head -c 40
version https://git-lfs.github.com/spec/
```
⚠️ **`git archive` 导出时这些 PNG 会变成指针**（发布流程必须按 `git ls-files` 从工作区复制，
否则图片全裂 —— 与网页版发布图片裂图是同一个原因）。

## 重新生成
```
python scripts/theme_pixel_baseline.py --write
```
换机器（字体/DPI 不同）前，先跑 `--noise` 重测噪声底，再决定是否重写基线。

## 区域定义（`--diff-report`）
| 区域 | 对应控件 | 几何来源 |
|---|---|---|
| `标题栏` | 窗口顶部条（宽度取整窗，高度到棋盘/侧栏顶边） | `(0, 0, window.w, min(board.top, side.top))` |
| `横幅` | `MainWindow.banner`（QSS `#banner`，**浮在棋盘上方**） | 控件 `mapTo(window)` 后的矩形 |
| `棋盘` | `MainWindow.board`（BoardWidget） | 同上 |
| `侧栏` | `MainWindow.side`（QScrollArea，宽 330） | 同上 |
| `其它` | 棋盘外阴影与留白 | 不属于以上任何矩形 |

**判定顺序：横幅 → 棋盘 → 侧栏 → 标题栏 → 其它。** 横幅必须优先，
否则它按几何落在棋盘矩形里，"将军色改到横幅"会被误报成"棋盘变了"（这个坑踩过）。

## 两种状态
| 基线 | 命令 | 用途 |
|---|---|---|
| `<theme>.png` | `--check` | 初始局面 |
| `<theme>_check.png` | `--check --state=check` | **将军态**（`#b21f1f` 只在将军时渲染） |

将军态夹具：黑王 `(0,4)`、红车 `(0,10)` 沿第 0 行打将、轮到黑走（`_check_game()`），固定不随机。

## 基线里不允许出现"随时间变化的内容"

**判据**：基线截图里不得包含时钟、动画、随机种子等随时间/随机的元素。
若无法消除，必须**点名是哪个元素**并在报告里单列该区域——**不许**用"容差"糊住。

本工具的处理：`_freeze_clock()` 在抓图前
1. 停掉窗口内所有 `QTimer`（`self.timer` 每 250ms 触发 `refresh()`）；
2. 把 `game.tick` 打成空操作（否则 `refresh()` 仍会按真实时间扣钟）；
3. 钉死 `game.state.clocks_ms = {RED: 20min, BLACK: 20min}`。

之后 `--noise` 与 `--check` 均为 **0**。`NOISE_FLOOR` 保持全 0——
**不要为了"让测试过"调大它**，那等于给真实回归开后门。
调试需要动态界面时可用 `--no-freeze`（此时不做零差异断言）。

## 变更记录

### 2026-11-01 · 将军态基线随 B-1 更新
B-1 把将军横幅的文字色从 `#b21f1f` 改成主题的 `banner_fg`（浅色白字 / 暗色 `#410002`）。
原因：横幅底色本来就是 `#7f1d1d`（U-15 的 danger-surface），而文字也是深红 —— 实测 **1.48:1**，
深红压深红。改后 10.02:1（浅色）/ 10.03:1（暗色），符合审计 §5。

因此 `<theme>_check.png` 五张**全部重生成**（初始态基线未动，因为该样式只在将军态生效）。

## 变更记录

### 2026-11-01 · 将军态基线随 B-1 更新
B-1 把将军横幅的文字色从 `#b21f1f` 改成主题的 `banner_fg`（浅色白字 / 暗色 `#410002`）。
原因：横幅底色本来就是 `#7f1d1d`（U-15 的 danger-surface），而文字也是深红 —— 实测 **1.48:1**，
深红压深红。改后 10.02:1（浅色）/ 10.03:1（暗色），符合审计 §5。

因此 `<theme>_check.png` 五张**全部重生成**（初始态基线未动，因为该样式只在将军态生效）。
