# 控制器架构测试指南

## 📋 测试文件说明

本项目包含两套测试系统，用于验证重构后的控制器架构：

---

## 🌟 推荐: Node.js完整测试（功能最全面）

### 快速开始（3步完成）

#### 步骤1: 安装Node.js

访问官网下载: https://nodejs.org/
- 选择 **LTS版本** (长期支持版)
- 双击安装包，一路点击"Next"
- 完成后重启命令行

验证安装:
```cmd
node --version
npm --version
```

#### 步骤2: 一键安装依赖

```cmd
cd C:\Users\27415\PycharmProjects\xionghan-chess\web\tests
install-and-test.bat
```

或手动执行:
```cmd
npm install
```

#### 步骤3: 运行测试

```cmd
# 方法1: 使用批处理脚本
run-tests.bat

# 方法2: 使用npm命令
npm test

# 方法3: 直接执行
node test-controllers-node.js
```

### Node.js测试特性

✅ **15个完整测试套件**，覆盖所有核心模块:
- EventDispatcher事件分发器
- GameState游戏状态
- GameLogicHandler游戏逻辑
- UIController界面控制
- NetworkHandler网络通信
- ReplayManager复盘管理
- GameController主控制器
- SoundManager音效管理
- GameRuleConfig规则配置
- ChessBoardRenderer棋盘渲染
- GameRecordManager对局记录
- 多事件监听器协作
- once一次性事件
- 事件驱动通信机制
- 兵复活接口(spawnBing)

✅ **自动化依赖管理** - package.json统一管理
✅ **多种测试模式** - 基础/监听/覆盖率/详细输出
✅ **详细的错误报告** - 精确定位问题位置
✅ **持续集成支持** - GitHub Actions兼容

📖 **详细文档**: [README_NODEJS_TESTS.md](README_NODEJS_TESTS.md)

### 1. 浏览器集成测试
**文件**: `test-controllers.html` + `test-controllers-integration.js`

**特点**:
- ✅ 可视化界面，直观展示测试结果
- ✅ 实时显示测试进度和状态
- ✅ 完整的控制台输出
- ✅ 适合功能验证和演示

**运行方式**:
```bash
# 在浏览器中打开
start web/tests/test-controllers.html

# 或使用Python启动本地服务器
cd web
python -m http.server 8080
# 访问 http://localhost:8080/tests/test-controllers.html
```

### 2. Node.js单元测试
**文件**: `test-controllers-node.js`

**特点**:
- ✅ 命令行运行，适合CI/CD
- ✅ 快速执行，无浏览器依赖
- ✅ 可集成到自动化测试流程
- ✅ 适合回归测试

**运行方式**:
```bash
cd web/tests
node test-controllers-node.js
```

## 🧪 测试覆盖范围

### EventDispatcher (事件分发器)
- ✅ 实例化测试
- ✅ 事件订阅和发布
- ✅ 取消订阅功能
- ✅ 一次性事件
- ✅ 事件常量定义
- ✅ 多监听器触发
- ✅ 事件执行顺序

### GameLogicHandler (游戏逻辑处理器)
- ✅ 实例化测试
- ✅ 移动历史管理
- ✅ 清空历史功能
- ✅ 悔棋逻辑（边界情况）
- ✅ 重新开始功能

### NetworkHandler (网络处理器)
- ✅ 实例化测试
- ✅ 初始状态验证
- ✅ 状态查询方法
- ✅ 断开连接处理

### UIController (UI控制器)
- ✅ 实例化测试
- ✅ DOM元素初始化
- ✅ 暗黑模式切换
- ✅ 棋子选中功能
- ✅ Canvas坐标计算

### ReplayManager (复盘管理器)
- ✅ 实例化测试
- ✅ 初始化流程
- ✅ 游戏记录管理
- ✅ 空记录处理

### GameController (主控制器)
- ✅ 实例化测试
- ✅ 属性初始化
- ✅ 事件分发器创建
- ✅ 默认配置验证

### 事件驱动通信
- ✅ 多模块监听同一事件
- ✅ 事件执行顺序
- ✅ 事件数据传递

## 📊 测试指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 测试覆盖率 | > 80% | 核心功能的覆盖比例 |
| 通过率 | 100% | 所有测试必须通过 |
| 执行时间 | < 5秒 | 单次测试完成时间 |
| 内存泄漏 | 0 | 无内存泄漏问题 |

## 🔍 如何解读测试结果

### 浏览器测试界面

```
🟢 绿色 = 测试通过
🔴 红色 = 测试失败
🟡 黄色 = 待执行

状态栏显示:
- 总测试数
- 通过数量
- 失败数量
- 通过率百分比
```

### Node.js测试输出

```
✅ 测试名称          # 通过的测试
❌ 测试名称          # 失败的测试
   错误: 详细信息     # 错误原因

📊 测试结果汇总
总测试数: X
通过: Y ✅
失败: Z ❌
通过率: XX.XX%
```

## 🐛 常见问题排查

### 问题1: 测试无法加载依赖

**症状**: `ReferenceError: XXX is not defined`

**解决**:
```javascript
// 确保在HTML中按正确顺序加载脚本
<script src="../js/core/game-state.js"></script>
<script src="../js/controllers/event-dispatcher.js"></script>
<!-- ... 其他依赖 -->
```

### 问题2: DOM元素不存在

**症状**: `Cannot read property 'addEventListener' of null`

**解决**:
```javascript
// 测试前创建必要的DOM元素
const canvas = document.createElement('canvas');
canvas.id = 'chess-board';
document.body.appendChild(canvas);
```

### 问题3: 异步测试超时

**症状**: 测试长时间无响应

**解决**:
```javascript
// 使用async/await
async function testAsyncFeature() {
    await someAsyncOperation();
    Assert.ok(result, '异步操作应该完成');
}
```

## 📝 添加新测试

### 浏览器测试

```javascript
// 在 test-controllers-integration.js 中添加
async testNewFeature() {
    console.log('📋 测试X: 新功能');
    
    try {
        // 测试代码
        const result = someFunction();
        this.assert(result === expected, '结果应该符合预期');
        
        this.pass('新功能测试通过');
    } catch (error) {
        this.fail('新功能测试失败', error);
    }
    
    console.log('');
}

// 在 runAllTests() 中调用
await this.testNewFeature();
```

### Node.js测试

```javascript
// 在 test-controllers-node.js 中添加
test('新功能应该正常工作', () => {
    const result = someFunction();
    Assert.equal(result, expected, '结果应该符合预期');
});
```

## 🚀 持续集成

### GitHub Actions 示例

```yaml
name: Controller Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '16'
    
    - name: Run Tests
      run: |
        cd web/tests
        node test-controllers-node.js
```

## 📈 性能测试

### 测试事件分发性能

```javascript
test('事件分发性能', () => {
    const events = new EventDispatcher();
    
    // 注册1000个监听器
    for (let i = 0; i < 1000; i++) {
        events.on('perf:test', () => {});
    }
    
    const start = performance.now();
    events.emit('perf:test');
    const end = performance.now();
    
    const duration = end - start;
    Assert.ok(duration < 100, `事件分发应该在100ms内完成，实际${duration}ms`);
});
```

## 🎯 测试最佳实践

1. **独立性**: 每个测试应该独立，不依赖其他测试
2. **可重复**: 测试结果应该一致，不受环境影响
3. **原子性**: 每个测试只验证一个功能点
4. **清晰命名**: 测试名称应该清楚描述测试内容
5. **边界情况**: 测试正常情况和边界情况
6. **错误处理**: 验证错误情况的处理

## 📚 相关文档

- [架构说明](../docs/ARCHITECTURE.md)
- [重构总结](../docs/REFACTORING_SUMMARY.md)
- [开发者指南](../docs/DEVELOPER_GUIDE.md)

---

**版本**: 1.0  
**更新日期**: 2026-05-22  
**维护者**: Development Team
