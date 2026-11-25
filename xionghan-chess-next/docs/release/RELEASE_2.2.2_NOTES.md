# 匈汉象棋 v2.2.2 · GitHub Release 说明

> 用途：在本地 `D:\匈汉象棋` 已打包安装完成、GitHub 连接器完成授权后，把本文件作为 Release body 发布。
> 发布目标：`Jinny168/xionghan-chess` → tag `v2.2.2`（指向已推 master 的 `752a000` 或其后的发布提交）。
> 当前仓库 GitHub Releases 页面仍停在 `v1.0.0`（2026-02-01），仅有源码包，无 exe —— 正是本次要更新的原因。

---

## Release 标题

```
v2.2.2 · 匈汉象棋（XiongHan Chess）
```

## Release body（可直接复制）

```markdown
## 匈汉象棋 2.2.2

中国象棋变体：13×13 棋盘、自定义兵种（尉/射/檑/巡）、将入敌九宫获胜、兵复活、三连吃子、射星轨。
三端共享同一套 Python 规则内核：Windows 桌面 / Web / Android WebView。

**纯本地、零采集、零账号、零联网依赖。**

### 本次更新（相对 2.2.0）

- **复盘提示不再说谎**：手机端和网页端的「只分析了前 120 手」提示此前从未真正出现（判断条件恒假），现已修好；三端同一句中性表述，恰好 120 手不误报。
- **老玩家选过的棋子外观不再被悄悄改回字形**，棋盘、设置、棋谱三处一致。
- 更高版本的设置文件不会被旧程序回写覆盖。
- 默认时长五处默认值统一；聊天框按撤销不再被棋盘快捷键抢走。
- 三端棋子规则分组改为共用一份（服务端下发，离线降级普通规则区）。
- 35 道真题新增内容型「为什么」解析，接在原有提示之后；不改题库数据、不增加章节闯关扣分。

走子、吃子、将军、将死、困毙、入宫判定的规则语义一律未动（`RULE_VERSION=3`）。
AI 强度标定、题库局面与判题逻辑未动。

### 下载

| 文件 | 说明 |
|---|---|
| `匈漢象棋-2.2.2.exe` | Windows 桌面安装包，约 61.6 MB，解压/双击即用 |

无需安装 Python，无需联网。旧版本可并存，新 exe 不会覆盖旧文件。

### 校验

- SHA-256：`18ae96f3910364771fc754b5caedf883871f18f704d1b20d24d3e1983e663c19`
- 大小：64,551,870 字节
- 版本资源：FileVersion / ProductVersion = `2.2.2.0`

详细更新日志见仓库 `docs/CHANGELOG_2.2.2.md`。
```

---

## 待上传资产

| 文件 | 本地路径 | 大小 | SHA-256 |
|---|---|---|---|
| `匈漢象棋-2.2.2.exe` | `D:\匈汉象棋\匈漢象棋-2.2.2.exe` | 64,551,870 B | `18ae96f3910364771fc754b5caedf883871f18f704d1b20d24d3e1983e663c19` |

---

## 授权后的一条命令（在 WorkBuddy 里执行）

GitHub 连接器重新授权后，用 GitHub 工具创建 Release：

- repository：`Jinny168/xionghan-chess`
- tag：`v2.2.2`（若 tag 不存在，创建时会自动建）
- target commitish：`master`（当前 `752a000`）
- body：本文件「Release body」段落的逐字内容
- assets：上表 exe

发布后用 WebFetch 核对 `https://github.com/Jinny168/xionghan-chess/releases/tag/v2.2.2`
显示 **Latest** 且 Assets 里出现 `匈漢象棋-2.2.2.exe`，才算完成。

---

## 前置状态（已核）

- [x] 本地打包安装成功（`release.py --all-local`，EXE_PROBE_OK）
- [x] exe 双副本 sha256 相同
- [x] 版本源 10 处均为 2.2.2，四元组 `(2,2,2,0)`
- [x] 代码已推 GitHub `master`
- [ ] GitHub 连接器重新授权（用户拒绝过一次，不可自动重试）
- [ ] 创建 Release + 上传 exe
- [ ] 网页核对 Latest 与 Assets
