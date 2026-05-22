/**
 * 游戏主控制器 - 匈汉象棋（重构版）
 * 职责：协调各子控制器，管理游戏生命周期
 */

class GameController {
    constructor() {
        // 核心状态
        this.gameState = null;
        this.renderer = null;
        
        // 事件分发器
        this.events = new EventDispatcher();
        
        // 子控制器
        this.logicHandler = null;
        this.networkHandler = null;
        this.uiController = null;
        this.replayManager = null;
        
        // 辅助管理器
        this.soundManager = null;
        this.avatarManager = null;
        this.ruleConfig = null;
        this.tauntManager = null;
        this.statisticsManager = null;
        
        // 游戏配置
        this.playerCamp = 'red';
        this.isOnline = false;
        this.isReplayMode = false;
        
        // Canvas引用
        this.canvas = null;
    }
    
    /**
     * 初始化游戏
     */
    init(options = {}) {
        const gameMode = options.mode || 'local';
        const roomId = options.roomId;
        
        // 初始化Canvas
        this.canvas = document.getElementById('chess-board');
        
        // 初始化游戏状态
        this.gameState = new GameState();
        
        // 初始化渲染器
        this.renderer = new ChessBoardRenderer(this.canvas, false);
        
        // 初始化规则配置
        this.ruleConfig = new GameRuleConfig();
        this.ruleConfig.bindUI();
        
        // 初始化子控制器
        this.initializeControllers();
        
        // 初始化辅助管理器
        this.initializeManagers();
        
        // 绑定事件处理
        this.bindEventHandlers();
        
        // 如果是在线模式，初始化网络
        if (gameMode === 'online' && roomId) {
            this.isOnline = true;
            this.networkHandler.initialize(roomId);
        }
        
        // 启动游戏循环
        this.startGameLoop();
        
        // 初始渲染
        this.render();
        
        // 播放背景音乐
        this.soundManager.playBackgroundMusic();
        
        console.log(`游戏初始化完成 - ${gameMode === 'online' ? '联机对战' : '单机对战'}`);
    }
    
    /**
     * 初始化子控制器
     */
    initializeControllers() {
        this.logicHandler = new GameLogicHandler(this.gameState, this.ruleConfig, this.events);
        this.networkHandler = new NetworkHandler(this.events);
        this.uiController = new UIController(this.canvas, this.events);
        this.uiController.initElements();
        this.replayManager = new ReplayManager(this);
        this.replayManager.init();
    }
    
    /**
     * 初始化辅助管理器
     */
    initializeManagers() {
        this.soundManager = new SoundManager();
        this.avatarManager = new AvatarManager();
        this.tauntManager = new TauntManager();
        this.statisticsManager = new StatisticsManager();
        
        this.avatarManager.setAvatarStyle({
            colors: {
                red: ['#ff6b6b', '#c92a2a'],
                black: ['#495057', '#212529']
            }
        });
        
        this.soundManager.setMusicVolume(0.7);
    }
    
    /**
     * 绑定事件处理器
     */
    bindEventHandlers() {
        // 绑定UI事件
        this.uiController.bindEvents({
            onCanvasClick: (pos) => this.handleCanvasClick(pos),
            onHome: () => this.goBackToHome(),
            onUndo: () => this.undo(),
            onRestart: () => this.restart(),
            onSurrender: () => this.resign(),
            onNewGame: () => this.newGame(),
            onDarkMode: () => this.uiController.toggleDarkMode(),
            onMoveHistory: () => this.showMoveHistoryModal(),
            onReplay: () => this.replayManager.showReplaySidebar(),
            onChat: () => this.showChatModal(),
            onSettings: () => this.showSettingsModal(),
            onHelp: () => this.showHelpModal(),
            onChatSend: () => this.sendChatMessage()
        });
        
        // 监听游戏事件
        this.events.on('piece:moved', () => {
            this.soundManager.playMove();
            this.updateUI();
        });
        
        this.events.on('piece:captured', (data) => {
            this.soundManager.playCapture();
            const capturedType = this.getPieceType(data.capturedPiece);
            if (capturedType) {
                this.statisticsManager.updatePiecesCaptured(capturedType);
            }
        });
        
        this.events.on('check:detected', () => {
            this.soundManager.playCheck();
            this.uiController.updateCheckAlert(true);
        });
        
        this.events.on('checkmate:detected', () => {
            this.handleGameEnd();
        });
        
        this.events.on('turn:changed', () => {
            this.updateUI();
        });
        
        this.events.on('game:reset', () => {
            this.updateUI();
            this.render();
        });
        
        // 监听网络事件
        this.events.on('opponent:move', (data) => {
            this.handleOpponentMove(data);
        });
        
        this.events.on('chat:message', (data) => {
            this.addChatMessage(data.player || '对手', data.message);
        });
        
        this.events.on('undo:request', () => {
            this.handleUndoRequest();
        });
        
        this.events.on('restart:request', () => {
            this.handleRestartRequest();
        });
    }
    
    /**
     * 启动游戏循环
     */
    startGameLoop() {
        setInterval(() => {
            if (!this.gameState.gameOver) {
                this.updateUI();
            }
        }, 1000);
    }
    
    /**
     * 处理Canvas点击
     */
    handleCanvasClick(pos) {
        if (this.gameState.gameOver) return;
        if (this.isOnline && this.gameState.playerTurn !== this.playerCamp) return;
        
        const piece = this.gameState.getPieceAt(pos.row, pos.col);
        
        // 检查是否点击了兵的出生点
        if (!this.uiController.getSelectedPiece()) {
            if (!piece && this.gameState.isBingSpawnPoint(pos.row, pos.col, this.gameState.playerTurn)) {
                const ruleConfig = window.GameRules ? window.GameRules.getRuleConfig() : {};
                if (ruleConfig.pawnResurrection) {
                    const result = this.logicHandler.trySpawnBing(pos.row, pos.col);
                    if (result.success) {
                        this.render();
                    }
                    return;
                }
            }
        }
        
        // 选择或移动棋子
        if (this.uiController.getSelectedPiece()) {
            const selectedPos = this.uiController.getSelectedPiece();
            const result = this.logicHandler.executeMove(selectedPos, pos);
            
            if (result.success) {
                this.uiController.clearSelection();
                this.renderer.clearHighlights();
                
                if (result.moveData && result.moveData.gameOver) {
                    this.handleGameEnd();
                }
            } else {
                // 如果点击的是己方其他棋子，切换选中
                if (piece && piece.camp === this.gameState.playerTurn) {
                    this.selectPiece(pos);
                }
            }
        } else {
            // 选择棋子
            if (piece && piece.camp === this.gameState.playerTurn) {
                this.selectPiece(pos);
            }
        }
        
        this.render();
    }
    
    /**
     * 选择棋子
     */
    selectPiece(pos) {
        this.soundManager.playSelect();
        this.uiController.highlightSelectedPiece(pos);
        
        const { moves, capturable } = this.gameState.calculatePossibleMoves(pos.row, pos.col);
        this.renderer.setPossibleMoves(moves);
        this.renderer.setCapturablePositions(capturable);
        
        this.render();
    }
    
    /**
     * 处理对手移动
     */
    handleOpponentMove(data) {
        const { fromRow, fromCol, toRow, toCol } = data;
        
        // 在临时状态上执行移动以更新显示
        const piece = this.gameState.getPieceAt(fromRow, fromCol);
        if (piece) {
            const capturedPiece = this.gameState.getPieceAt(toRow, toCol);
            if (capturedPiece) {
                this.gameState.pieces = this.gameState.pieces.filter(p => p !== capturedPiece);
            }
            
            piece.moveTo(toRow, toCol);
            this.gameState.playerTurn = this.gameState.playerTurn === 'red' ? 'black' : 'red';
            this.gameState.movesCount++;
            
            const { GameRules } = window;
            this.gameState.inCheck = GameRules.isCheck(this.gameState.pieces, this.gameState.playerTurn);
            
            this.updateUI();
            this.soundManager.playMove();
            
            if (this.gameState.inCheck) {
                this.soundManager.playCheck();
                this.uiController.updateCheckAlert(true);
            }
            
            if (this.gameState.gameOver) {
                this.handleGameEnd();
            }
            
            this.render();
        }
    }
    
    /**
     * 悔棋
     */
    undo() {
        if (this.isOnline) {
            this.networkHandler.requestUndo();
            window.dialogManager.showInfo('悔棋请求', '已发送悔棋请求，等待对方同意...');
            return;
        }
        
        const result = this.logicHandler.undo();
        if (result.success) {
            this.updateUI();
            this.render();
        } else {
            window.dialogManager.showInfo('提示', result.message);
        }
    }
    
    /**
     * 重新开始
     */
    restart() {
        window.dialogManager.showConfirm(
            '重新开始',
            '确定要重新开始游戏吗？当前游戏进度将丢失。',
            () => {
                this.logicHandler.restart();
                this.avatarManager.clearCache();
                this.updateUI();
                this.render();
                
                if (this.isOnline) {
                    this.networkHandler.requestRestart();
                }
            }
        );
    }
    
    /**
     * 认输
     */
    resign() {
        window.dialogManager.showConfirm(
            '认输',
            '确定要认输吗？认输后本局游戏将结束。',
            () => {
                this.logicHandler.resign(this.playerCamp);
                this.handleGameEnd();
                
                if (this.isOnline) {
                    this.networkHandler.resign();
                }
            }
        );
    }
    
    /**
     * 新对局
     */
    newGame() {
        this.logicHandler.restart();
        this.avatarManager.clearCache();
        this.updateUI();
        this.render();
    }
    
    /**
     * 处理游戏结束
     */
    handleGameEnd() {
        const winnerText = this.gameState.winner 
            ? `${this.gameState.winner === 'red' ? '红方' : '黑方'}胜利！`
            : '和棋';
        
        // 保存对局记录
        this.replayManager.saveCurrentGameRecord();
        
        // 更新统计数据
        const { redTime, blackTime } = this.gameState.getTimes();
        const gameDuration = redTime + blackTime;
        
        this.statisticsManager.updateGamesPlayed();
        this.statisticsManager.updateGameResult(
            this.gameState.winner || 'draw',
            gameDuration
        );
        this.statisticsManager.updateTotalMoves(this.gameState.movesCount);
        
        // 播放音效
        if (this.gameState.winner) {
            if (this.gameState.winner === this.playerCamp) {
                this.soundManager.playVictory();
                setTimeout(() => {
                    const taunt = this.tauntManager.getRandomTaunt();
                    window.dialogManager.showInfo(' 胜利！', taunt);
                }, 500);
            } else {
                this.soundManager.playDefeat();
            }
        }
        
        this.soundManager.stopBackgroundMusic();
        
        // 显示游戏结束对话框
        window.dialogManager.showConfirm(
            '游戏结束',
            `<h2 style="color: ${this.gameState.winner === 'red' ? '#d32f2f' : '#333'}">${winnerText}</h2><p>是否复盘或重新开始？</p>`,
            () => {
                this.replayManager.showReplaySidebar();
            },
            () => {
                this.newGame();
            },
            '复盘',
            '重新开始'
        );
    }
    
    /**
     * 更新UI
     */
    updateUI() {
        const stats = {
            stepCount: this.gameState.movesCount,
            totalTime: this.gameState.getTimes().redTime + this.gameState.getTimes().blackTime
        };
        
        this.uiController.updateUI(this.gameState, stats);
        this.uiController.updateMoveHistory(this.logicHandler.getMoveHistory());
    }
    
    /**
     * 渲染棋盘
     */
    render() {
        if (this.renderer && this.gameState) {
            this.renderer.render(this.gameState.pieces, this.gameState.lastMove);
        }
    }
    
    /**
     * 显示棋谱记录对话框
     */
    showMoveHistoryModal() {
        const modal = document.getElementById('move-history-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }
    
    /**
     * 显示聊天对话框
     */
    showChatModal() {
        const modal = document.getElementById('chat-modal');
        if (modal) {
            modal.classList.remove('hidden');
            setTimeout(() => {
                const input = document.getElementById('chat-input-modal');
                if (input) input.focus();
            }, 100);
        }
    }
    
    /**
     * 发送聊天消息
     */
    sendChatMessage() {
        const input = document.getElementById('chat-input-modal');
        if (!input) return;
        
        const message = input.value.trim();
        if (!message) return;
        
        this.uiController.addChatMessage('你', message, true);
        input.value = '';
        
        if (this.isOnline) {
            this.networkHandler.sendChatMessage(message);
        }
    }
    
    /**
     * 添加聊天消息
     */
    addChatMessage(sender, message) {
        this.uiController.addChatMessage(sender, message, false);
    }
    
    /**
     * 显示设置对话框
     */
    showSettingsModal() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            this.updateSettingsUI();
            modal.classList.remove('hidden');
        }
    }
    
    /**
     * 更新设置UI
     */
    updateSettingsUI() {
        const musicStatusText = document.getElementById('music-status-text');
        const musicStyleText = document.getElementById('music-style-text');
        
        if (musicStatusText) {
            musicStatusText.textContent = this.soundManager.musicEnabled ? '开启' : '关闭';
        }
        if (musicStyleText) {
            musicStyleText.textContent = this.soundManager.currentMusicStyle === 'qq' ? 'QQ风格' : 'FC风格';
        }
        
        const volumeValue = document.getElementById('volume-value');
        const volumeSlider = document.getElementById('volume-slider');
        const volumePercent = Math.round(this.soundManager.volume * 100);
        
        if (volumeValue) {
            volumeValue.textContent = `${volumePercent}%`;
        }
        if (volumeSlider) {
            volumeSlider.value = volumePercent;
        }
    }
    
    /**
     * 显示帮助对话框
     */
    showHelpModal() {
        const modal = document.getElementById('help-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }
    
    /**
     * 返回主页
     */
    goBackToHome() {
        window.dialogManager.showConfirm(
            '返回主页',
            '确定要返回主页吗？当前游戏进度将丢失。',
            () => {
                this.soundManager.stopBackgroundMusic();
                window.location.href = '/';
            }
        );
    }
    
    /**
     * 处理悔棋请求
     */
    handleUndoRequest() {
        window.dialogManager.showConfirm(
            '悔棋请求',
            '对手请求悔棋，是否同意？',
            () => {
                this.networkHandler.respondUndo(true);
                this.logicHandler.undo();
                this.updateUI();
                this.render();
            },
            () => {
                this.networkHandler.respondUndo(false);
                window.dialogManager.showInfo('提示', '已拒绝对手的悔棋请求');
            }
        );
    }
    
    /**
     * 处理重新开始请求
     */
    handleRestartRequest() {
        window.dialogManager.showConfirm(
            '重新开始请求',
            '对手请求重新开始游戏，是否同意？',
            () => {
                this.networkHandler.respondRestart(true);
                this.logicHandler.restart();
                this.updateUI();
                this.render();
            },
            () => {
                this.networkHandler.respondRestart(false);
                window.dialogManager.showInfo('提示', '已拒绝对手的重新开始请求');
            }
        );
    }
    
    /**
     * 获取棋子类型
     */
    getPieceType(pieceName) {
        const typeMap = {
            '車': 'ju', '马': 'ma', '馬': 'ma',
            '相': 'xiang', '象': 'xiang',
            '士': 'shi', '仕': 'shi',
            '将': 'king', '帥': 'king', '帅': 'king',
            '炮': 'pao', '砲': 'pao',
            '兵': 'pawn', '卒': 'pawn',
            '射': 'she', '䠶': 'she',
            '檑': 'lei', '礌': 'lei'
        };
        return typeMap[pieceName] || null;
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameController = GameController;
}
