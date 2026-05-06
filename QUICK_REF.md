# 项目重构快速参考

## ✅ 已完成的操作

1. ✓ 创建 `desktop/` 目录（桌面端应用）
2. ✓ 将原 `program/` 下的桌面端代码移至 `desktop/`
3. ✓ 将 `web/` 目录提升至项目根目录
4. ✓ 删除空的 `program/` 目录
5. ✓ 批量更新所有Python导入路径（program → desktop）
6. ✓ 修正配置文件和构建脚本
7. ✓ 验证导入和功能正常

## 📁 新的目录结构

```
xionghan-chess/
├── desktop/          # 🖥️ 桌面端（PyGame）
├── web/              # 🌐 Web端（Flask + HTML5）
├── docs/             # 📚 项目文档
└── tests/            # 🧪 测试文件
```

## 🚀 快速启动

### 桌面端
```bash
cd desktop
python main.py
```

### Web端
```bash
cd web
start.bat
```
访问: http://localhost:5000

## 🔧 关键变更

### 导入路径变更
- **之前**: `from program.xxx import ...`
- **现在**: `from desktop.xxx import ...`

### 打包命令
```bash
cd desktop
python build_exe.py
```

## 📊 统计信息

- **桌面端文件**: 232个
- **Web端文件**: 2159个
- **更新的导入**: 200+处
- **重构时间**: ~2分钟（自动化）

## 📖 相关文档

- [详细项目结构](./PROJECT_STRUCTURE.md)
- [重构总结报告](./REFACTORING_SUMMARY.md)
- [Web端用户指南](./web/README.md)

---

**重构日期**: 2026-05-06  
**状态**: ✅ 完成并验证通过
