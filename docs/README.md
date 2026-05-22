# 雄汉象棋文档中心

本目录包含项目的所有文档，按类型分类管理。

## 📚 文档分类

### 入门指南
- [README.md](../README.md) - 项目总览（根目录）
- [web/docs/README.md](../web/docs/README.md) - Web 版本说明

### 部署文档
- [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) - **统一部署指南**（推荐）
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考卡片（速查）

### 开发文档
- [web/docs/DEVELOPER_GUIDE.md](../web/docs/DEVELOPER_GUIDE.md) - 开发者指南

### 配置文件
- [docker/config/.env.example](../docker/config/.env.example) - Docker 环境变量模板
- [web/docs/taunts.json](../web/docs/taunts.json) - 嘲讽语句配置

## 🚀 快速导航

### 我想快速部署（3分钟）
👉 阅读 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 一键部署命令

### 我需要详细部署指南
👉 阅读 [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) - 完整教程（Docker + Linux 虚拟机）

### 我是开发者，想了解项目架构
👉 阅读 [web/docs/DEVELOPER_GUIDE.md](../web/docs/DEVELOPER_GUIDE.md)

### 我想了解项目概况
👉 阅读 [README.md](../README.md)

## 📖 文档结构说明

```
docs/
├── README.md                      # 本文档（文档索引）
├── DEPLOY_GUIDE.md               # 统一部署指南（Docker + Linux）
└── QUICK_REFERENCE.md            # 快速参考卡片（常用命令速查）

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
- **避免重复**：相似内容合并到一个文档

### 更新日志
每次更新文档后，建议在文档开头添加更新记录：

```markdown
## 更新历史

- 2024-05-21: 初始版本
- 2024-05-22: 添加故障排查章节
```

---

**最后更新**: 2024-05-22  
**维护者**: 雄汉象棋开发团队

---

## 📝 整理说明

本次整理将原有的 3 个部署文档（DOCKER_DEPLOY.md、LINUX_DEPLOY_GUIDE.md、README_DOCKER.md）合并为：

1. **DEPLOY_GUIDE.md** - 统一部署指南，包含：
   - 快速开始（3分钟部署）
   - Docker 部署详解
   - Linux 环境准备（虚拟机教程）
   - 配置说明、故障排查、生产优化

2. **QUICK_REFERENCE.md** - 快速参考卡片，包含：
   - 常用命令速查
   - 故障排查速查
   - 数据备份命令

**优势**：
- ✅ 消除重复内容（从 1600+ 行减少到 870 行）
- ✅ 逻辑更清晰（统一部署入口）
- ✅ 易于维护（单一事实来源）
- ✅ 路径已更新（匹配新的 docker/ 目录结构）
