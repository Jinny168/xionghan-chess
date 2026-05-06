# 项目结构说明

本项目包含两个独立的子项目：桌面端应用和Web端应用。

## 📁 目录结构

```
xionghan-chess/
├── desktop/          # 桌面端应用（PyGame）
│   ├── ai/           # AI模块
│   ├── assets/       # 资源文件（图片、音频、字体）
│   ├── config/       # 配置文件
│   ├── controllers/  # 控制器层
│   ├── core/         # 核心游戏逻辑
│   ├── events/       # 事件系统
│   ├── exceptions/   # 异常定义
│   ├── lan/          # 网络对战
│   ├── ui/           # 用户界面
│   ├── utils/        # 工具函数
│   ├── main.py       # 桌面端入口
│   └── game.py       # 游戏主类
│
├── web/              # Web端应用（Flask + HTML5）
│   ├── css/          # 样式文件
│   ├── js/           # JavaScript代码
│   ├── server/       # Flask后端
│   ├── images/       # 图片资源
│   ├── sounds/       # 音效文件
│   ├── index.html    # 主页
│   └── game.html     # 游戏页面
│
└── docs/             # 项目文档
```

## 🚀 快速开始

### 桌面端

```bash
cd desktop
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

## 🎮 功能特性

### 桌面端特性
- ✅ PyGame图形界面
- ✅ 完整的AI对战系统
- ✅ 本地双人对战
- ✅ 网络联机对战
- ✅ 棋谱记录与回放
- ✅ 丰富的音效和视觉效果

### Web端特性
- ✅ HTML5 Canvas渲染
- ✅ WebSocket实时对战
- ✅ 响应式设计
- ✅ 暗黑模式
- ✅ 内置聊天功能
- ✅ 跨平台支持

## 📝 开发指南

### 依赖安装

**桌面端依赖：**
```bash
cd desktop
pip install pygame pygame-ce numpy
# AI相关（可选）
pip install torch paddlepaddle
```

**Web端依赖：**
```bash
cd web/server
pip install flask flask-cors flask-socketio
```

### 运行测试

```bash
# 桌面端测试
cd desktop
python -m pytest tests/

# Web端测试
cd web/server
python app.py  # 手动测试
```

## 🔧 技术栈

### 桌面端
- **语言**: Python 3.8+
- **图形库**: PyGame CE 2.5+
- **AI框架**: PyTorch / PaddlePaddle (可选)
- **网络**: Socket编程

### Web端
- **前端**: HTML5, CSS3, Vanilla JavaScript
- **后端**: Flask + Flask-SocketIO
- **通信**: WebSocket
- **渲染**: Canvas API

## 📖 更多文档

- 桌面端详细文档: `desktop/README.md` (待创建)
- Web端用户指南: `web/README.md`
- Web端开发者文档: `web/docs/DEVELOPER_GUIDE.md`
- 项目总体说明: `README.md`

## ⚠️ 注意事项

1. **导入路径**: 桌面端使用 `desktop.xxx` 作为包名前缀
2. **资源路径**: 所有资源路径相对于各自的子目录
3. **独立运行**: 桌面端和Web端可以独立开发和部署
4. **共享资源**: 如需共享资源，请放在项目根目录的 `shared/` 目录（待创建）

## 🤝 贡献指南

提交代码前请确保：
- [ ] 桌面端和Web端都能正常运行
- [ ] 所有测试通过
- [ ] 代码符合项目规范
- [ ] 更新了相关文档

---

**Enjoy Coding! 🎉**
