# Docker 目录说明

## 📁 目录结构

```
docker/
├── config/                    # 配置文件目录
│   ├── Dockerfile            # Flask 应用容器定义
│   ├── docker-compose.yml    # 多服务编排配置
│   ├── .env.example          # 环境变量模板（复制为 .env 使用）
│   ├── .dockerignore         # Docker 构建忽略规则
│   └── nginx/                # Nginx 配置
│       └── nginx.conf        # Nginx 反向代理配置
│
├── scripts/                   # 部署脚本目录
│   ├── windows/              # Windows 平台脚本
│   │   ├── docker-start.bat  # 批处理启动脚本
│   │   └── docker-start.ps1  # PowerShell 启动脚本（推荐）
│   └── linux/                # Linux 平台脚本
│       ├── deploy.sh         # 一键部署脚本
│       └── check-env.sh      # 环境检查脚本
│
└── README.md                 # 详细使用说明文档
```

## 🎯 快速开始

### Windows 用户
```powershell
cd docker/scripts/windows
.\docker-start.ps1
```

### Linux 用户
```bash
cd docker/scripts/linux
chmod +x *.sh
sudo ./deploy.sh
```

## 📖 详细说明

完整的使用说明请查看 [README.md](README.md)

## 🔧 常用路径

- **配置文件**: `docker/config/`
- **环境变量**: `docker/config/.env`（从 .env.example 复制）
- **Windows 脚本**: `docker/scripts/windows/`
- **Linux 脚本**: `docker/scripts/linux/`
- **Nginx 配置**: `docker/config/nginx/nginx.conf`

---

**整理日期**: 2024-05-22  
**说明**: 本目录已重新组织，将配置文件和脚本分离，便于管理和维护
