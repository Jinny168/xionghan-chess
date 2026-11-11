# 原版 Desktop 功能参考与迁移状态

本文档记录对原项目 `desktop/` 的功能审阅结果，供新版本继续迭代时查阅。原目录仅作为行为和视觉参考，新版本不直接导入旧 Pygame 规则对象，所有走棋、AI、对局状态和联机协议继续使用 `xionghan_chess.core` 与 FastAPI 服务。

## 1. 原版启动流程与模式

关键代码：

- `desktop/main.py`：主流程状态机，串联模式选择、规则设置、统计、规则阅读、阵营选择和联机入口。
- `desktop/ui/mode_selection_screen.py`：PVP、PVC、网络、设置、规则和统计入口。
- `desktop/ui/camp_selection_screen.py`：玩家阵营和 AI 难度选择。
- `desktop/game.py`：实际对局循环、AI 调度、悔棋、重开、全屏、音效和复盘入口。

新版本状态：

| 功能 | 原版实现 | 新版本状态 |
| --- | --- | --- |
| 本地人人 | PVP 模式 | 规则核心支持，桌面界面仍以人机模式为主要入口 |
| 人机对战 | PVC + 多 AI 算法 | 已实现四档难度和异步思考锁 |
| 玩家执红/执黑 | 阵营选择页 | 已实现设置下拉框 |
| 传统/经典/完整模式 | 全局配置切换 | 已改为 `RuleProfile`，棋子、布局和规则成组切换 |
| 局域网联机 | 旧 Socket/SimpleAPI | 已替换为统一 FastAPI + WebSocket 房间协议 |

## 2. 对局菜单与操作面板

原版 `desktop/ui/game_screen.py::init_menus` 提供：

- 导入棋局
- 导出棋局
- 音效设置
- 窗口切换
- 主题切换
- 统计数据
- 游戏规则
- 关于

原版可折叠操作面板还提供悔棋、重新开局、返回主菜单、退出和挑衅语句。

新版本已补齐：

- `文件 -> 导出棋局`，快捷键 `Ctrl+S`
- `文件 -> 导入棋局`，快捷键 `Ctrl+O`
- `文件 -> 打开自动保存目录`
- `对局 -> 重新开局/悔棋/复盘/认输/提和/复活兵卒`
- `设置 -> 规则与界面设置/全屏/对局统计`
- `F11` 全屏快捷键
- `帮助 -> 棋子规则/关于`

挑衅已按聊天快捷短语迁移，不占用棋盘动画层，也不改变棋局状态版本。

## 3. 棋盘绘制与交互

关键代码：`desktop/ui/chess_board.py`

原版能力：

- 13×13 匈汉棋盘与传统 9×10 棋盘
- 长城/阴山中央分隔区
- 九宫斜线、兵炮位角标、复活星位
- 选中高亮、可行点、可吃目标、最近一步轨迹
- 将军/将死脉冲提示
- 棋盘列标
- 点击落子

新版本状态：

- 已实现两种棋盘尺寸、长城/阴山规范绘制、九宫、角标、星点。
- 已实现点击与拖拽落子、选中高亮、可行点和可吃目标。
- 已实现将军棋子红色高亮。
- 新增可选背景图片叠加，透明度固定，保证网格和棋子可读性。
- 最近一步起止轨迹和独立脉冲文字提示仍待后续增强。

## 4. 规则与棋子配置

关键代码：

- `desktop/ui/settings_screen.py`
- `desktop/controllers/game_config_manager.py`
- `desktop/core/game_rules.py`
- `desktop/core/move_validator.py`

原版设置按棋子分类，允许控制汉/汗、仕/士、相/象、马、兵卒的加强能力，以及全部特色棋子的登场状态。

新版本已迁移到 `RuleOptions`：

- 汉/汗出九宫、宫内斜走、出宫后失去斜走、攻入敌宫获胜
- 仕/士出宫和出宫后直走
- 相/象过长城阴山和敌境横竖两格
- 马直走三格
- 射/䠶星点弱化或强化模式
- 兵卒复活、升变、底线后退和四向移动
- 禁止送将、三次重复和棋
- 14 类棋子独立登场开关，汉/汗强制登场

完整规则以 `docs/PIECE_RULES.md` 为准。

## 5. AI 系统

关键代码：

- `desktop/controllers/ai_manager.py`
- `desktop/ai/xionghan_chess_search_ai.py`
- `desktop/ai/xionghan_chess_mcts_ai.py`
- `desktop/ai/mcts/`

原版同时存在 Negamax/Alpha-Beta 搜索和实验性 MCTS/神经网络训练代码。训练代码依赖 Redis、PyTorch/PaddlePaddle、旧棋盘编码和旧规则函数。

新版本处理：

- 已用共享核心的合法走棋生成器重写搜索 AI。
- 提供入门、初级、中级、高级四档。
- AI 在工作线程中运行，界面锁定期间不能重复走棋。
- 超时、无合法着和异常均有回退处理。
- 原 MCTS 模型未直接迁移，因为其状态编码与当前棋子集合、规则选项和胜负条件不一致。后续接入前必须先定义共享核心的稳定训练编码和模型版本协议。

## 6. 音效与背景音乐

关键代码：`desktop/controllers/sound_manager.py`

原版包含选子、落子、吃子、将军、按钮、胜利和失败音效，以及 FC/QQ 两套循环背景音乐和独立音量。

新版本现已实现：

- Qt 原生音频播放，不依赖 Pygame mixer。
- 选子、走子、吃子、将军、胜负音效。
- FC/QQ 背景音乐切换。
- 音效开关、音乐开关、音效音量、音乐音量。
- 设置保存到 `%APPDATA%/XionghanChess/settings.json`。

## 7. 棋谱、保存与复盘

关键代码：

- `desktop/controllers/game_io_controller.py`
- `desktop/controllers/replay_controller.py`
- `desktop/ui/replay_screen.py`

原版棋谱文件名使用 `.fen`，实际内容可能是包含历史、阵亡子力、时间和局面的 JSON；复盘界面提供开局、上一步、下一步、终局和进度条。

新版本重新定义为版本化 `.xhgame` JSON：

- 保存共享 `GameState`、规则选项和全部复盘快照。
- 导入时校验格式版本，不再依赖旧棋子类名反射。
- 对局结束可自动保存到 `%APPDATA%/XionghanChess/games/`。
- 独立复盘窗口支持开局、前后步、终局和任意进度跳转。
- 旧 `.fen` 兼容导入尚未实现；需要单独编写旧棋子名称与新 `PieceType` 的迁移器。

## 8. 统计功能

关键代码：`desktop/controllers/statistics_manager.py`

原版记录总局数、胜负和棋、对局时长、吃子数量和总步数。

新版本当前记录：

- 总对局数
- 胜、负、和
- 累计走子数
- 玩家胜率
- 统计重置

数据保存到 `%APPDATA%/XionghanChess/statistics.json`。分棋子吃子统计和平均对局时长可在后续版本补充。

## 9. 网络对战

关键代码：

- `desktop/lan/network_game.py`
- `desktop/ui/network_connect_screen.py`
- `desktop/ui/network_game_screen.py`

原版支持主机/客户端、聊天、悔棋协商、重开协商、全量状态同步确认和断线检测，但协议只适用于旧 Desktop。

新版本已统一到 WebSocket 协议：

- 创建房间、输入房间号加入
- 权威状态版本号
- 非法走棋由服务器拒绝并返回最新状态
- 提和、悔棋、认输
- 断线状态和超时处理

聊天已通过统一 WebSocket `chat` 消息迁移到桌面和 Web；Android WebView 复用 Web 界面。
联机重新开局仍使用现有 `restart` 消息，后续可继续补充双方确认流程。

## 10. 其他原版功能

| 功能 | 关键代码 | 状态/建议 |
| --- | --- | --- |
| 头像 | `desktop/ui/avatar.py` | 当前使用文字阵营面板，可后续增加本地头像 |
| 挑衅语句 | `desktop/controllers/taunts_manager.py` | 已迁移为聊天快捷短语，不触发动画 |
| 将军脉冲提示 | `desktop/controllers/check_checkmate_tip_manager.py` | 当前有高亮，动画文字待增强 |
| 步数计数 | `desktop/controllers/step_counter.py` | 已由 `GameState.history` 统一承担 |
| 命令模式 | `desktop/core/commands.py` | 当前由状态快照实现悔棋，无需重复命令栈 |
| 事件总线 | `desktop/events/event_bus.py` | PySide Signal 已承担界面事件；核心保持无 UI 依赖 |
| 性能基准 | `desktop/tests/performance_benchmark.py` | 可参考，但应改为测试共享规则和 AI |

## 11. 后续优先级

建议按以下顺序继续：

1. 最近一步轨迹与将军/将死脉冲动画。
2. 旧 `.fen` 棋谱兼容迁移器。
3. 联机重新开局的双方确认流程与房间级聊天开关。
4. 统计中的平均时长、吃子分类和模式维度。
5. 可选头像与本地棋谱管理列表。
6. 为共享核心设计稳定编码后，再评估 MCTS 模型迁移。

任何规则差异应先更新 `RuleOptions`、`PIECE_RULES.md` 和规则测试，再修改客户端表现。
