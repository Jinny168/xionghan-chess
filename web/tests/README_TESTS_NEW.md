# 控制器集成测试

本目录包含匈汉象棋控制器架构的集成测试文件。

## 📁 测试文件说明

### 浏览器端测试（推荐，无需Node.js）⭐

#### `run-tests-browser.html` ⭐ **推荐使用**
- **运行方式**: 直接在浏览器中打开
- **依赖**: 无需安装任何软件
- **特点**: 
  - 图形化界面，直观显示测试结果
  - 实时统计通过率
  - 控制台输出便于调试
  - 支持一键重新测试

**使用方法**:
```bash
# 方法1: 双击HTML文件直接打开
start run-tests-browser.html

# 方法2: 通过HTTP服务器访问（推荐，避免跨域问题）
python -m http.server 8080
# 然后在浏览器中访问: http://localhost:8080/tests/run-tests-browser.html
```

#### `test-controllers-browser.js`
- **用途**: 浏览器测试的核心逻辑文件
- **不直接运行**,由`run-tests-browser.html`加载

---

### Node.js端测试（需要安装Node.js）

#### `test-controllers-node.js`
- **运行方式**: 在Node.js环境中执行
- **依赖**: Node.js >= 14.0
- **特点**: 适合自动化测试和CI/CD

**使用方法**:
```bash
# 确保已安装Node.js
node --version

# 运行测试
node test-controllers-node.js
```

#### `test-controllers-integration.js`
- **用途**: 提供测试类定义，供其他测试文件引用
- **不直接运行**

---

## 🧪 测试内容

所有测试文件覆盖以下功能模块:

### 1. EventDispatcher (事件分发器)
- ✅ 事件注册与触发
- ✅ 事件数据传递
- ✅ 事件监听器移除

### 2. GameState (游戏状态)
- ✅ 初始化检查
- ✅ 棋子数量验证
- ✅ 回合制逻辑

### 3. GameLogicHandler (游戏逻辑处理器)
- ✅ 移动验证
- ✅ 兵复活逻辑
- ✅ 将军检测

### 4. UIController (UI控制器)
- ✅ Canvas渲染
- ✅ 事件绑定
- ✅ UI更新

### 5. NetworkHandler (网络处理器)
- ✅ 连接管理
- ✅ 房间加入
- ✅ 消息收发

### 6. ReplayManager (复盘管理器)
- ✅ 复盘模式初始化
- ✅ 历史记录加载
- ✅ 进度控制

### 7. 兵复活接口
- ✅ 三参数签名验证 (`spawnBing(row, col, camp)`)
- ✅ 阵营参数可选性
- ✅ 网络对战兼容性

### 8. GameController (主控制器)
- ✅ 设置功能方法完整性
  - `toggleBackgroundMusic()`
  - `switchMusicStyle()`
  - `updateVolume(volume)`
  - `changeBoardTheme(theme)`
  - `changePieceStyle(style)`
  - `resetSettings()`
- ✅ 核心游戏方法
  - `handleCanvasClick(pos)`
  - `undo()`
  - `restart()`
  - `resign()`

### 9. 事件驱动通信
- ✅ 组件间事件传递
- ✅ 移动事件触发
- ✅ UI响应机制

### 10. 设置功能完整性
- ✅ HTML控件存在性检查
- ✅ 背景音乐开关
- ✅ 音量滑块
- ✅ 主题选择器
- ✅ 样式选择器
- ✅ 恢复默认按钮

---

## 🚀 快速开始

### 方案A: 浏览器测试（最简单）⭐

1. **启动Flask服务器**:
```bash
cd web/server
python app.py
```

2. **打开浏览器测试页面**:
   - 访问: `http://localhost:5000/tests/run-tests-browser.html`
   - 或直接双击: `web/tests/run-tests-browser.html`

3. **点击"运行测试"按钮**

4. **查看结果**:
   - 绿色 ✅ = 通过
   - 红色 ❌ = 失败
   - 底部显示统计信息

### 方案B: Node.js测试（高级）

1. **安装Node.js** (如果尚未安装):
   - 下载: https://nodejs.org/
   - 验证: `node --version`

2. **运行测试**:
```bash
cd web/tests
node test-controllers-node.js
```

---

## 📊 解读测试结果

### 全部通过 (理想情况)
```
🎉 所有测试通过！
总测试数: XX
通过: XX
失败: 0
通过率: 100%
```

### 部分失败
```
⚠️ 部分测试失败
总测试数: XX
通过: YY
失败: ZZ
通过率: WW%
```

**处理建议**:
1. 查看红色标记的失败项
2. 阅读错误详情
3. 检查对应模块的代码
4. 修复后重新运行测试

---

## 🔧 常见问题

### Q1: 浏览器测试时出现 "XXX is not defined" 错误
**原因**: JavaScript文件加载顺序错误或路径不正确

**解决方法**:
1. 检查HTML中的 `<script>` 标签顺序
2. 确认文件路径正确
3. 使用HTTP服务器而非直接打开文件

### Q2: 某些测试显示 "跳过"
**原因**: 前置条件不满足（如缺少某个DOM元素）

**解决方法**:
- 这是正常的，不影响其他测试
- 确保在完整的游戏环境中运行测试

### Q3: 测试通过率不是100%
**可能原因**:
1. 代码有bug
2. 测试用例过时
3. 环境配置问题

**解决方法**:
1. 查看详细错误信息
2. 对比原版代码
3. 检查依赖是否完整

### Q4: 如何添加新的测试用例？

**步骤**:
1. 打开 `test-controllers-browser.js`
2. 在 `ControllerIntegrationTest` 类中添加新方法:
```javascript
testNewFeature() {
    console.group('🆕 测试X: 新功能');
    
    // 编写测试逻辑
    this.assertTrue(condition, '描述');
    this.assertEqual(actual, expected, '描述');
    
    console.groupEnd();
}
```
3. 在 `runAllTests()` 方法中调用新测试:
```javascript
this.testNewFeature();
```

---

## 📝 版本历史

- **v1.0** (当前版本)
  - 初始浏览器端测试框架
  - 10个核心测试套件
  - 图形化测试结果展示
  - 无需Node.js即可运行

---

## 💡 最佳实践

1. **每次修改控制器后运行测试**
   - 确保没有破坏现有功能
   - 及时发现回归问题

2. **保持测试覆盖率**
   - 新增功能时同步添加测试
   - 修复bug时添加对应的测试用例

3. **定期审查测试用例**
   - 删除过时的测试
   - 优化测试性能

4. **团队协作**
   - 提交代码前确保测试通过
   - 共享测试发现的问题

---

## 📞 技术支持

如有问题，请:
1. 查看控制台输出（F12开发者工具）
2. 检查错误详情
3. 联系开发团队

---

**最后更新**: 2024年
