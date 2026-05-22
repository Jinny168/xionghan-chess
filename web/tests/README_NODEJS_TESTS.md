# Node.js 完整测试指南

## 📦 第一步: 安装Node.js

### Windows系统安装步骤

#### 方法1: 官网下载(推荐)

1. **访问Node.js官网**
   ```
   https://nodejs.org/
   ```

2. **选择版本**
   - 推荐下载 **LTS版本**(长期支持版,更稳定)
   - 当前最新LTS: v20.x.x

3. **下载安装包**
   - Windows 64位: `node-v20.x.x-x64.msi`
   - 直接下载链接: https://nodejs.org/dist/latest-v20.x/node-v20.x.x-x64.msi

4. **运行安装程序**
   - 双击`.msi`文件
   - 点击"Next"直到完成
   - ✅ 建议勾选"Automatically install the necessary tools"

5. **验证安装**
   ```cmd
   node --version
   npm --version
   ```
   
   应该显示类似:
   ```
   v20.11.0
   10.2.4
   ```

#### 方法2: 使用包管理器(高级)

```cmd
# 使用Chocolatey
choco install nodejs-lts

# 或使用Scoop
scoop install nodejs
```

---

## 🚀 第二步: 安装项目依赖

### 1. 进入测试目录

```cmd
cd C:\Users\27415\PycharmProjects\xionghan-chess\web\tests
```

### 2. 安装npm依赖

```cmd
npm install
```

这将自动安装以下依赖:
- **jsdom**: 模拟浏览器环境
- **chai**: 断言库(可选,我们已实现自己的断言)
- **mocha**: 测试框架(可选,我们已实现自己的测试运行器)

安装成功后会显示:
```
added XX packages in Xs
```

---

## 🧪 第三步: 运行测试

### 基础测试命令

```cmd
# 运行所有测试
npm test

# 或直接执行
node test-controllers-node.js
```

### 高级测试命令

```cmd
# 监听模式(文件变化时自动重新测试)
npm run test:watch

# 代码覆盖率分析
npm run test:coverage

# 详细输出模式
npm run test:verbose
```

---

## 📊 测试结果说明

### 成功输出示例

```
============================================================
🧪 匈汉象棋控制器架构集成测试
============================================================

🚀 开始加载游戏模块...

📦 加载核心模块...
✅ 核心模块加载完成

🎨 加载UI模块...
✅ UI模块加载完成

⚙️ 加载控制器模块...
✅ 控制器模块加载完成


============================================================
📋 测试1: EventDispatcher事件分发器
────────────────────────────────────────────────────────────
  ✅ 事件应该被触发
  ✅ 事件数据应该正确传递
  ✅ 移除监听器后不应再触发

📋 测试2: GameState游戏状态
────────────────────────────────────────────────────────────
  ✅ GameState应该成功创建
  ✅ 红方先手
  ✅ 游戏未结束
  ✅ 初始44个棋子
  ✅ 初始无移动历史

...(更多测试)...

============================================================
📊 测试结果汇总
============================================================
总测试数: 15
通过: 15 ✅
失败: 0 ❌
通过率: 100.00%
耗时: 0.85s
============================================================

🎉 恭喜！所有测试通过！
```

### 失败输出示例

```
📋 测试X: XXX功能
────────────────────────────────────────────────────────────
  ✅ 测试项1
  ❌ 测试项2
     期望: true, 实际: false

============================================================
📊 测试结果汇总
============================================================
总测试数: 15
通过: 14 ✅
失败: 1 ❌
通过率: 93.33%
耗时: 0.92s
============================================================

⚠️ 有 1 个测试失败，请检查上述错误信息
```

---

## 🔍 第四步: 解读测试结果

### 测试覆盖范围

| 测试编号 | 测试模块 | 测试内容 |
|---------|---------|---------|
| 测试1 | EventDispatcher | 事件注册、触发、移除 |
| 测试2 | GameState | 初始化、棋子数量、回合制 |
| 测试3 | GameLogicHandler | 移动验证、兵复活逻辑 |
| 测试4 | UIController | Canvas渲染、事件绑定 |
| 测试5 | NetworkHandler | 连接管理、房间加入 |
| 测试6 | ReplayManager | 复盘模式、历史记录 |
| 测试7 | spawnBing接口 | 三参数签名、camp参数 |
| 测试8 | GameController | 设置功能、核心方法 |
| 测试9 | 事件驱动通信 | 组件间事件传递 |
| 测试10 | SoundManager | 音效播放方法 |
| 测试11 | GameRuleConfig | 规则配置管理 |
| 测试12 | 多事件监听器 | 多个监听器协作 |
| 测试13 | once一次性事件 | 单次触发机制 |
| 测试14 | ChessBoardRenderer | 棋盘渲染方法 |
| 测试15 | GameRecordManager | 对局记录保存加载 |

---

## 🐛 常见问题排查

### Q1: npm install 失败

**症状**: 
```
npm ERR! code ECONNRESET
npm ERR! network timeout
```

**解决方法**:
```cmd
# 切换淘宝镜像
npm config set registry https://registry.npmmirror.com

# 重新安装
npm install
```

### Q2: 模块加载失败

**症状**:
```
❌ 模块加载失败: Cannot find module '../js/core/chess-piece.js'
```

**解决方法**:
1. 确认当前目录是`web/tests`
2. 检查文件路径是否正确
3. 确保所有JS文件都存在

```cmd
# 查看当前目录
cd

# 应该显示
C:\Users\27415\PycharmProjects\xionghan-chess\web\tests
```

### Q3: jsdom相关错误

**症状**:
```
Error: The module 'xxx.node' was compiled against a different Node.js version
```

**解决方法**:
```cmd
# 清理缓存
npm cache clean --force

# 删除node_modules
rmdir /s /q node_modules

# 重新安装
npm install
```

### Q4: 测试通过率不是100%

**处理步骤**:
1. 查看红色标记的失败项
2. 阅读错误详情
3. 根据提示定位问题代码
4. 修复后重新运行测试

---

## 💡 最佳实践

### 1. 每次修改后运行测试

```cmd
# 修改代码后立即测试
git commit -m "修改XXX功能"
npm test
```

### 2. 使用监听模式开发

```cmd
# 文件变化时自动重新测试
npm run test:watch
```

### 3. 定期运行完整测试

```cmd
# 每天下班前运行
npm test

# 或提交代码前运行
git push origin main
```

### 4. 添加新测试用例

在`test-controllers-node.js`中添加:

```javascript
runner.testGroup('测试X: 新功能', () => {
    const { NewFeature } = window;
    
    runner.assertNotNull(NewFeature, '新功能应该存在');
    // ... 更多测试
});
```

---

## 📈 进阶: 持续集成(CI)

### GitHub Actions配置

在项目根目录创建`.github/workflows/test.yml`:

```yaml
name: Controller Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '20'
    
    - name: Install dependencies
      run: |
        cd web/tests
        npm install
    
    - name: Run tests
      run: |
        cd web/tests
        npm test
```

---

## 🎯 性能优化

### 加速测试执行

```cmd
# 使用--max-old-space-size增加内存
node --max-old-space-size=4096 test-controllers-node.js

# 跳过某些耗时的测试组
# (在代码中注释掉对应的runner.testGroup调用)
```

---

## 📞 技术支持

如有问题:
1. 查看控制台输出的错误信息
2. 检查Node.js版本是否>=14.0
3. 确认所有依赖已正确安装
4. 联系开发团队

---

## 📝 版本历史

- **v1.0** (当前版本)
  - 完整的Node.js测试框架
  - 15个测试套件
  - 自动化依赖管理
  - 支持多种测试模式

---

**最后更新**: 2024年  
**维护者**: Xionghan Chess Development Team
