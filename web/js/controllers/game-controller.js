/**
 * 游戏主控制器 - 匈汉象棋
 */

class GameController {
    constructor() {
        this.gameState = null;
        this.renderer = null;
        this.soundManager = null;
        this.avatarManager = null;
        
        this.selectedPiece = null;
        this.playerCamp = 'red'; // 单机模式下双方都可操作
        
        this.lastMoveNotation = '';
        this.moveHistory = [];
        
        // UI元素
        this.canvas = null;
        this.turnIndicator = null;
        this.checkAlert = null;
        this.moveList = null;
        this.stepCount = null;
        this.totalTime = null;
        
        // 网络相关（预留）
        this.isOnline = false;
        this.network = null;
    }
    
    /**
     * 初始化DOM元素
     */
    initDOMElements() {
        // 棋盘Canvas
        this.canvas = document.getElementById('chess-board');
        
        // 回合指示器
        this.turnIndicator = document.getElementById('turn-indicator');
        
        // 将军提示
        this.checkAlert = document.getElementById('check-alert');
        
        // 步数显示
        this.stepCount = document.getElementById('step-count');
        
        // 总时间显示
        this.totalTime = document.getElementById('total-time');
        
        // 棋谱列表
        this.moveList = document.getElementById('move-history');
    }
    
    /**
     * 初始化游戏
     */
    init(options = {}) {
        // 解析游戏模式
        const gameMode = options.mode || 'local';
        const roomId = options.roomId;
        
        // 匈汉象棋模式(固定)
        this.playerCamp = 'red'; // 单机模式，固定为红方视角
        
        // 初始化DOM元素
        this.initDOMElements();
        
        // 初始化游戏状态
        this.gameState = new GameState();
        
        // 初始化渲染器(匈汉象棋13x13棋盘)
        this.renderer = new ChessBoardRenderer(this.canvas, false);
        
        // 初始化管理器
        this.soundManager = new SoundManager();
        this.avatarManager = new AvatarManager();
        
        // 设置头像样式配置(匈汉象棋)
        const avatarStyle = {
            colors: {
                red: ['#ff6b6b', '#c92a2a'],
                black: ['#495057', '#212529']
            }
        };
        this.avatarManager.setAvatarStyle(avatarStyle);
        
        // 设置音效音量
        this.soundManager.setMusicVolume(0.7);
        
        // 绑定事件
        this.bindEvents();
        
        // 如果是在线模式，初始化网络
        if (gameMode === 'online' && roomId) {
            this.isOnline = true;
            this.initializeNetwork(roomId);
        }
        
        // 开始游戏循环
        this.startGameLoop();
        
        // 初始绘制
        this.render();
        
        // 播放背景音乐
        this.soundManager.playBackgroundMusic();
        
        console.log(`游戏初始化完成 - ${gameMode === 'online' ? '联机对战' : '单机对战'}`);
    }
    
    /**
     * 启动游戏循环（计时器等）
     */
    startGameLoop() {
        setInterval(() => {
            if (!this.gameState.gameOver) {
                this.updateUI();
            }
        }, 1000);
    }
    
    /**
     * 初始化网络连接
     */
    initializeNetwork(roomId) {
        console.log(`正在连接房间: ${roomId}`);
        
        // 创建WebSocket客户端
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}`;
        
        this.network = new WebSocketClient(wsUrl);
        
        // 注册事件回调
        this.network.on('opponent_move', (data) => {
            this.handleOpponentMove(data);
        });
        
        this.network.on('game_over', (data) => {
            this.handleNetworkGameOver(data);
        });
        
        this.network.on('chat_message', (data) => {
            this.addChatMessage(data.player || '对手', data.message);
        });
        
        this.network.on('undo_request', (data) => {
            this.handleUndoRequest(data);
        });
        
        this.network.on('undo_response', (data) => {
            this.handleUndoResponse(data);
        });
        
        this.network.on('player_disconnected', () => {
            window.dialogManager.showError('对手已断开连接');
        });
        
        // 连接服务器
        this.network.connect();
        
        // 加入房间
        setTimeout(() => {
            if (this.network.isConnected()) {
                this.network.send({
                    type: 'join_game_room',
                    data: { roomId: roomId }
                });
            }
        }, 500);
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 棋盘点击
        this.canvas.addEventListener('click', (e) => {
            this.handleCanvasClick(e);
        });
        
        // 返回主页按钮
        const homeBtn = document.getElementById('btn-home');
        if (homeBtn) {
            homeBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.goBackToHome();
            });
        }
        
        // 悔棋按钮 - 支持多种ID命名
        const undoBtn = document.getElementById('btn-undo') || document.getElementById('btn-regret');
        if (undoBtn) {
            undoBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.undo();
            });
        }
        
        // 重新开始按钮 - 支持多种ID命名
        const restartBtn = document.getElementById('btn-restart');
        if (restartBtn) {
            restartBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.restart();
            });
        }
        
        // 认输按钮 - 支持多种ID命名
        const surrenderBtn = document.getElementById('btn-surrender');
        if (surrenderBtn) {
            surrenderBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.resign();
            });
        }
        
        // 导航按钮 - 新游戏
        const newGameBtn = document.getElementById('btn-new-game');
        if (newGameBtn) {
            newGameBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.newGame();
            });
        }
        
        // 暗黑模式按钮
        const darkModeBtn = document.getElementById('btn-dark-mode');
        if (darkModeBtn) {
            darkModeBtn.addEventListener('click', () => {
                this.toggleDarkMode();
            });
        }
        
        // 棋谱记录按钮
        const moveHistoryBtn = document.getElementById('btn-move-history');
        if (moveHistoryBtn) {
            moveHistoryBtn.addEventListener('click', () => {
                this.showMoveHistoryModal();
            });
        }
        
        // 聊天按钮
        const chatBtn = document.getElementById('btn-chat');
        if (chatBtn) {
            chatBtn.addEventListener('click', () => {
                this.showChatModal();
            });
        }
        
        // 设置按钮
        const settingsBtn = document.getElementById('btn-settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.showSettingsModal();
            });
        }
        
        // 帮助按钮
        const helpBtn = document.getElementById('btn-help');
        if (helpBtn) {
            helpBtn.addEventListener('click', () => {
                this.soundManager.playButton();
                this.showHelpModal();
            });
        }
        
        // 关闭棋谱对话框
        const closeMoveHistory = document.getElementById('close-move-history');
        if (closeMoveHistory) {
            closeMoveHistory.addEventListener('click', () => {
                document.getElementById('move-history-modal').classList.add('hidden');
            });
        }
        
        // 关闭聊天对话框
        const closeChat = document.getElementById('close-chat');
        if (closeChat) {
            closeChat.addEventListener('click', () => {
                document.getElementById('chat-modal').classList.add('hidden');
            });
        }
        
        // 关闭设置对话框
        const closeSettings = document.getElementById('close-settings');
        if (closeSettings) {
            closeSettings.addEventListener('click', () => {
                document.getElementById('settings-modal').classList.add('hidden');
            });
        }
        
        // 关闭帮助对话框
        const closeHelp = document.getElementById('close-help');
        if (closeHelp) {
            closeHelp.addEventListener('click', () => {
                document.getElementById('help-modal').classList.add('hidden');
            });
        }
        
        // 设置对话框 - 关闭按钮
        const btnCloseSettings = document.getElementById('btn-close-settings');
        if (btnCloseSettings) {
            btnCloseSettings.addEventListener('click', () => {
                document.getElementById('settings-modal').classList.add('hidden');
            });
        }
        
        // 设置对话框 - 恢复默认按钮
        const btnResetSettings = document.getElementById('btn-reset-settings');
        if (btnResetSettings) {
            btnResetSettings.addEventListener('click', () => {
                this.resetSettings();
            });
        }
        
        // 设置对话框 - 背景音乐开关
        const btnToggleMusic = document.getElementById('btn-toggle-music');
        if (btnToggleMusic) {
            btnToggleMusic.addEventListener('click', () => {
                this.toggleBackgroundMusic();
            });
        }
        
        // 设置对话框 - 切换音乐风格
        const btnSwitchMusic = document.getElementById('btn-switch-music');
        if (btnSwitchMusic) {
            btnSwitchMusic.addEventListener('click', () => {
                this.switchMusicStyle();
            });
        }
        
        // 设置对话框 - 音量滑块
        const volumeSlider = document.getElementById('volume-slider');
        if (volumeSlider) {
            volumeSlider.addEventListener('input', (e) => {
                const volume = parseInt(e.target.value);
                this.updateVolume(volume);
            });
        }
        
        // 设置对话框 - 棋盘主题选择
        const boardThemeSelect = document.getElementById('board-theme-select');
        if (boardThemeSelect) {
            boardThemeSelect.addEventListener('change', (e) => {
                this.changeBoardTheme(e.target.value);
            });
        }
        
        // 设置对话框 - 棋子样式选择
        const pieceStyleSelect = document.getElementById('piece-style-select');
        if (pieceStyleSelect) {
            pieceStyleSelect.addEventListener('change', (e) => {
                this.changePieceStyle(e.target.value);
            });
        }
        
        // 帮助对话框 - 确定按钮
        const btnCloseHelp = document.getElementById('btn-close-help');
        if (btnCloseHelp) {
            btnCloseHelp.addEventListener('click', () => {
                document.getElementById('help-modal').classList.add('hidden');
            });
        }
        
        // 模态对话框点击背景关闭
        const moveHistoryModal = document.getElementById('move-history-modal');
        if (moveHistoryModal) {
            moveHistoryModal.addEventListener('click', (e) => {
                if (e.target === moveHistoryModal) {
                    moveHistoryModal.classList.add('hidden');
                }
            });
        }
        
        const chatModal = document.getElementById('chat-modal');
        if (chatModal) {
            chatModal.addEventListener('click', (e) => {
                if (e.target === chatModal) {
                    chatModal.classList.add('hidden');
                }
            });
        }
        
        const settingsModal = document.getElementById('settings-modal');
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    settingsModal.classList.add('hidden');
                }
            });
        }
        
        const helpModal = document.getElementById('help-modal');
        if (helpModal) {
            helpModal.addEventListener('click', (e) => {
                if (e.target === helpModal) {
                    helpModal.classList.add('hidden');
                }
            });
        }
        
        // 聊天发送按钮（模态框内）
        const sendChatBtnModal = document.getElementById('btn-send-modal');
        if (sendChatBtnModal) {
            sendChatBtnModal.addEventListener('click', () => this.sendChatMessage());
        }
        
        // 聊天输入框回车发送（模态框内）
        const chatInputModal = document.getElementById('chat-input-modal');
        if (chatInputModal) {
            chatInputModal.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendChatMessage();
            });
        }
    }
    
    /**
     * 处理棋盘点击
     */
    handleCanvasClick(event) {
        // 游戏结束或不是自己的回合，忽略点击
        if (this.gameState.gameOver) return;
        if (this.isOnline && this.gameState.playerTurn !== this.playerCamp) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        
        const pos = this.renderer.getGridPosition(mouseX, mouseY);
        if (!pos) return;
        
        const { row, col } = pos;
        
        if (this.selectedPiece) {
            // 已有选中的棋子
            const clickedPiece = this.gameState.getPieceAt(row, col);
            
            // 如果点击的是己方其他棋子，切换选中
            if (clickedPiece && clickedPiece.color === this.gameState.playerTurn) {
                // 如果点击的不是当前选中的棋子，切换选中
                if (this.selectedPiece.row !== row || this.selectedPiece.col !== col) {
                    this.selectPiece(row, col);
                    return;
                }
            }
            
            // 否则尝试移动
            this.tryMove(row, col);
        } else {
            // 选择棋子
            this.selectPiece(row, col);
        }
    }
    
    /**
     * 选择棋子
     */
    selectPiece(row, col) {
        const piece = this.gameState.getPieceAt(row, col);
        
        // 如果点击的是已选中的棋子，取消选中
        if (this.selectedPiece && this.selectedPiece.row === row && this.selectedPiece.col === col) {
            this.selectedPiece = null;
            this.renderer.clearHighlights();
            this.render();
            return;
        }
        
        // 如果点击的不是己方棋子，取消当前选中（而不是忽略）
        if (!piece || piece.color !== this.gameState.playerTurn) {
            // 如果有已选中的棋子，先取消选中
            if (this.selectedPiece) {
                this.selectedPiece = null;
                this.renderer.clearHighlights();
                this.render();
            }
            return;
        }
        
        // 播放选择音效
        this.soundManager.playSelect();
        
        this.selectedPiece = { row, col };
        this.renderer.highlightPosition(row, col);
        
        // 计算可能移动
        const { moves, capturable } = this.gameState.calculatePossibleMoves(row, col);
        this.renderer.setPossibleMoves(moves);
        this.renderer.setCapturablePositions(capturable);
        
        this.render();
    }
    
    /**
     * 尝试移动
     */
    tryMove(toRow, toCol) {
        if (!this.selectedPiece) return;
        
        const { row: fromRow, col: fromCol } = this.selectedPiece;
        
        // 执行移动
        const success = this.gameState.movePiece(fromRow, fromCol, toRow, toCol);
        
        if (success) {
            // 记录最后移动
            this.gameState.lastMove = [fromRow, fromCol, toRow, toCol];
            
            // 生成走法记谱
            const piece = this.gameState.getPieceAt(toRow, toCol);
            this.lastMoveNotation = this.generateMoveNotation(piece, fromRow, fromCol, toRow, toCol);
            this.addMoveToHistory(this.lastMoveNotation);
            
            // 如果在线，发送移动
            if (this.isOnline) {
                this.network.sendMove(fromRow, fromCol, toRow, toCol);
            }
            
            // 更新UI
            this.updateUI();
            
            // 播放音效
            if (this.gameState.moveHistory.length > 0) {
                const lastMove = this.gameState.moveHistory[this.gameState.moveHistory.length - 1];
                if (lastMove.capturedPiece) {
                    this.soundManager.playCapture();
                } else {
                    this.soundManager.playMove();
                }
            }
            
            // 检查将军
            if (this.gameState.inCheck) {
                this.soundManager.playCheck();
                this.showCheckAlert();
            } else {
                this.hideCheckAlert();
            }
            
            // 清除选择
            this.selectedPiece = null;
            this.renderer.clearHighlights();
            
            // 检查游戏结束
            if (this.gameState.gameOver) {
                this.handleGameEnd();
            } else {
                // 检查将军/绝杀状态
                this.soundManager.checkAndPlayGameSound(this.gameState);
            }
        }
        
        this.render();
    }
    
    /**
     * 新对局（重置全部状态 = 新游戏）
     */
    newGame() {
        this.avatarManager.clearCache();
        this.gameState.reset();
        this.selectedPiece = null;
        this.moveHistory = [];
        this.lastMoveNotation = '';
        this.gameState.lastMove = null;
        
        // 清空棋谱记录UI
        const moveHistoryContent = document.getElementById('move-history-content');
        if (moveHistoryContent) {
            moveHistoryContent.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">暂无走棋记录</div>';
        }
        
        // 清空聊天框
        const chatContent = document.getElementById('chat-content');
        if (chatContent) {
            chatContent.innerHTML = '<p style="color: #999;">欢迎来到匈汉象棋！</p>';
        }
        
        this.updateUI();
        this.render();
        
        console.log('新对局已创建');
    }
    
    /**
     * 重新开始（重置当前棋盘，保留模式）
     */
    resetBoard() {
        this.newGame();
        console.log('棋盘已重置');
    }
    
    /**
     * 悔棋
     */
    undo() {
        if (this.gameState.moveHistory.length === 0) {
            window.dialogManager.showInfo('提示', '当前没有可以悔棋的步数');
            return;
        }
        
        // 在线模式下需要对方同意
        if (this.isOnline) {
            this.network.sendUndoRequest();
            window.dialogManager.showInfo('悔棋请求', '已发送悔棋请求，等待对方同意...');
            return;
        }
        
        // 本地模式显示确认对话框
        window.dialogManager.showConfirm(
            '悔棋',
            '确定要悔棋吗？',
            () => {
                // 确认悔棋
                this.gameState.undoMove();
                this.moveHistory.pop();
                this.updateUI();
                this.render();
            },
            () => {
                // 取消悔棋
                console.log('取消悔棋');
            }
        );
    }
    
    /**
     * 重新开始
     */
    restart() {
        window.dialogManager.showConfirm(
            '重新开始',
            '确定要重新开始游戏吗？当前游戏进度将丢失。',
            () => {
                // 确认重新开始
                this.avatarManager.clearCache();
                
                this.gameState.reset();
                this.selectedPiece = null;
                this.moveHistory = [];
                this.lastMoveNotation = '';
                this.gameState.lastMove = null;
                
                this.updateUI();
                this.render();
                
                if (this.isOnline) {
                    this.network.sendRestartRequest();
                }
            },
            () => {
                // 取消重新开始
                console.log('取消重新开始');
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
                // 确认认输
                this.gameState.gameOver = true;
                this.gameState.winner = this.playerCamp === 'red' ? 'black' : 'red';
                this.handleGameEnd();
                
                if (this.isOnline) {
                    this.network.sendResign();
                }
            },
            () => {
                // 取消认输
                console.log('取消认输');
            }
        );
    }
    
    /**
     * 处理游戏结束
     */
    handleGameEnd() {
        const winnerText = this.gameState.winner 
            ? `${this.gameState.winner === 'red' ? '红方' : '黑方'}胜利！`
            : '和棋';
        
        // 播放游戏结束音效
        if (this.gameState.winner) {
            if (this.gameState.winner === this.playerCamp) {
                this.soundManager.playVictory();
            } else {
                this.soundManager.playDefeat();
            }
        }
        
        // 停止背景音乐
        this.soundManager.stopBackgroundMusic();
        
        // 显示游戏结束对话框
        window.dialogManager.showConfirm(
            '游戏结束',
            `<h2 style="color: ${this.gameState.winner === 'red' ? '#d32f2f' : '#333'}">${winnerText}</h2><p>是否重新开始？</p>`,
            () => {
                this.newGame();
            },
            () => {
                // 返回主页
                window.location.href = '/';
            }
        );
    }
    
    /**
     * 更新UI
     */
    updateUI() {
        // 更新回合指示器
        const turnText = this.gameState.playerTurn === 'red' ? '红方回合' : '黑方回合';
        if (this.turnIndicator) {
            this.turnIndicator.textContent = turnText;
            
            // 更新样式
            if (this.gameState.playerTurn === 'red') {
                this.turnIndicator.style.color = '#b41e1e';
            } else {
                this.turnIndicator.style.color = '#212121';
            }
        }
        
        // 更新步数
        if (this.stepCount) {
            this.stepCount.textContent = this.gameState.movesCount;
        }
        
        // 更新时间
        const { redTime, blackTime } = this.gameState.getTimes();
        const totalTime = redTime + blackTime;
        if (this.totalTime) {
            this.totalTime.textContent = this.formatTime(totalTime);
        }
        
        // 更新悔棋按钮状态
        const undoBtn = document.getElementById('btn-regret');
        if (undoBtn) {
            undoBtn.disabled = this.gameState.moveHistory.length === 0;
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
            
        this.addChatMessage('你', message);
        input.value = '';
            
        // 如果是在线模式，发送消息给对手
        if (this.isOnline && this.network) {
            this.network.send({
                type: 'chat_message',
                data: { message: message }
            });
        }
    }
        
    /**
     * 添加聊天消息
     */
    addChatMessage(sender, message) {
        const chatContent = document.getElementById('chat-content');
        if (!chatContent) return;
            
        const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        const messageElement = document.createElement('p');
        messageElement.style.marginBottom = '5px';
        messageElement.textContent = `[${time}] ${sender}: ${message}`;
        chatContent.appendChild(messageElement);
        chatContent.scrollTop = chatContent.scrollHeight;
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
            // 聚焦到输入框
            setTimeout(() => {
                const input = document.getElementById('chat-input-modal');
                if (input) input.focus();
            }, 100);
        }
    }
        
    /**
     * 显示设置对话框
     */
    showSettingsModal() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            // 更新UI状态
            this.updateSettingsUI();
            modal.classList.remove('hidden');
        }
    }
    
    /**
     * 更新设置UI状态
     */
    updateSettingsUI() {
        // 更新音乐状态
        const musicStatusText = document.getElementById('music-status-text');
        const musicStyleText = document.getElementById('music-style-text');
        if (musicStatusText) {
            musicStatusText.textContent = this.soundManager.musicEnabled ? '开启' : '关闭';
        }
        if (musicStyleText) {
            musicStyleText.textContent = this.soundManager.currentMusicStyle === 'qq' ? 'QQ风格' : 'FC风格';
        }
        
        // 更新音量
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
     * 显示设置（旧方法，保留兼容）
     */
    showSettings() {
        this.showSettingsModal();
    }
        
    /**
     * 显示帮助（旧方法，保留兼容）
     */
    showHelp() {
        this.showHelpModal();
    }
        
    /**
     * 切换暗黑模式
     */
    toggleDarkMode() {
        const body = document.body;
        const darkModeBtn = document.getElementById('btn-dark-mode');
            
        body.classList.toggle('dark-mode');
            
        const isDark = body.classList.contains('dark-mode');
        if (darkModeBtn) {
            darkModeBtn.textContent = isDark ? '️' : '🌙';
        }
            
        // 保存用户偏好
        localStorage.setItem('darkMode', isDark);
            
        console.log(`暗黑模式: ${isDark ? '开启' : '关闭'}`);
    }
    
    /**
     * 返回主页
     */
    goBackToHome() {
        window.dialogManager.showConfirm(
            '返回主页',
            '确定要返回主页吗？当前游戏进度将丢失。',
            () => {
                // 停止背景音乐
                this.soundManager.stopBackgroundMusic();
                // 返回主页
                window.location.href = '/';
            },
            () => {
                console.log('取消返回主页');
            }
        );
    }
    
    /**
     * 切换背景音乐
     */
    toggleBackgroundMusic() {
        const musicStatusText = document.getElementById('music-status-text');
        
        if (this.soundManager.musicEnabled) {
            this.soundManager.stopBackgroundMusic();
            this.soundManager.musicEnabled = false;
            if (musicStatusText) {
                musicStatusText.textContent = '关闭';
            }
        } else {
            this.soundManager.playBackgroundMusic();
            this.soundManager.musicEnabled = true;
            if (musicStatusText) {
                musicStatusText.textContent = '开启';
            }
        }
        
        // 保存设置
        localStorage.setItem('musicEnabled', this.soundManager.musicEnabled);
    }
    
    /**
     * 切换音乐风格
     */
    switchMusicStyle() {
        const musicStyleText = document.getElementById('music-style-text');
        const newStyle = this.soundManager.toggleMusicStyle();
        
        if (musicStyleText) {
            musicStyleText.textContent = newStyle === 'qq' ? 'QQ风格' : 'FC风格';
        }
        
        // 保存设置
        localStorage.setItem('musicStyle', newStyle);
    }
    
    /**
     * 更新音量
     */
    updateVolume(volume) {
        const volumeValue = document.getElementById('volume-value');
        const volumePercent = Math.round(volume);
        
        if (volumeValue) {
            volumeValue.textContent = `${volumePercent}%`;
        }
        
        // 更新音效管理器音量
        this.soundManager.setMusicVolume(volume / 100);
        
        // 保存设置
        localStorage.setItem('volume', volume);
    }
    
    /**
     * 切换棋盘主题
     */
    changeBoardTheme(theme) {
        console.log(`切换棋盘主题: ${theme}`);
        
        // 通知渲染器更新主题
        if (this.renderer) {
            this.renderer.setBoardTheme(theme);
        }
        
        // 保存设置
        localStorage.setItem('boardTheme', theme);
    }
    
    /**
     * 切换棋子样式
     */
    changePieceStyle(style) {
        console.log(`切换棋子样式: ${style}`);
        
        // 通知渲染器更新棋子样式
        if (this.renderer) {
            this.renderer.setPieceStyle(style);
        }
        
        // 保存设置
        localStorage.setItem('pieceStyle', style);
    }
    
    /**
     * 重置设置
     */
    resetSettings() {
        window.dialogManager.showConfirm(
            '恢复默认设置',
            '确定要恢复所有设置为默认值吗？',
            () => {
                console.log('开始恢复默认设置...');
                
                // 恢复默认音量
                this.soundManager.setMusicVolume(0.7);
                
                // 恢复默认棋盘主题
                if (this.renderer) {
                    this.renderer.setBoardTheme('classic');
                }
                
                // 恢复默认棋子样式
                if (this.renderer) {
                    this.renderer.setPieceStyle('traditional');
                }
                
                // 清除保存的设置
                localStorage.removeItem('volume');
                localStorage.removeItem('boardTheme');
                localStorage.removeItem('pieceStyle');
                localStorage.removeItem('musicEnabled');
                localStorage.removeItem('musicStyle');
                
                // 更新UI显示
                this.updateSettingsUI();
                
                // 更新下拉框的选中值
                const boardThemeSelect = document.getElementById('board-theme-select');
                if (boardThemeSelect) {
                    boardThemeSelect.value = 'classic';
                }
                
                const pieceStyleSelect = document.getElementById('piece-style-select');
                if (pieceStyleSelect) {
                    pieceStyleSelect.value = 'traditional';
                }
                
                console.log('设置已恢复为默认值');
                window.dialogManager.showInfo('提示', '设置已恢复为默认值');
            },
            () => {
                console.log('取消恢复默认设置');
            }
        );
    }
        
    
    /**
     * 显示将军提示
     */
    showCheckAlert() {
        if (this.checkAlert) {
            this.checkAlert.classList.remove('hidden');
            setTimeout(() => {
                this.checkAlert.classList.add('hidden');
            }, 3000);
        }
    }
    
    /**
     * 隐藏将军提示
     */
    hideCheckAlert() {
        if (this.checkAlert) {
            this.checkAlert.classList.add('hidden');
        }
    }
    
    /**
     * 添加到历史记录
     */
    addMoveToHistory(notation) {
        this.moveHistory.push(notation);
        
        // 在控制台输出
        console.log(`走法记录: ${this.moveHistory.length}. ${notation}`);
        
        // 更新模态框中的棋谱记录
        const moveHistoryContent = document.getElementById('move-history-content');
        if (moveHistoryContent) {
            // 如果是第一次添加，清空提示文字
            if (this.moveHistory.length === 1) {
                moveHistoryContent.innerHTML = '';
            }
            
            const moveItem = document.createElement('div');
            moveItem.className = 'move-item';
            moveItem.textContent = `${this.moveHistory.length}. ${notation}`;
            moveHistoryContent.appendChild(moveItem);
            
            // 滚动到底部
            moveHistoryContent.scrollTop = moveHistoryContent.scrollHeight;
        }
    }
    
    /**
     * 生成走法记谱
     */
    generateMoveNotation(piece, fromRow, fromCol, toRow, toCol) {
        // 简化版记谱
        const pieceName = piece.name;
        const action = piece.col === toCol ? '进' : piece.row === toRow ? '平' : '退';
        const distance = Math.abs(toCol - fromCol) || Math.abs(toRow - fromRow);
        
        return `${pieceName}${action}${distance}`;
    }
    
    /**
     * 格式化时间
     * @param {number} seconds - 秒数
     * @returns {string} 格式化后的时间字符串 (MM:SS)
     */
    formatTime(seconds) {
        // mins 是 minutes 的缩写，表示分钟数
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    /**
     * 处理对手移动
     */
    handleOpponentMove(data) {
        console.log('对手移动:', data);
        
        const { fromRow, fromCol, toRow, toCol } = data;
        
        // 执行移动
        this.gameState.movePiece(fromRow, fromCol, toRow, toCol);
        
        // 记录最后移动
        this.gameState.lastMove = [fromRow, fromCol, toRow, toCol];
        
        // 更新UI
        this.updateUI();
        
        // 播放音效
        this.soundManager.playMove();
        
        // 检查将军
        if (this.gameState.inCheck) {
            this.soundManager.playCheck();
            this.showCheckAlert();
        }
        
        // 渲染棋盘
        this.render();
    }
    
    /**
     * 处理网络模式游戏结束
     */
    handleNetworkGameOver(data) {
        console.log('游戏结束:', data);
        
        this.gameState.gameOver = true;
        this.gameState.winner = data.winner;
        
        this.handleGameEnd();
    }
    
    /**
     * 处理悔棋请求
     */
    handleUndoRequest(data) {
        window.dialogManager.showConfirm(
            '悔棋请求',
            '对手请求悔棋，是否同意？',
            () => {
                // 同意悔棋
                this.network.sendUndoResponse(true);
                this.gameState.undoMove();
                this.moveHistory.pop();
                this.updateUI();
                this.render();
            },
            () => {
                // 拒绝悔棋
                this.network.sendUndoResponse(false);
                window.dialogManager.showInfo('提示', '已拒绝对手的悔棋请求');
            }
        );
    }
    
    /**
     * 处理悔棋响应
     */
    handleUndoResponse(data) {
        if (data.accepted) {
            window.dialogManager.showInfo('提示', '对手同意了你的悔棋请求');
            this.gameState.undoMove();
            this.moveHistory.pop();
            this.updateUI();
            this.render();
        } else {
            window.dialogManager.showInfo('提示', '对手拒绝了你的悔棋请求');
        }
    }
    
    /**
     * 渲染棋盘
     */
    render() {
        if (this.renderer && this.gameState) {
            console.log('渲染棋盘:', {
                piecesCount: this.gameState.pieces.length,
                lastMove: this.gameState.lastMove,
                canvasSize: `${this.canvas.width}x${this.canvas.height}`
            });
            this.renderer.render(this.gameState.pieces, this.gameState.lastMove);
        } else {
            console.error('渲染失败:', {
                hasRenderer: !!this.renderer,
                hasGameState: !!this.gameState
            });
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameController = GameController;
}
