# 雄汉象棋 - 部署指南

## 🚀 开发环境部署 (Windows)

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务器
```bash
python app.py
```

访问: http://localhost:5000

---

## 🏭 生产环境部署 (Linux/Mac)

### 方案一: Gunicorn + Gevent (推荐)

#### 1. 安装依赖
```bash
pip install gunicorn gevent flask-socketio flask-cors redis python-socketio
```

#### 2. 启动命令
```bash
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         -w 4 \
         --bind 0.0.0.0:5000 \
         --timeout 120 \
         app:app
```

#### 3. 使用环境变量配置
```bash
export REDIS_HOST=your-redis-host
export REDIS_PORT=6379
export REDIS_PASSWORD=your-password
export FLASK_ENV=production

gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         -w 4 \
         --bind 0.0.0.0:5000 \
         --timeout 120 \
         app:app
```

---

### 方案二: Nginx + Gunicorn (高并发)

#### 1. Nginx 配置 (`/etc/nginx/sites-available/xionghan-chess`)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### 2. 启动 Gunicorn
```bash
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         -w 4 \
         --bind 127.0.0.1:5000 \
         --timeout 120 \
         app:app
```

#### 3. 重启 Nginx
```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🐳 Docker 部署

### 1. Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn gevent

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", 
     "-w", "4", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]
```

### 2. docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - FLASK_ENV=production
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

### 3. 启动
```bash
docker-compose up -d
```

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_HOST` | Redis 主机地址 | localhost |
| `REDIS_PORT` | Redis 端口 | 6379 |
| `REDIS_PASSWORD` | Redis 密码 | (空) |
| `REDIS_DB` | Redis 数据库编号 | 0 |
| `FLASK_ENV` | 运行环境 | development |

---

## 🔧 性能优化建议

### 1. Worker 数量
```bash
# 推荐公式: (2 × CPU核心数) + 1
# 例如: 4核CPU → 9个worker
gunicorn -w 9 ...
```

### 2. 线程模式选择

| 环境 | 推荐模式 | 说明 |
|------|----------|------|
| Windows开发 | threading | 无需额外依赖 |
| Linux生产 | gevent | 高性能异步IO |
| 超高并发 | gevent + Redis | 多进程+消息队列 |

### 3. Redis 优化
- 启用持久化 (RDB/AOF)
- 设置合理的过期时间
- 监控内存使用

---

## 📊 监控与维护

### 健康检查端点
添加以下代码到 `app.py`:
```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'redis_connected': USE_REDIS
    })
```

### 日志管理
```bash
# Gunicorn 日志配置
gunicorn --access-logfile access.log \
         --error-logfile error.log \
         --log-level info \
         app:app
```

---

## ❓ 常见问题

### Q1: Windows上无法使用gevent?
**A:** Gevent在Windows上支持有限,建议使用:
- 开发环境: threading模式(当前配置)
- 生产环境: 使用WSL2或Linux服务器

### Q2: 如何处理大量并发连接?
**A:** 
1. 使用gevent替代threading
2. 增加worker数量
3. 使用Redis作为消息后端
4. 前端实现连接池

### Q3: WebSocket连接断开频繁?
**A:** 
1. 检查防火墙/代理配置
2. 调整ping_timeout和ping_interval
3. 确保Nginx正确配置Upgrade头

---

## 🔐 安全建议

1. **启用HTTPS**: 使用Let's Encrypt免费证书
2. **限制CORS**: 修改为特定域名
   ```python
   CORS(app, origins=['https://your-domain.com'])
   ```
3. **Redis认证**: 始终设置密码
4. **速率限制**: 已实现IP限流,可根据需要调整

---

## 📝 更新日志

- **2024-XX-XX**: 移除eventlet,改用threading模式
- **后续计划**: 迁移到FastAPI + asyncio
