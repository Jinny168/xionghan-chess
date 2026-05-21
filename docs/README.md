# 雄汉象棋文档中心

本目录包含项目的所有文档，按类型分类管理。

## 📚 文档分类

### 入门指南
- [README.md](../README.md) - 项目总览（根目录）
- [web/docs/README.md](../web/docs/README.md) - Web 版本说明

### 部署文档
- [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md) - Docker 完整部署指南
- [LINUX_DEPLOY_GUIDE.md](LINUX_DEPLOY_GUIDE.md) - Linux 虚拟机部署教程（小白版）
- [README_DOCKER.md](README_DOCKER.md) - Docker 快速参考卡片

### 开发文档
- [web/docs/DEVELOPER_GUIDE.md](../web/docs/DEVELOPER_GUIDE.md) - 开发者指南

### 配置文件
- [docker/.env.example](../docker/.env.example) - Docker 环境变量模板
- [web/docs/taunts.json](../web/docs/taunts.json) - 嘲讽语句配置

## 🚀 快速导航

### 我是新手，想部署到 Linux 虚拟机
👉 阅读 [LINUX_DEPLOY_GUIDE.md](LINUX_DEPLOY_GUIDE.md)

### 我想使用 Docker 部署
👉 阅读 [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)

### 我想快速开始 Docker 部署
👉 阅读 [README_DOCKER.md](README_DOCKER.md)

### 我是开发者，想了解项目架构
👉 阅读 [web/docs/DEVELOPER_GUIDE.md](../web/docs/DEVELOPER_GUIDE.md)

### 我想了解项目概况
👉 阅读 [README.md](../README.md)

## 📖 文档结构说明

```
docs/
├── README.md                      # 本文档（文档索引）
├── DOCKER_DEPLOY.md              # Docker 部署完整指南
├── LINUX_DEPLOY_GUIDE.md         # Linux 部署详细教程
└── README_DOCKER.md              # Docker 快速参考

web/docs/
├── README.md                      # Web 版本说明
├── DEVELOPER_GUIDE.md            # 开发者指南
└── taunts.json                    # 游戏配置
```

## 🔧 常用链接

- **Docker 配置目录**: [docker/](../docker/)
- **Web 文档目录**: [web/docs/](../web/docs/)
- **项目根目录**: [../](../)

## 📝 文档维护

### 添加新文档
1. 将 Markdown 文件放入 `docs/` 目录
2. 在本文档中添加链接和说明
3. 更新相关文档中的交叉引用

### 文档规范
- 使用中文编写
- 包含清晰的目录结构
- 提供代码示例
- 添加常见问题解答
- 保持格式统一（使用 Markdown）

### 更新日志
每次更新文档后，建议在文档开头添加更新记录：

```markdown
## 更新历史

- 2024-05-21: 初始版本
- 2024-05-22: 添加故障排查章节
```

---

**最后更新**: 2024-05-21  
**维护者**: 雄汉象棋开发团队
