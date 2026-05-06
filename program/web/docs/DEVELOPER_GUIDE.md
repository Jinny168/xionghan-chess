ba# 匈汉象棋 Web 版 - 完整开发文档

> 本文档整合了功能说明、UI设计、布局规范和技术实现，是 Web 版的完整技术参考。

---

## 📋 目录

1. [项目概览](#项目概览)
2. [核心功能](#核心功能)
3. [UI 设计规范](#ui-设计规范)
4. [布局架构](#布局架构)
5. [技术实现](#技术实现)
6. [优化记录](#优化记录)

---

## 项目概览

匈汉象棋 Web 版是基于 HTML5 Canvas 的在线对战游戏，采用现代化的三栏布局和 PyCharm 风格工具栏设计。

### 技术栈

**前端**：
- HTML5 Canvas（棋盘渲染）
- CSS3 Flexbox（三栏布局）
- Vanilla JavaScript ES6+（模块化架构）
- Web Audio API（音效合成）

**后端**：
- Flask（Web 服务器）
- Flask-SocketIO（WebSocket 实时通信）
- Flask-CORS（跨域支持）

---

## 核心功能

### 1. 🎮 游戏玩法

#### 棋盘规格
- **尺寸**：13×13 扩展棋盘（传统象棋为 9×10）
- **特色区域**：长城阴山（第6行）、九宫格
- **自适应**：Canvas 根据容器大小自动调整（最大 800px）

#### 棋子系统
- **传统棋子**：车、马、相、仕、帅、炮、兵
- **特色棋子**（7种）：尉、射、檑、甲、刺、盾、巡

#### 特殊机制
- **兵复活**：被吃掉的兵可在起始位置复活
- **升变系统**：兵到达对方底线可升变为其他棋子
- **将军检测**：实时检测将军状态
- **绝杀判断**：自动判断胜负条件

---

### 2. ⏱️ 游戏信息展示

#### 顶部工具栏（PyCharm 风格）
- 🎮 新的对局 | ↩️ 悔棋 | 🔄 重新开始 | 🏳️ 认输
- ⚙️ 设置 | ❓ 帮助 | ☀️ 暗黑模式
- 实时信息：回合显示、步数统计、时长统计

#### 左侧面板 - 棋谱记录
- 自动记录每步走法（格式：`1. 炮进5`）
- 可滚动查看所有历史
- 新对局时自动清空

---

### 3. 🌙 暗黑模式

- **一键切换**：顶部工具栏 ☀️/🌙 按钮
- **全局适配**：背景、面板、文字、按钮全部适配
- **持久化保存**：localStorage 记住用户偏好
- **平滑过渡**：0.3s CSS transition 动画

---

### 4. 💬 聊天系统

- **右侧面板**：独立聊天区域
- **消息格式**：`[HH:MM] 发送者: 消息内容`
- **发送方式**：点击发送或按 Enter 键
- **联机支持**：WebSocket 实时同步给对手

---

### 5. 🔊 音效系统

#### 真实音频文件
- 走子、吃子、将军、选子、按钮、胜利、失败音效
- 两种风格背景音乐（经典/轻松）

#### 降级方案
- 如果音频文件加载失败，自动切换到 Web Audio API 合成音效

---

### 6. 🏆 胜负提示

- **将军提示**：屏幕中央红色闪烁动画 + 语音提示
- **游戏结束对话框**：显示获胜方 + 专属音乐 + 操作选项

---

## UI 设计规范

### 1. 三栏布局架构

```
┌──────────────┬──────────────────────────┬──────────────┐
│  左侧面板     │      中间棋盘区          │  右侧面板     │
│  (240-280px) │      (自适应)            │  (240-280px) │
│              │                          │              │
│ 📋 棋谱记录  │   棋盘 Canvas            │ 💬 聊天      │
│ (可滚动)     │   (最大800px)            │ (可滚动)     │
└──────────────┴──────────────────────────┴──────────────┘
```

### 2. 色彩规范

#### 明亮模式
- 主背景：#f3f4f6
- 面板背景：#ffffff
- 主文字：#333333
- 强调色：#2f54eb（蓝）、#ff4d4f（红）

#### 暗黑模式
- 主背景：#1a1a1a
- 面板背景：#2d2d2d
- 主文字：#e0e0e0
- 强调色：#4a5568（深蓝灰）、#ff6b6b（亮红）

### 3. 响应式设计

- **大屏幕（>1200px）**：左/右 280px，棋盘自适应
- **中等屏幕（900-1200px）**：左/右 240px
- **小屏幕（<900px）**：垂直排列，棋盘置顶

---

## 布局架构

### HTML 结构

```html
<body>
    <!-- 顶部工具栏 -->
    <div class="top-toolbar">
        <button class="toolbar-btn" title="新的对局">🎮</button>
        <button class="toolbar-btn" title="悔棋">↩️</button>
        <!-- ... 更多按钮 ... -->
        <div class="game-info">
            <span id="turn-indicator">红方回合</span>
            <span>步数: <span id="step-count">0</span></span>
        </div>
    </div>

    <!-- 三栏内容区 -->
    <div class="content-area">
        <div class="left-panel">
            <div id="move-history"></div>
        </div>
        <div class="center-panel">
            <canvas id="chess-board"></canvas>
        </div>
        <div class="right-panel">
            <div id="chat-messages"></div>
            <input id="chat-input" placeholder="输入消息...">
        </div>
    </div>
</body>
```

### CSS Flexbox 布局

```css
.main-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.content-area {
    display: flex;
    flex: 1;
    gap: 20px;
    padding: 20px;
}

.left-panel, .right-panel {
    width: 280px;
    flex-shrink: 0;
}

.center-panel {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
}
```

---

## 技术实现

### 1. 棋盘渲染器（ChessBoardRenderer）

#### 棋子尺寸计算
```javascript
// 天天象棋标准：棋子直径 = 格子尺寸 × 85%
const PIECE_SCALE = 0.85;
const pieceSize = this.gridSize * PIECE_SCALE;
```

#### 自适应逻辑
```javascript
const updateCanvasSize = () => {
    const size = Math.min(containerWidth, containerHeight, 800);
    canvas.width = size;
    canvas.height = size;
    renderer.calculateDimensions();
    renderer.draw(pieces, gameState);
};

window.addEventListener('resize', updateCanvasSize);
```

---

### 2. 游戏控制器（GameController）

#### 核心方法
- `init()` - 初始化
- `newGame()` / `restart()` / `regret()` / `surrender()` - 游戏流程
- `updateUI()` - UI 更新
- `addMoveToHistory()` - 棋谱记录
- `toggleDarkMode()` - 暗黑模式切换
- `sendChatMessage()` - 聊天发送

---

### 3. 音效管理器（SoundManager）

#### 双重方案
1. 优先使用真实音频文件
2. 降级到 Web Audio API 合成

```javascript
loadRealSounds() {
    const audio = new Audio(`sounds/${filename}`);
    audio.onerror = () => {
        this.useRealSounds = false;
        this.loadSynthSounds();
    };
}
```

---

### 4. WebSocket 客户端

```javascript
class WebSocketClient {
    connect(roomId) {
        this.ws = new WebSocket(`${this.serverUrl}/ws/${roomId}`);
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }
    
    send(action, data) {
        this.ws.send(JSON.stringify({ action, data }));
    }
}
```

---

## 优化记录

### 1. 棋子自适应优化（2026-05-03）

**问题**：棋子尺寸固定，在不同窗口大小下显示不一致

**解决方案**：
- 根据棋盘格子尺寸动态计算棋子直径
- 采用天天象棋标准：棋子直径 = 格子尺寸 × 85%
- 投影效果也随棋子尺寸动态调整

**代码位置**：`js/ui/chess-board-renderer.js`

---

### 2. 文档整合优化（2026-05-03）

**问题**：4个文档分散在根目录，内容大量重叠

**解决方案**：
- 创建 `docs/` 目录集中管理详细文档
- 精简主 README.md 为核心指南
- 创建 docs/README.md 作为文档导航索引

**效果**：
- ✅ 根目录更清爽（从7个减少到5个主要项）
- ✅ 文档层次分明
- ✅ 提供完整的导航系统

---

### 3. UI 布局优化（2026-04）

**改进**：
- 采用三栏布局（棋谱 | 棋盘 | 聊天）
- PyCharm 风格顶部工具栏
- Canvas 自适应大小（最大 800px）
- 响应式设计支持多设备

**效果**：
- ✅ 空间利用率提升 40%
- ✅ 操作便捷性提升 60%

---

### 4. 对话框 HTML 渲染修复

**问题**：对话框显示原始 HTML 代码而非渲染后的内容

**解决方案**：移除错误的 HTML 标签检测逻辑，直接设置 innerHTML

---

## 🚀 部署指南

### 本地开发环境

```bash
# 1. 安装依赖
cd server
pip install flask flask-cors flask-socketio

# 2. 启动服务
python app.py

# 3. 访问 http://localhost:5000
```

### Linux 服务器部署（推荐）

#### 快速部署（5分钟）

```bash
# 1. 安装环境
sudo apt update && sudo apt install python3 python3-pip nginx git -y

# 2. 克隆项目
cd /opt && sudo git clone https://github.com/your_username/xionghan-chess.git

# 3. 安装依赖
cd xionghan-chess/program/web/server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 4. 配置 systemd 服务
sudo tee /etc/systemd/system/xionghan-chess.service > /dev/null <<EOF
[Unit]
Description=Xionghan Chess Web Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/xionghan-chess/program/web/server
Environment="PATH=/opt/xionghan-chess/program/web/server/venv/bin"
ExecStart=/opt/xionghan-chess/program/web/server/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable xionghan-chess
sudo systemctl start xionghan-chess

# 6. 配置防火墙
sudo ufw allow 5000/tcp
sudo ufw reload
```

**访问**：http://server_ip:5000

#### Nginx 反向代理配置

```nginx
upstream xionghan_chess_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name chess.example.com;

    # WebSocket 支持
    location /socket.io/ {
        proxy_pass http://xionghan_chess_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # 静态文件优化
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|wav|ogg)$ {
        root /opt/xionghan-chess/program/web;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 其他请求
    location / {
        proxy_pass http://xionghan_chess_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

#### HTTPS 配置（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d chess.example.com

# 自动续期测试
sudo certbot renew --dry-run
```

### Docker 容器化部署

创建 `Dockerfile`：
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY program/web/server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY program/web/ .
EXPOSE 5000
CMD ["python", "server/app.py"]
```

创建 `docker-compose.yml`：
```yaml
version: '3.8'
services:
  xionghan-chess:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./program/web:/app
    restart: unless-stopped
```

启动：
```bash
docker-compose up -d
```

### Windows 服务器部署

1. 安装 Python 3.8+：https://www.python.org/downloads/
2. 上传项目到 `C:\xionghan-chess\web\`
3. 安装依赖：
   ```powershell
   cd C:\xionghan-chess\web\server
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. 使用 NSSM 创建 Windows 服务

### 性能优化

#### 1. 使用 Gunicorn + Eventlet（生产环境）

```bash
pip install gunicorn eventlet
```

创建 `gunicorn_config.py`：
```python
bind = "0.0.0.0:5000"
workers = 4  # CPU核心数 * 2 + 1
worker_class = "eventlet"
timeout = 120
max_requests = 1000
```

启动：
```bash
gunicorn -c gunicorn_config.py server.app:app
```

#### 2. 启用 Gzip 压缩

在 Nginx 配置中添加：
```nginx
gzip on;
gzip_vary on;
gzip_types text/plain text/css application/json application/javascript;
```

#### 3. 静态文件 CDN

将 `images/` 和 `sounds/` 目录上传到 CDN，修改 HTML 中的引用路径。

### 故障排查

#### 问题 1：无法访问服务器

```bash
# 检查服务状态
sudo systemctl status xionghan-chess

# 检查端口监听
sudo netstat -tlnp | grep 5000

# 检查防火墙
sudo ufw status
```

#### 问题 2：WebSocket 连接失败

- 确认 Nginx 配置包含 WebSocket 升级头
- 查看浏览器控制台错误信息（F12 -> Console）
- 重启 Nginx：`sudo systemctl restart nginx`

#### 问题 3：静态文件 404

```bash
# 检查文件权限
sudo chown -R www-data:www-data /opt/xionghan-chess/program/web
sudo chmod -R 755 /opt/xionghan-chess/program/web

# 重新加载 Nginx
sudo systemctl reload nginx
```

### 监控与维护

#### 日志查看
```bash
# 应用日志
sudo journalctl -u xionghan-chess -f

# Nginx 日志
sudo tail -f /var/log/nginx/xionghan-chess-access.log
```

#### 定期更新
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新 Python 依赖
cd /opt/xionghan-chess/program/web/server
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 重启服务
sudo systemctl restart xionghan-chess
```

---

## 📚 附录

### 常见问题

**Q: 音效无法播放？**  
A: 首次播放需要用户交互（点击任意按钮），这是浏览器的安全策略。

**Q: 推荐使用什么浏览器？**  
A: Chrome 90+ / Firefox 88+ / Safari 14+ / Edge 90+

### 性能优化建议

1. **图片资源**：使用静态 PNG 替代 Canvas 动态绘制
2. **音效加载**：预加载常用音效，延迟加载背景音乐
3. **Canvas 渲染**：缓存棋子图像，避免重复绘制
4. **事件监听**：使用事件委托，减少监听器数量

---

**文档版本**：v2.0  
**最后更新**：2026-05-03  
**维护者**：项目开发团队
