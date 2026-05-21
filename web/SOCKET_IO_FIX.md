# Socket.IO 连接问题解决方案

## 问题描述
浏览器控制台报错：
```
socket.io.min.js:1 Failed to load resource: net::ERR_PROXY_CONNECTION_FAILED
websocket-client.js?v=15:27 Socket.IO库未加载，请检查HTML中是否包含socket.io.js
```

这是因为网络代理无法访问 CDN 导致的。

## 已实施的自动修复

### 1. 多 CDN 备用方案
已在 `game.html` 中配置了三个备用 CDN 源：
- 主 CDN: `https://cdn.socket.io/4.7.5/socket.io.min.js`
- 备用1: `https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js`
- 备用2: `/socket.io.min.js` (本地服务器)

### 2. Flask 服务器重定向
在 `server/app.py` 中添加了 `/socket.io.min.js` 路由，会重定向到可靠的 Cloudflare CDN。

## 如果问题仍然存在

### 方案一：使用下载工具（最简单）

1. 打开浏览器访问：`http://localhost:5000/download-socketio.html`
2. 点击"📥 下载 Socket.IO"按钮
3. 将下载的 `socket.io.min.js` 文件移动到 `web/js/network/` 目录
4. 刷新游戏页面

### 方案二：手动下载

1. 访问以下任一链接下载文件：
   - [Cloudflare CDN](https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js)
   - [unpkg CDN](https://unpkg.com/socket.io-client@4.7.5/dist/socket.io.min.js)
   - [jsDelivr CDN](https://cdn.jsdelivr.net/npm/socket.io-client@4.7.5/dist/socket.io.min.js)

2. 右键点击页面 → "另存为" → 保存为 `socket.io.min.js`

3. 将文件复制到项目目录：
   ```
   web/js/network/socket.io.min.js
   ```

4. 修改 `game.html` 第 10-18 行，改为直接引用本地文件：
   ```html
   <!-- 引入Socket.IO客户端库（本地文件） -->
   <script src="js/network/socket.io.min.js"></script>
   ```

5. 刷新游戏页面

### 方案三：使用 npm 安装（适合开发者）

1. 打开终端，进入项目根目录：
   ```powershell
   cd C:\Users\27415\PycharmProjects\xionghan-chess
   ```

2. 初始化 npm（如果还没有 package.json）：
   ```powershell
   npm init -y
   ```

3. 安装 socket.io-client：
   ```powershell
   npm install socket.io-client@4.7.5
   ```

4. 复制文件到项目目录：
   ```powershell
   Copy-Item node_modules\socket.io-client\dist\socket.io.min.js web\js\network\socket.io.min.js
   ```

5. 修改 `game.html` 引用本地文件（同方案二第4步）

6. 刷新游戏页面

## 验证修复

1. 启动 Flask 服务器：
   ```powershell
   cd web\server
   python app.py
   ```

2. 打开浏览器访问：`http://localhost:5000/game.html?mode=online&room=YOUR_ROOM_ID`

3. 打开浏览器开发者工具（F12），查看 Console 标签：
   - ✅ 成功：应该看到 "正在连接房间: XXXX" 且没有 "Socket.IO库未加载" 错误
   - ❌ 失败：如果仍有错误，请检查 Network 标签中 `socket.io.min.js` 的加载状态

## 常见问题

### Q: 为什么会有代理错误？
A: 某些网络环境（公司内网、学校网络等）可能限制了对外部 CDN 的访问，或者需要配置代理。

### Q: 使用本地文件有什么优缺点？
优点：
- 不依赖外部网络
- 加载速度更快
- 更稳定可靠

缺点：
- 需要手动更新版本
- 增加项目文件大小

### Q: 如何更新 Socket.IO 版本？
如果使用本地文件，需要重新下载新版本并替换旧文件。建议关注 [Socket.IO 官方发布](https://github.com/socketio/socket.io/releases)。

## 技术说明

### 当前架构
```
浏览器
  ↓
game.html (尝试多个 CDN)
  ↓
Flask Server (重定向到 CDN)
  ↓
CDN 提供商 (Cloudflare 等)
```

### 优化后的架构（使用本地文件）
```
浏览器
  ↓
game.html
  ↓
本地文件 (web/js/network/socket.io.min.js)
```

## 相关文件

- `web/game.html` - 游戏页面，包含 Socket.IO 引用
- `web/server/app.py` - Flask 服务器，提供重定向路由
- `web/js/network/websocket-client.js` - WebSocket 客户端封装
- `web/download-socketio.html` - 下载工具页面
- `web/SOCKET_IO_FIX.md` - 本文档
