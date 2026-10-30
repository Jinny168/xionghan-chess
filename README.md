# 匈汉象棋 (Xionghan Chess)

一款融合中国传统象棋与匈奴、东汉历史文化元素的创新象棋变体：**13×13 扩展盘面**，在传统七种棋子之外新增**尉、射、檑、甲、刺、楯、巡**七种特色棋子，共 14 种棋子；规则差异由可配置的规则档案描述，并同时保留传统 10×9 模式。

支持 **Windows 桌面端、Web 端与 Android 端**三种形态，三端共享同一套规则、AI、联机协议与 `.xhgame` 棋谱格式。**双人同机与人机对战可离线运行**，联机对战需自建服务端。

## 🚩 从哪开始

当前主线代码在 **[`xionghan-chess-next/`](xionghan-chess-next/)**，入口文档见 **[xionghan-chess-next/README.md](xionghan-chess-next/README.md)**（快速开始 / 三端构建 / 目录结构 / 规则要点 / 已知限制）。

## 📁 仓库结构：两棵树

| 目录 | 性质 | 说明 |
|---|---|---|
| [`xionghan-chess-next/`](xionghan-chess-next/) | ✅ **活体树（当前开发主线）** | `src/` 核心（规则 / AI / 服务）+ Web 客户端 + Android 客户端 + 测试 + 打包脚本 + 文档 |
| 仓库根其余内容 | ✅ **已收敛** | 仓库根仅保留 `README.md` / `LICENSE` / `requirements.txt` / `.github/` / `xionghan-chess-next/`；**迁移前遗留树（`desktop/`、`web/`、`docker/`、`docs/`、`handoff.md`、`DEPLOYMENT.md`）已于 2026-10-30 删除**（`108b166`，324 文件 / −53,503 行） |

> 首次访问请直接前往 [`xionghan-chess-next/README.md`](xionghan-chess-next/README.md)，其余目录可忽略。

## 📝 项目简介（对外口径）

**中文：**
匈汉象棋是一款在 13×13 扩展棋盘上进行的中国象棋变体，融合匈奴与东汉历史文化元素。除传统七种棋子外，它还引入了尉、射、檑、甲、刺、楯、巡七种特色棋子，并以可配置的规则档案适配不同玩法。项目提供 Windows 桌面端、Web 端与 Android 端三种形态，三者共享同一套规则、AI 与联机协议。双人同机与人机对战可离线运行，网络对战通过自建的 FastAPI 服务进行。

**English:**
Xionghan Chess is a Chinese chess variant played on a 13×13 expanded board, blending Xiongnu and Eastern Han historical themes. Beyond the seven traditional piece types, it adds seven special pieces — Guard, Archer, Thunder, Armor, Assassin, Shield, and Patrol — with configurable rule profiles for different modes. It ships as a Windows desktop app, a web client, and an Android app that share one rules engine, AI, and online protocol. Pass-and-play and AI games run offline; online play uses a self-hosted FastAPI server.

## 📄 许可证

MIT，详见 [LICENSE](LICENSE)。
