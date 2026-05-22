/**
 * 控制器架构集成测试
 * 验证重构后的各控制器是否能正常协作
 */

class ControllerIntegrationTest {
    constructor() {
        this.testResults = [];
        this.totalTests = 0;
        this.passedTests = 0;
        this.failedTests = 0;
    }

    /**
     * 运行所有测试
     */
    async runAllTests() {
        console.log('🧪 开始运行控制器集成测试...\n');
        
        // 测试1: 事件分发器
        await this.testEventDispatcher();
        
        // 测试2: 游戏逻辑处理器
        await this.testGameLogicHandler();
        
        // 测试3: UI控制器
        await this.testUIController();
        
        // 测试4: 网络处理器
        await this.testNetworkHandler();
        
        // 测试5: 复盘管理器
        await this.testReplayManager();
        
        // 测试6: 主控制器初始化
        await this.testGameControllerInit();
        
        // 输出测试结果
        this.printResults();
    }

    /**
     * 测试事件分发器
     */
    async testEventDispatcher() {
        console.log('📋 测试1: 事件分发器 (EventDispatcher)');
        
        try {
            // 创建事件分发器
            const events = new EventDispatcher();
            this.assert(events instanceof EventDispatcher, 'EventDispatcher实例化');
            
            // 测试事件订阅和发布
            let eventTriggered = false;
            let eventData = null;
            
            const unsubscribe = events.on('test:event', (data) => {
                eventTriggered = true;
                eventData = data;
            });
            
            events.emit('test:event', { message: 'hello' });
            this.assert(eventTriggered, '事件触发');
            this.assert(eventData.message === 'hello', '事件数据传递');
            
            // 测试取消订阅
            eventTriggered = false;
            unsubscribe();
            events.emit('test:event', { message: 'world' });
            this.assert(!eventTriggered, '取消订阅生效');
            
            // 测试一次性事件
            let onceCount = 0;
            events.once('once:event', () => {
                onceCount++;
            });
            
            events.emit('once:event');
            events.emit('once:event');
            this.assert(onceCount === 1, '一次性事件只触发一次');
            
            // 测试事件常量
            this.assert(GameEvents.PIECE_MOVED === 'piece:moved', '事件常量定义');
            this.assert(GameEvents.GAME_END === 'game:end', '事件常量定义');
            
            this.pass('事件分发器测试通过');
        } catch (error) {
            this.fail('事件分发器测试失败', error);
        }
        
        console.log('');
    }

    /**
     * 测试游戏逻辑处理器
     */
    async testGameLogicHandler() {
        console.log('📋 测试2: 游戏逻辑处理器 (GameLogicHandler)');
        
        try {
            // 创建依赖
            const gameState = new GameState();
            const ruleConfig = new GameRuleConfig();
            const events = new EventDispatcher();
            
            // 创建逻辑处理器
            const logicHandler = new GameLogicHandler(gameState, ruleConfig, events);
            this.assert(logicHandler instanceof GameLogicHandler, 'GameLogicHandler实例化');
            
            // 测试获取移动历史
            const history = logicHandler.getMoveHistory();
            this.assert(Array.isArray(history), '获取移动历史返回数组');
            this.assert(history.length === 0, '初始移动历史为空');
            
            // 测试清空历史
            logicHandler.clearHistory();
            this.assert(logicHandler.getMoveHistory().length === 0, '清空历史成功');
            
            // 测试悔棋（无历史记录时）
            const undoResult = logicHandler.undo();
            this.assert(!undoResult.success, '无历史记录时悔棋失败');
            
            // 测试重新开始
            logicHandler.restart();
            this.assert(logicHandler.getMoveHistory().length === 0, '重新开始后历史清空');
            
            this.pass('游戏逻辑处理器测试通过');
        } catch (error) {
            this.fail('游戏逻辑处理器测试失败', error);
        }
        
        console.log('');
    }

    /**
     * 测试UI控制器
     */
    async testUIController() {
        console.log('📋 测试3: UI控制器 (UIController)');
        
        try {
            // 创建Canvas元素
            const canvas = document.createElement('canvas');
            canvas.id = 'test-canvas';
            canvas.width = 800;
            canvas.height = 800;
            document.body.appendChild(canvas);
            
            const events = new EventDispatcher();
            
            // 创建UI控制器
            const uiController = new UIController(canvas, events);
            this.assert(uiController instanceof UIController, 'UIController实例化');
            
            // 测试初始化元素
            uiController.initElements();
            this.assert(uiController.elements !== null, 'DOM元素初始化');
            
            // 测试暗黑模式切换
            uiController.toggleDarkMode(false);
            this.assert(!uiController.isDarkMode, '暗黑模式关闭');
            
            uiController.toggleDarkMode(true);
            this.assert(uiController.isDarkMode, '暗黑模式开启');
            this.assert(document.body.classList.contains('dark-mode'), 'body添加dark-mode类');
            
            uiController.toggleDarkMode(false);
            this.assert(!document.body.classList.contains('dark-mode'), 'body移除dark-mode类');
            
            // 测试选中棋子
            uiController.highlightSelectedPiece({ row: 0, col: 0 });
            const selected = uiController.getSelectedPiece();
            this.assert(selected.row === 0 && selected.col === 0, '选中棋子');
            
            uiController.clearSelection();
            this.assert(uiController.getSelectedPiece() === null, '清除选中');
            
            // 清理
            document.body.removeChild(canvas);
            
            this.pass('UI控制器测试通过');
        } catch (error) {
            this.fail('UI控制器测试失败', error);
        }
        
        console.log('');
    }

    /**
     * 测试网络处理器
     */
    async testNetworkHandler() {
        console.log('📋 测试4: 网络处理器 (NetworkHandler)');
        
        try {
            const events = new EventDispatcher();
            
            // 创建网络处理器
            const networkHandler = new NetworkHandler(events);
            this.assert(networkHandler instanceof NetworkHandler, 'NetworkHandler实例化');
            
            // 测试初始状态
            const status = networkHandler.getStatus();
            this.assert(!status.isConnected, '初始未连接');
            this.assert(status.roomId === null, '初始无房间ID');
            
            // 测试状态查询方法
            this.assert(!networkHandler.isNetworkConnected(), 'isNetworkConnected返回false');
            this.assert(networkHandler.getPlayerCamp() === null, 'getPlayerCamp返回null');
            this.assert(!networkHandler.getIsHost(), 'getIsHost返回false');
            this.assert(!networkHandler.isOpponentConnected(), 'isOpponentConnected返回false');
            
            // 测试断开连接（未连接时不应报错）
            networkHandler.disconnect();
            this.assert(!networkHandler.isNetworkConnected(), '断开连接后状态正确');
            
            this.pass('网络处理器测试通过');
        } catch (error) {
            this.fail('网络处理器测试失败', error);
        }
        
        console.log('');
    }

    /**
     * 测试复盘管理器
     */
    async testReplayManager() {
        console.log('📋 测试5: 复盘管理器 (ReplayManager)');
        
        try {
            // 创建模拟的GameController
            const mockGameController = {
                gameState: new GameState(),
                render: () => {},
                isOnline: false
            };
            
            // 创建复盘管理器
            const replayManager = new ReplayManager(mockGameController);
            this.assert(replayManager instanceof ReplayManager, 'ReplayManager实例化');
            
            // 测试初始化
            replayManager.init();
            this.assert(replayManager.gameState !== null, 'GameState初始化');
            
            // 测试游戏记录管理器
            this.assert(replayManager.gameRecordManager instanceof GameRecordManager, 'GameRecordManager实例化');
            
            // 测试保存空记录（应该不保存）
            replayManager.saveCurrentGameRecord();
            const records = replayManager.gameRecordManager.loadAllRecords();
            this.assert(records.length === 0, '空对局不保存记录');
            
            // 测试加载记录列表（无记录时）
            // 注意：这里需要DOM元素存在，所以跳过UI相关测试
            
            this.pass('复盘管理器测试通过');
        } catch (error) {
            this.fail('复盘管理器测试失败', error);
        }
        
        console.log('');
    }

    /**
     * 测试主控制器初始化
     */
    async testGameControllerInit() {
        console.log('📋 测试6: 主控制器初始化 (GameController)');
        
        try {
            // 创建必要的DOM元素
            this.createMockDOMElements();
            
            // 创建主控制器
            const gameController = new GameController();
            this.assert(gameController instanceof GameController, 'GameController实例化');
            
            // 测试属性初始化
            this.assert(gameController.events instanceof EventDispatcher, '事件分发器初始化');
            this.assert(gameController.playerCamp === 'red', '默认玩家阵营为红方');
            this.assert(!gameController.isOnline, '默认非在线模式');
            this.assert(!gameController.isReplayMode, '默认非复盘模式');
            
            // 测试初始化方法（不实际启动游戏）
            // 注意：完整初始化需要更多DOM元素和依赖，这里只测试基本结构
            
            this.pass('主控制器初始化测试通过');
        } catch (error) {
            this.fail('主控制器初始化测试失败', error);
        } finally {
            // 清理DOM元素
            this.cleanupMockDOMElements();
        }
        
        console.log('');
    }

    /**
     * 测试事件驱动通信
     */
    async testEventDrivenCommunication() {
        console.log('📋 测试7: 事件驱动通信');
        
        try {
            const events = new EventDispatcher();
            
            // 模拟多个模块监听同一事件
            let module1Received = false;
            let module2Received = false;
            let module3Received = false;
            
            events.on('game:state:changed', () => {
                module1Received = true;
            });
            
            events.on('game:state:changed', () => {
                module2Received = true;
            });
            
            events.on('game:state:changed', () => {
                module3Received = true;
            });
            
            // 触发事件
            events.emit('game:state:changed');
            
            this.assert(module1Received, '模块1收到事件');
            this.assert(module2Received, '模块2收到事件');
            this.assert(module3Received, '模块3收到事件');
            
            // 测试事件执行顺序
            let executionOrder = [];
            
            events.on('order:test', () => executionOrder.push(1));
            events.on('order:test', () => executionOrder.push(2));
            events.on('order:test', () => executionOrder.push(3));
            
            events.emit('order:test');
            this.assert(
                executionOrder[0] === 1 && executionOrder[1] === 2 && executionOrder[2] === 3,
                '事件按注册顺序执行'
            );
            
            this.pass('事件驱动通信测试通过');
        } catch (error) {
            this.fail('事件驱动通信测试失败', error);
        }
        
        console.log('');
    }

    /**
     * 创建模拟DOM元素
     */
    createMockDOMElements() {
        const elements = [
            'chess-board',
            'turn-indicator',
            'check-alert',
            'step-count',
            'total-time',
            'move-history',
            'btn-home',
            'btn-undo',
            'btn-restart',
            'btn-surrender',
            'btn-new-game',
            'btn-dark-mode',
            'btn-move-history',
            'btn-replay',
            'btn-chat',
            'btn-settings',
            'btn-help',
            'close-move-history',
            'close-chat',
            'close-settings',
            'close-help',
            'close-replay-sidebar',
            'replay-sidebar',
            'game-records-list',
            'replay-step-info',
            'replay-progress',
            'replay-begin',
            'replay-prev',
            'replay-next',
            'replay-end',
            'chat-input-modal',
            'move-history-modal',
            'chat-modal',
            'settings-modal',
            'help-modal'
        ];
        
        elements.forEach(id => {
            if (!document.getElementById(id)) {
                const element = document.createElement('div');
                element.id = id;
                document.body.appendChild(element);
            }
        });
    }

    /**
     * 清理模拟DOM元素
     */
    cleanupMockDOMElements() {
        // 清理测试中添加的元素
        const elements = document.querySelectorAll('[id^="test-"]');
        elements.forEach(el => el.remove());
    }

    /**
     * 断言辅助方法
     */
    assert(condition, message) {
        this.totalTests++;
        if (!condition) {
            throw new Error(`断言失败: ${message}`);
        }
    }

    /**
     * 记录通过的测试
     */
    pass(message) {
        this.passedTests++;
        this.testResults.push({ status: 'PASS', message });
        console.log(`  ✅ ${message}`);
    }

    /**
     * 记录失败的测试
     */
    fail(message, error) {
        this.failedTests++;
        this.testResults.push({ status: 'FAIL', message, error: error.message });
        console.error(`  ❌ ${message}`);
        console.error(`     错误: ${error.message}`);
    }

    /**
     * 打印测试结果
     */
    printResults() {
        console.log('\n' + '='.repeat(60));
        console.log('📊 测试结果汇总');
        console.log('='.repeat(60));
        console.log(`总测试数: ${this.totalTests}`);
        console.log(`通过: ${this.passedTests} ✅`);
        console.log(`失败: ${this.failedTests} ❌`);
        console.log(`通过率: ${((this.passedTests / this.totalTests) * 100).toFixed(2)}%`);
        console.log('='.repeat(60));
        
        if (this.failedTests > 0) {
            console.log('\n❌ 失败的测试:');
            this.testResults
                .filter(r => r.status === 'FAIL')
                .forEach(r => {
                    console.log(`  - ${r.message}`);
                    console.log(`    错误: ${r.error}`);
                });
        } else {
            console.log('\n🎉 所有测试通过！重构成功！');
        }
        
        console.log('='.repeat(60) + '\n');
    }
}

// 导出测试类
if (typeof window !== 'undefined') {
    window.ControllerIntegrationTest = ControllerIntegrationTest;
}

// 自动运行测试（如果在浏览器环境中）
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    window.addEventListener('load', () => {
        setTimeout(() => {
            const test = new ControllerIntegrationTest();
            test.runAllTests();
        }, 1000);
    });
}
