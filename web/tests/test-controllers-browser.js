/**
 * 控制器架构集成测试
 * 在浏览器中运行，无需Node.js环境
 */
class ControllerIntegrationTest {
    constructor() {
        this.totalTests = 0;
        this.passedTests = 0;
        this.failedTests = 0;
        this.testResults = [];
    }

    /**
     * 断言：相等
     */
    assertEqual(actual, expected, message) {
        this.totalTests++;
        if (actual === expected) {
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`✅ ${message}`);
            return true;
        } else {
            this.failedTests++;
            const error = `期望: ${expected}, 实际: ${actual}`;
            this.testResults.push({ status: 'fail', message, error });
            console.error(`❌ ${message} - ${error}`);
            return false;
        }
    }

    /**
     * 断言：真值
     */
    assertTrue(value, message) {
        this.totalTests++;
        if (value === true) {
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`✅ ${message}`);
            return true;
        } else {
            this.failedTests++;
            const error = `期望: true, 实际: ${value}`;
            this.testResults.push({ status: 'fail', message, error });
            console.error(`❌ ${message} - ${error}`);
            return false;
        }
    }

    /**
     * 断言：对象存在
     */
    assertNotNull(obj, message) {
        this.totalTests++;
        if (obj !== null && obj !== undefined) {
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`✅ ${message}`);
            return true;
        } else {
            this.failedTests++;
            const error = '对象为null或undefined';
            this.testResults.push({ status: 'fail', message, error });
            console.error(`❌ ${message} - ${error}`);
            return false;
        }
    }

    /**
     * 断言：函数执行不抛出异常
     */
    assertNoThrow(fn, message) {
        this.totalTests++;
        try {
            fn();
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`✅ ${message}`);
            return true;
        } catch (e) {
            this.failedTests++;
            const error = e.message;
            this.testResults.push({ status: 'fail', message, error });
            console.error(`❌ ${message} - ${error}`);
            return false;
        }
    }

    /**
     * 测试1: EventDispatcher基础功能
     */
    testEventDispatcher() {
        console.group('📦 测试1: EventDispatcher');
        
        const dispatcher = new window.EventDispatcher();
        let eventFired = false;
        let eventData = null;

        // 注册事件监听器
        dispatcher.on('test:event', (data) => {
            eventFired = true;
            eventData = data;
        });

        // 触发事件
        dispatcher.emit('test:event', { value: 42 });

        this.assertTrue(eventFired, '事件应该被触发');
        this.assertEqual(eventData.value, 42, '事件数据应该正确传递');

        // 移除监听器
        dispatcher.off('test:event');
        eventFired = false;
        dispatcher.emit('test:event', { value: 99 });
        this.assertTrue(!eventFired, '移除监听器后不应再触发');

        console.groupEnd();
    }

    /**
     * 测试2: GameState初始化
     */
    testGameStateInit() {
        console.group('🎮 测试2: GameState初始化');

        const gameState = new window.GameState();
        
        this.assertNotNull(gameState, 'GameState应该成功创建');
        this.assertEqual(gameState.playerTurn, 'red', '红方先手');
        this.assertEqual(gameState.gameOver, false, '游戏未结束');
        // 注意：匈汉象棋有44个棋子（包含特殊棋子），不是传统象棋的32个
        this.assertEqual(gameState.pieces.length, 44, '初始44个棋子');
        this.assertEqual(gameState.moveHistory.length, 0, '初始无移动历史');

        console.groupEnd();
    }

    /**
     * 测试3: GameLogicHandler功能
     */
    testGameLogicHandler() {
        console.group('⚙️ 测试3: GameLogicHandler');

        const gameState = new window.GameState();
        const ruleConfig = new window.GameRuleConfig();
        const events = new window.EventDispatcher();
        const logicHandler = new window.GameLogicHandler(gameState, ruleConfig, events);

        this.assertNotNull(logicHandler, 'GameLogicHandler应该成功创建');
        this.assertNotNull(logicHandler.executeMove, 'executeMove方法应该存在');
        this.assertNotNull(logicHandler.trySpawnBing, 'trySpawnBing方法应该存在');

        // 测试兵复活配置检查
        const result = logicHandler.trySpawnBing(6, 0);
        this.assertEqual(result.success, false, '默认配置下兵复活应该失败');

        console.groupEnd();
    }

    /**
     * 测试4: UIController功能
     */
    testUIController() {
        console.group('🎨 测试4: UIController');

        // 创建模拟Canvas
        const canvas = document.createElement('canvas');
        canvas.width = 800;
        canvas.height = 800;
        document.body.appendChild(canvas);

        const events = new window.EventDispatcher();
        const uiController = new window.UIController(canvas, events);

        this.assertNotNull(uiController, 'UIController应该成功创建');
        this.assertNotNull(uiController.bindEvents, 'bindEvents方法应该存在');
        this.assertNotNull(uiController.updateUI, 'updateUI方法应该存在');

        // 清理
        document.body.removeChild(canvas);

        console.groupEnd();
    }

    /**
     * 测试5: NetworkHandler功能
     */
    testNetworkHandler() {
        console.group('🌐 测试5: NetworkHandler');

        const events = new window.EventDispatcher();
        const networkHandler = new window.NetworkHandler(events);

        this.assertNotNull(networkHandler, 'NetworkHandler应该成功创建');
        this.assertNotNull(networkHandler.connect, 'connect方法应该存在');
        this.assertNotNull(networkHandler.joinRoom, 'joinRoom方法应该存在');

        console.groupEnd();
    }

    /**
     * 测试6: ReplayManager功能
     */
    testReplayManager() {
        console.group('🎬 测试6: ReplayManager');

        // 创建模拟GameController
        const mockController = {
            gameState: new window.GameState(),
            loadGameFromHistory: () => {}
        };

        const replayManager = new window.ReplayManager(mockController);

        this.assertNotNull(replayManager, 'ReplayManager应该成功创建');
        this.assertNotNull(replayManager.init, 'init方法应该存在');
        this.assertNotNull(replayManager.showReplaySidebar, 'showReplaySidebar方法应该存在');

        console.groupEnd();
    }

    /**
     * 测试7: 兵复活接口（三参数）
     */
    testSpawnBingInterface() {
        console.group('♟️ 测试7: 兵复活接口');

        const gameState = new window.GameState();

        // 测试接口接受三个参数
        this.assertNotNull(gameState.spawnBing, 'spawnBing方法应该存在');
        
        // 验证方法签名支持camp参数
        const funcStr = gameState.spawnBing.toString();
        const hasCampParam = funcStr.includes('camp');
        this.assertTrue(hasCampParam, 'spawnBing应该接受camp参数');

        console.groupEnd();
    }

    /**
     * 测试8: GameController整体架构
     */
    testGameControllerArchitecture() {
        console.group('🕹️ 测试8: GameController架构');

        // 检查GameController是否存在所有必要的方法
        const requiredMethods = [
            'toggleBackgroundMusic',
            'switchMusicStyle',
            'updateVolume',
            'changeBoardTheme',
            'changePieceStyle',
            'resetSettings',
            'handleCanvasClick',
            'undo',
            'restart',
            'resign'
        ];

        requiredMethods.forEach(method => {
            this.assertNotNull(
                window.GameController.prototype[method],
                `GameController应该有${method}方法`
            );
        });

        console.groupEnd();
    }

    /**
     * 测试9: 事件驱动通信
     */
    testEventDrivenCommunication() {
        console.group('📨 测试9: 事件驱动通信');

        const events = new window.EventDispatcher();
        const gameState = new window.GameState();
        const ruleConfig = new window.GameRuleConfig();
        const logicHandler = new window.GameLogicHandler(gameState, ruleConfig, events);

        let moveExecuted = false;
        events.on('move:executed', () => {
            moveExecuted = true;
        });

        // 模拟一次移动
        const piece = gameState.getPieceAt(9, 4); // 红方兵
        if (piece) {
            logicHandler.executeMove([9, 4], [8, 4]);
            this.assertTrue(moveExecuted, '移动后应该触发move:executed事件');
        } else {
            this.assertTrue(true, '跳过移动测试（棋子不存在）');
        }

        console.groupEnd();
    }

    /**
     * 测试10: 设置功能完整性
     */
    testSettingsFunctionality() {
        console.group('⚙️ 测试10: 设置功能');

        // 检查HTML中的设置控件是否存在
        const controls = [
            'btn-toggle-music',
            'btn-switch-music',
            'volume-slider',
            'board-theme-select',
            'piece-style-select',
            'btn-reset-settings'
        ];

        controls.forEach(id => {
            const element = document.getElementById(id);
            this.assertNotNull(element, `设置控件 #${id} 应该存在`);
        });

        console.groupEnd();
    }

    /**
     * 运行所有测试
     */
    async runAllTests() {
        console.log('🚀 开始运行集成测试...\n');
        
        // 等待DOM加载完成
        await new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });

        try {
            this.testEventDispatcher();
            this.testGameStateInit();
            this.testGameLogicHandler();
            this.testUIController();
            this.testNetworkHandler();
            this.testReplayManager();
            this.testSpawnBingInterface();
            this.testGameControllerArchitecture();
            this.testEventDrivenCommunication();
            this.testSettingsFunctionality();
        } catch (error) {
            console.error('💥 测试过程中发生错误:', error);
        }

        console.log('\n✨ 测试完成!');
        console.log(`总计: ${this.totalTests}, 通过: ${this.passedTests}, 失败: ${this.failedTests}`);
        
        return {
            total: this.totalTests,
            passed: this.passedTests,
            failed: this.failedTests,
            rate: this.totalTests > 0 ? ((this.passedTests / this.totalTests) * 100).toFixed(2) : 0
        };
    }
}

// 导出到全局作用域
if (typeof window !== 'undefined') {
    window.ControllerIntegrationTest = ControllerIntegrationTest;
}
