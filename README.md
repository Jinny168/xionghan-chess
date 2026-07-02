# 匈汉象棋 (XiongHan Chess)

一个融合了中国传统象棋与中国古代匈奴与东汉历史文化元素的创新象棋变体游戏，支持桌面端和Web端双平台。

## 📁 项目结构

本项目包含两个独立的子项目：

```
xionghan-chess/
├── desktop/          # 🖥️ 桌面端应用（PyGame）
│   ├── ai/           # AI模块（传统AI + MCTS）
│   ├── assets/       # 资源文件（图片、音频、字体）
│   ├── config/       # 配置文件
│   ├── controllers/  # 控制器层
│   ├── core/         # 核心游戏逻辑
│   ├── docs/         # 桌面端文档和示例
│   ├── events/       # 事件系统
│   ├── exceptions/   # 异常定义
│   ├── lan/          # 网络对战
│   ├── tests/        # 单元测试
│   ├── ui/           # 用户界面
│   ├── utils/        # 工具函数
│   ├── main.py       # 入口文件
│   └── game.py       # 游戏主类
│
├── web/              # 🌐 Web端应用（Flask + HTML5）
│   ├── css/          # 样式文件
│   ├── docs/         # Web端文档
│   ├── js/           # JavaScript代码
│   ├── server/       # Flask后端
│   ├── images/       # 图片资源
│   ├── sounds/       # 音效文件
│   ├── index.html    # 主页
│   └── game.html     # 游戏页面
│
├── docker/           # 🐳 Docker 部署配置
│   ├── Dockerfile             # 容器镜像定义
│   ├── docker-compose.yml     # 多服务编排
│   ├── .env.example           # 环境变量模板
│   ├── .dockerignore          # 构建忽略文件
│   ├── nginx/                 # Nginx 配置
│   ├── docker-start.bat       # Windows 启动脚本
│   ├── docker-start.ps1       # PowerShell 启动脚本
│   ├── deploy.sh              # Linux 一键部署脚本
│   ├── check_deploy.sh        # 环境检查脚本
│   └── README.md              # Docker 配置说明
│
├── docs/             # 📚 项目文档中心
│   ├── README.md                      # 文档索引
│   ├── DOCKER_DEPLOY.md              # Docker 部署指南
│   ├── LINUX_DEPLOY_GUIDE.md         # Linux 部署教程
│   └── README_DOCKER.md              # Docker 快速参考
│
├── README.md           # 项目总览
├── requirements.txt    # Python 依赖
├── .gitignore          # Git 忽略配置
└── .gitattributes      # Git 属性配置
```

## 🚀 快速开始

### 桌面端

**环境要求：**
- Python 3.8+
- PyGame CE 2.5+
- NumPy
- Redis（用于MCTS AI训练，可选）

```bash
# 1. 安装依赖
cd desktop
pip install pygame pygame-ce numpy
# AI相关（可选）
pip install torch paddlepaddle

# 2. 启动游戏
python main.py
```

**打包为exe：**
```bash
cd desktop
python build_exe.py
```

### Web端

```bash
cd web
start.bat  # Windows
# 或
./start.ps1  # PowerShell
```

访问 http://localhost:5000

**Web端依赖：**
```bash
cd web/server
pip install flask flask-cors flask-socketio
```

## 🎮 功能特性

### 桌面端特性
- ✅ **丰富的游戏模式**: PVP双人对战、PVC人机对战、网络联机对战
- ✅ **智能AI系统**: 
  - 传统AI：Negamax算法 + Alpha-Beta剪枝 + 历史启发
  - MCTS AI：蒙特卡洛树搜索 + PyTorch/PaddlePaddle深度学习
- ✅ **特色棋子**: 尉、射、檑、甲、刺、盾、巡等7种独特棋子
- ✅ **扩展棋盘**: 13×13 的网格，包含楚河汉界和九宫格
- ✅ **实用功能**: 棋谱记录、悔棋系统、音效控制、主题切换
- ✅ **高级特性**: 将军提示、轨迹追踪、兵复活机制、升变系统

### Web端特性
- ✅ **跨平台支持**: 浏览器即可运行，无需安装
- ✅ **实时对战**: WebSocket通信，支持远程联机
- ✅ **响应式设计**: 自适应不同屏幕尺寸
- ✅ **暗黑模式**: 主题切换并持久化保存
- ✅ **内置聊天**: 对战时可实时交流
- ✅ **Canvas渲染**: 流畅的游戏体验

## 🎯 游戏玩法

### 基础操作
- **选择棋子**: 点击棋子进行选中，可用移动位置将高亮显示
- **移动棋子**: 点击目标位置完成移动
- **取消选择**: 再次点击已选棋子
- **特殊功能**: 
  - 悔棋按钮：撤销上一步操作
  - 设置按钮：调整游戏参数
  - 全屏切换：F11或Alt+Enter（桌面端）
  - 主题切换：在设置菜单中切换UI主题

### 胜负判定
- 将军/将死对手
- 汉/汗进入敌方九宫格
- 特殊规则胜利条件

### 快捷操作
- **聊天发送**: 输入后按 Enter 键（Web端）
- **窗口缩放**: 棋盘自动调整大小（Web端）
- **刷新页面**: 保留暗黑模式偏好（Web端）

## ⚙️ 特殊规则详解

### 棋子能力
- **汉/汗**: 可离开九宫，出宫后规则可能调整
- **仕/士**: 可扩展活动范围，可能获得额外移动能力
- **相/象**: 可过河作战，可能具备隔子攻击能力
- **兵/卒**: 拥有复活、升变、底线后退等特殊机制
- **特色棋子**: 每种特色棋子都有独特的移动和攻击规则

### 策略要点
- 利用扩展棋盘创造更多战术可能性
- 合理运用特色棋子的独特能力
- 注意控制棋盘中心和关键位置

## 🧪 测试

### 桌面端测试

```bash
cd desktop

# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_core_components.py -v

# 生成覆盖率报告
pip install pytest-cov
python -m pytest tests/ --cov=desktop --cov-report=html
```

### Web端测试

```bash
cd web/server
python app.py  # 手动测试
```

## 🔧 技术栈

### 桌面端
- **语言**: Python 3.8+
- **图形库**: PyGame CE 2.5+
- **AI框架**: PyTorch / PaddlePaddle (可选)
- **网络**: Socket编程
- **数据库**: Redis (MCTS训练)

### Web端
- **前端**: HTML5 Canvas, CSS3 Flexbox, Vanilla JavaScript ES6+
- **后端**: Flask + Flask-SocketIO + Flask-CORS
- **通信**: WebSocket
- **音频**: Web Audio API

## 📖 更多文档

### 📚 文档中心
所有文档已整理到 `docs/` 目录，请访问 [docs/README.md](docs/README.md) 查看完整文档索引。

**快速导航：**
- 🚀 **部署指南**: [docs/DEPLOY_GUIDE.md](docs/DEPLOY_GUIDE.md) - 项目部署教程
- 🐳 **Docker 部署**: [docker/README.md](docker/README.md) - Docker 完整部署指南
- ⚡ **Docker 快速参考**: [docker/INDEX.md](docker/INDEX.md) - Docker 快速开始
- 💻 **开发指南**: [web/docs/DEVELOPER_GUIDE.md](web/docs/DEVELOPER_GUIDE.md) - 开发者技术文档

### 桌面端文档
- **快速参考**: `desktop/docs/QUICK_REFERENCE.py` - API速查手册
- **实施总结**: `desktop/docs/IMPLEMENTATION_SUMMARY.md` - 架构改进记录
- **示例代码**: `desktop/docs/examples/new_features_demo.py` - 功能演示

### Web端文档
- **用户指南**: [web/README.md](web/README.md) - 使用教程和FAQ
- **开发者文档**: [web/docs/DEVELOPER_GUIDE.md](web/docs/DEVELOPER_GUIDE.md) - 技术实现和部署指南

## ⚠️ 注意事项

### 导入路径规范

**桌面端内部导入:**
```text
# 方式1：相对导入（推荐）
from .config.constants import GameConstants

# 方式2：绝对导入
from desktop.core.game_state import GameState
```

**避免跨子项目直接导入:**
```text
# ❌ 不推荐
from desktop.xxx import something

# ✅ 推荐：通过API或数据交换
```

### 资源路径

所有资源路径相对于各自的子目录：
- 桌面端：`desktop/assets/`
- Web端：`web/images/`, `web/sounds/`

### 独立运行

桌面端和Web端可以完全独立开发和部署，互不影响。

## 🤝 贡献指南

提交代码前请确保：
- [ ] 桌面端和Web端都能正常运行
- [ ] 所有测试通过 (`cd desktop && python -m pytest tests/`)
- [ ] 代码符合项目规范
- [ ] 更新了相关文档

欢迎提交Issue和Pull Request来帮助改进项目。

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 感谢所有为中国象棋文化传承做出贡献的爱好者
- 感谢开源社区提供的优质资源和工具
- 本项目由个人开发者维护，感谢社区支持

---

**最后更新**: 2026-05-06  
**项目状态**: ✅ 活跃开发中  
**版本**: v2.0 (桌面端 + Web端)