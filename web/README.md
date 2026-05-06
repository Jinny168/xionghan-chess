# 匈汉象棋网页版 (XiongHan Chess Web)

基于 HTML5 Canvas 的匈汉象棋在线对战游戏，支持单机双人对战和 WebSocket 联机实时对战。

## 🚀 快速开始

### 本地运行（开发/测试）

**Windows 用户**：双击 `start.bat` 或 `start.ps1`

**手动启动**：
```bash
cd server
pip install flask flask-cors flask-socketio
python app.py
```

**访问**：http://localhost:5000

### 服务器部署

查看 [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) 的"部署指南"章节，包含：
- Linux/Windows 服务器部署
- Docker 容器化部署
- Nginx + HTTPS 配置
- 性能优化与故障排查

---

## 🎮 游戏模式

### 单机模式
- 本地同屏双人对战
- 无需网络连接
- 适合练习和测试

### 联机模式
- WebSocket 实时对战
- 创建/加入房间（8位房间号）
- 内置聊天功能
- 支持远程对弈

---

## ✨ 主要功能

### 核心玩法
- ✅ 13×13 扩展棋盘（传统为 9×10）
- ✅ 7 种特色棋子（尉、射、檑、甲、刺、盾、巡）
- ✅ 兵复活机制、升变系统
- ✅ 将军检测、绝杀判断

### 用户体验
- ✅ PyCharm 风格顶部工具栏
- ✅ 自适应棋盘大小（最大 800px）
- ✅ 暗黑模式切换（持久化保存）
- ✅ 实时倒计时系统
- ✅ 棋谱记录与回放
- ✅ 三栏布局（棋谱 | 棋盘 | 聊天）

### 音效系统
- ✅ 真实音频文件（吃子、落子、将军等）
- ✅ 背景音乐（多种风格）
- ✅ Web Audio API 合成音效（降级方案）

---

## 📁 项目结构

```
web/
├── index.html              # 主页（模式选择）
├── game.html               # 游戏页面
├── start.bat / start.ps1   # 启动脚本
├── README.md               # 用户指南（本文档）⭐
├── docs/
│   ├── README.md           # 文档导航索引
│   └── DEVELOPER_GUIDE.md  # 开发者技术文档
├── css/
│   └── style.css          # 样式文件
├── js/                     # JavaScript 代码
│   ├── controllers/       # 控制器层
│   ├── core/              # 核心逻辑层
│   ├── network/           # 网络层
│   └── ui/                # 视图层
├── images/                 # 图片资源
├── sounds/                 # 音效文件
└── server/                 # Flask 后端
    ├── app.py             # 主应用
    └── requirements.txt   # Python 依赖
```

---

## 🔧 技术栈

**前端**：HTML5 Canvas、CSS3 Flexbox、Vanilla JavaScript ES6+、Web Audio API  
**后端**：Flask、Flask-SocketIO、Flask-CORS

---

## ⚡ 性能优化

### 服务器端优化（已实施）

#### 1. 静态资源缓存
- **图片/音频/CSS/JS**: 浏览器缓存1年（`Cache-Control: max-age=31536000`）
- **HTML页面**: 不缓存，确保最新版本（`no-cache, no-store`）
- **效果**: 首次加载后，后续访问速度提升80%+

#### 2. WebSocket连接优化
- **Ping/Pong机制**: 25秒间隔，60秒超时，自动检测断线
- **异步模式**: 自动选择最优异步后端（gevent > eventlet > threading）
- **缓冲区限制**: 最大1MB，防止内存溢出

#### 3. 日志优化
- **开发模式**: 显示详细连接/断开日志
- **生产模式**: 仅记录错误，减少I/O开销
- **Werkzeug日志**: 降级为WARNING级别

#### 4. 频率限制
- **移动操作**: 最小间隔100ms，防止刷屏
- **IP限流**: 每IP最多5个并发连接
- **消息长度**: 聊天消息限制200字符

### 前端优化建议

#### 1. 资源加载
```javascript
// 已实现：版本号控制，强制刷新缓存
<script src="/js/main.js?v=11"></script>

// 建议：懒加载非关键资源
const loadSound = (name) => {
    return new Audio(`/sounds/${name}.wav`);
};
```

#### 2. Canvas渲染优化
- ✅ 已使用离屏Canvas预渲染棋子
- ✅ 只在需要时重绘（requestAnimationFrame）
- 💡 建议：降低帧率到30FPS（游戏足够流畅）

#### 3. 网络优化
- ✅ WebSocket实时通信（比HTTP轮询高效）
- ✅ 只发送移动数据，不传输完整状态
- 💡 建议：压缩JSON数据（使用MessagePack）

### 部署优化指南

#### 开发环境
```bash
cd server
python app.py  # debug=True，详细日志
```

#### 生产环境
```bash
# 1. 安装高性能异步后端
pip install gevent gunicorn

# 2. 关闭debug模式，使用gunicorn启动
gunicorn -k gevent -w 4 -b 0.0.0.0:5000 server.app:app

# 3. 或使用Nginx反向代理（推荐）
# Nginx配置见 docs/DEVELOPER_GUIDE.md
```

#### 性能监控
```python
# 在 app.py 中添加性能监控
import time
from functools import wraps

def track_performance(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        if duration > 0.1:  # 超过100ms的请求
            print(f"[SLOW] {f.__name__}: {duration:.3f}s")
        return result
    return decorated_function
```

---

## 🎯 使用指南

### 基本操作
- **选择棋子**：点击己方棋子
- **移动棋子**：点击目标位置
- **取消选择**：再次点击已选棋子
- **悔棋**：点击工具栏 ↩️ 按钮（至少需有一步）

### 工具栏功能
- 🎮 **新的对局** - 开始全新游戏
- ↩️ **悔棋** - 撤销上一步
- 🔄 **重新开始** - 重置当前棋盘
- 🏳️ **认输** - 主动结束本局
- ⚙️ **游戏设置** - 音效控制
- ❓ **帮助说明** - 使用指南
- ☀️ **暗黑模式** - 切换主题

### 快捷操作
- **聊天发送**：输入后按 Enter 键
- **窗口缩放**：棋盘自动调整大小
- **刷新页面**：保留暗黑模式偏好

---

## ❓ 常见问题

**Q: 如何切换游戏模式？**  
A: 在主页选择不同的模式卡片即可。

**Q: 联机对战如何创建房间？**  
A: 点击"联机双人对战" → "创建房间"，系统会生成 8 位房间号。

**Q: 连接失败怎么办？**  
A: 确保服务器正在运行，检查防火墙设置，浏览器控制台(F12)查看错误信息。

**Q: 推荐使用什么浏览器？**  
A: Chrome 90+ / Firefox 88+ / Safari 14+ / Edge 90+

**Q: 音效无法播放？**  
A: 首次播放需要用户交互（点击任意按钮），这是浏览器的安全策略。

---

## 📝 游戏规则简介

匈汉象棋在传统中国象棋基础上进行了创新：

- **棋盘**：13×13 扩展棋盘（传统为 9×10）
- **特色棋子**：尉、射、檑、甲、刺、盾、巡（7种）
- **特殊机制**：兵复活、升变系统、长城阴山区域

详见桌面版项目文档获取完整规则说明。

---

## 📚 更多文档

- **用户指南**：本文档（README.md）
- **开发者文档**：[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) - 技术实现、部署指南、架构设计

---

## 🎉 总结

匈汉象棋 Web 版拥有专业级的用户体验：

✅ **功能完备** - 所有核心功能一应俱全  
✅ **界面美观** - PyCharm 风格工具栏 + 暗黑模式  
✅ **性能优秀** - Canvas 渲染 + 静态图片资源  
✅ **易于使用** - 直观的操作 + 详细的帮助  
✅ **扩展灵活** - 模块化设计 + 清晰的代码结构  

**Enjoy the Game! 🎊**
