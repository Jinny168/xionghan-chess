/**
 * 复盘管理器模块
 * 负责管理复盘侧边栏、对局记录列表等UI交互逻辑
 */

class ReplayManager {
    constructor(gameController) {
        this.gameController = gameController;
        this.gameState = null;
        this.replayController = null;
        this.gameRecordManager = new GameRecordManager();
        this.isReplayMode = false;
        
        // UI元素引用
        this.sidebar = null;
        this.recordsList = null;
        this.stepInfoElement = null;
        this.progressElement = null;
        this.turnIndicator = null;
        
        // 按钮引用
        this.beginBtn = null;
        this.prevBtn = null;
        this.nextBtn = null;
        this.endBtn = null;
        this.closeBtn = null;
    }
    
    /**
     * 初始化复盘管理器
     */
    init() {
        this.gameState = this.gameController.gameState;
        this.initDOMElements();
        this.bindEvents();
    }
    
    /**
     * 初始化DOM元素
     */
    initDOMElements() {
        // 侧边栏
        this.sidebar = document.getElementById('replay-sidebar');
        
        // 对局记录列表
        this.recordsList = document.getElementById('game-records-list');
        
        // 步骤信息
        this.stepInfoElement = document.getElementById('replay-step-info');
        
        // 进度条
        this.progressElement = document.getElementById('replay-progress');
        
        // 回合指示器
        this.turnIndicator = document.getElementById('turn-indicator');
        
        // 控制按钮
        this.beginBtn = document.getElementById('replay-begin');
        this.prevBtn = document.getElementById('replay-prev');
        this.nextBtn = document.getElementById('replay-next');
        this.endBtn = document.getElementById('replay-end');
        this.closeBtn = document.getElementById('close-replay-sidebar');
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 关闭按钮
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => {
                this.exitReplayMode();
            });
        }
        
        // 跳转到开局
        if (this.beginBtn) {
            this.beginBtn.addEventListener('click', () => {
                if (this.replayController) {
                    this.replayController.goToBeginning();
                    this.updateReplayUI();
                    this.gameController.render();
                }
            });
        }
        
        // 上一步
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => {
                if (this.replayController) {
                    this.replayController.goToPrevious();
                    this.updateReplayUI();
                    this.gameController.render();
                }
            });
        }
        
        // 下一步
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                if (this.replayController) {
                    this.replayController.goToNext();
                    this.updateReplayUI();
                    this.gameController.render();
                }
            });
        }
        
        // 跳转到终局
        if (this.endBtn) {
            this.endBtn.addEventListener('click', () => {
                if (this.replayController) {
                    this.replayController.goToEnd();
                    this.updateReplayUI();
                    this.gameController.render();
                }
            });
        }
        
        // 进度条拖动
        if (this.progressElement) {
            this.progressElement.addEventListener('input', (e) => {
                if (this.replayController) {
                    const percentage = parseInt(e.target.value);
                    this.replayController.setProgress(percentage);
                    this.updateReplayUI();
                    this.gameController.render();
                }
            });
        }
    }
    
    /**
     * 显示复盘侧边栏
     */
    showReplaySidebar() {
        if (!this.sidebar) return;
        
        // 检查localStorage中是否有保存的对局记录
        const records = this.gameRecordManager.loadAllRecords();
        
        if (records.length === 0) {
            window.dialogManager.showInfo('提示', '当前没有对局记录，无法复盘');
            return;
        }
        
        // 显示侧边栏
        this.sidebar.classList.remove('hidden');
        
        // 给body添加类，调整右上角状态区域的边距
        document.body.classList.add('replay-active');
        
        // 加载对局记录列表
        this.loadGameRecordsList();
        
        // 如果有当前对局历史，也初始化复盘模式
        if (this.gameState.moveHistory.length > 0) {
            this.initReplayMode();
        }
    }
    
    /**
     * 初始化复盘模式
     */
    initReplayMode() {
        // 创建复盘控制器
        this.replayController = ReplayController.enterReplayMode(this.gameState);
        this.isReplayMode = true;
        
        // 更新UI
        this.updateReplayUI();
        this.gameController.render();
        
        console.log('进入复盘模式');
    }
    
    /**
     * 更新复盘UI
     */
    updateReplayUI() {
        if (!this.replayController) return;
        
        const stepInfo = this.replayController.getCurrentStepInfo();
        
        // 更新步骤信息
        if (this.stepInfoElement) {
            this.stepInfoElement.textContent = `${stepInfo.current} / ${stepInfo.total}`;
        }
        
        // 更新进度条
        if (this.progressElement) {
            this.progressElement.value = stepInfo.percentage;
        }
        
        // 更新回合指示器
        const turnText = this.gameState.playerTurn === 'red' ? '红方回合' : '黑方回合';
        if (this.turnIndicator) {
            this.turnIndicator.textContent = turnText + ' (复盘)';
        }
    }
    
    /**
     * 退出复盘模式
     */
    exitReplayMode() {
        if (this.replayController) {
            // 恢复原始状态
            this.replayController.restoreOriginalState();
            this.replayController = null;
            this.isReplayMode = false;
            
            // 隐藏侧边栏
            if (this.sidebar) {
                this.sidebar.classList.add('hidden');
            }
            
            // 移除body的replay-active类，恢复状态区域的边距
            document.body.classList.remove('replay-active');
            
            // 恢复UI
            const turnText = this.gameState.playerTurn === 'red' ? '红方回合' : '黑方回合';
            if (this.turnIndicator) {
                this.turnIndicator.textContent = turnText;
            }
            
            this.gameController.render();
            console.log('退出复盘模式');
        }
    }
    
    /**
     * 加载对局记录列表
     */
    loadGameRecordsList() {
        if (!this.recordsList) return;
        
        const records = this.gameRecordManager.loadAllRecords();
        
        if (records.length === 0) {
            this.recordsList.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">暂无对局记录</div>';
            return;
        }
        
        this.recordsList.innerHTML = '';
        
        records.forEach((record, index) => {
            const recordElement = document.createElement('div');
            recordElement.style.cssText = `
                padding: 12px 15px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                transition: background 0.2s;
            `;
            recordElement.onmouseover = () => recordElement.style.background = '#f5f5f5';
            recordElement.onmouseout = () => recordElement.style.background = 'white';
            
            const winnerText = record.winner 
                ? (record.winner === 'red' ? '红方胜利' : '黑方胜利')
                : '和棋';
            
            const durationText = this.gameRecordManager.formatDuration(record.duration || 0);
            const dateText = this.gameRecordManager.formatDate(record.timestamp);
            
            recordElement.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: bold; color: #333; margin-bottom: 4px;">
                            第 ${index + 1} 局 - ${winnerText}
                        </div>
                        <div style="font-size: 12px; color: #666;">
                            ${dateText} | ${record.movesCount} 步 | 时长 ${durationText}
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-small" style="padding: 4px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" data-action="load" data-id="${record.id}">
                            加载
                        </button>
                        <button class="btn-small" style="padding: 4px 12px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" data-action="delete" data-id="${record.id}">
                            删除
                        </button>
                    </div>
                </div>
            `;
            
            // 添加事件监听
            recordElement.querySelector('[data-action="load"]').addEventListener('click', (e) => {
                e.stopPropagation();
                this.loadRecord(record.id);
            });
            
            recordElement.querySelector('[data-action="delete"]').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteRecord(record.id);
            });
            
            this.recordsList.appendChild(recordElement);
        });
    }
    
    /**
     * 加载指定记录
     */
    loadRecord(recordId) {
        const record = this.gameRecordManager.loadRecord(recordId);
        if (!record) {
            window.dialogManager.showError('加载失败', '找不到对局记录');
            return;
        }
        
        // 从记录恢复游戏状态
        const success = this.gameRecordManager.restoreFromRecord(record, this.gameState);
        
        if (success) {
            // 重新初始化复盘控制器
            this.initReplayMode();
            
            window.dialogManager.showInfo('提示', '对局记录加载成功');
            this.gameController.render();
        } else {
            window.dialogManager.showError('加载失败', '无法从记录恢复游戏状态');
        }
    }
    
    /**
     * 删除对局记录
     */
    deleteRecord(recordId) {
        window.dialogManager.showConfirm(
            '删除记录',
            '确定要删除这局记录吗？',
            () => {
                const success = this.gameRecordManager.deleteRecord(recordId);
                if (success) {
                    window.dialogManager.showInfo('提示', '记录已删除');
                    // 重新加载列表
                    this.loadGameRecordsList();
                } else {
                    window.dialogManager.showError('删除失败', '无法删除记录');
                }
            },
            () => {}
        );
    }
    
    /**
     * 保存当前对局记录
     */
    saveCurrentGameRecord() {
        if (this.gameState.moveHistory.length === 0) {
            return; // 没有移动记录，不保存
        }
        
        const recordId = this.gameRecordManager.saveGameRecord(
            this.gameState, 
            this.gameController.isOnline ? 'online' : 'local'
        );
        
        if (recordId) {
            console.log('对局记录已保存:', recordId);
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.ReplayManager = ReplayManager;
}
