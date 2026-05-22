/**
 * UI 控制器 - 管理所有用户界面交互
 * 职责：事件绑定、UI更新、对话框管理、Canvas交互
 */

class UIController {
    constructor(canvas, eventDispatcher) {
        this.canvas = canvas;
        this.events = eventDispatcher;
        
        // UI元素引用
        this.elements = {};
        
        // 状态
        this.selectedPiece = null;
        this.isDarkMode = false;
        
        // Canvas相关
        this.cellSize = 0;
        this.offsetX = 0;
        this.offsetY = 0;
    }

    /**
     * 初始化DOM元素引用
     */
    initElements() {
        this.elements = {
            // 棋盘
            canvas: document.getElementById('chess-board'),
            
            // 状态显示
            turnIndicator: document.getElementById('turn-indicator'),
            checkAlert: document.getElementById('check-alert'),
            stepCount: document.getElementById('step-count'),
            totalTime: document.getElementById('total-time'),
            
            // 棋谱
            moveList: document.getElementById('move-history'),
            
            // 按钮
            homeBtn: document.getElementById('btn-home'),
            undoBtn: document.getElementById('btn-undo'),
            restartBtn: document.getElementById('btn-restart'),
            surrenderBtn: document.getElementById('btn-surrender'),
            newGameBtn: document.getElementById('btn-new-game'),
            darkModeBtn: document.getElementById('btn-dark-mode'),
            moveHistoryBtn: document.getElementById('btn-move-history'),
            replayBtn: document.getElementById('btn-replay'),
            chatBtn: document.getElementById('btn-chat'),
            settingsBtn: document.getElementById('btn-settings'),
            helpBtn: document.getElementById('btn-help'),
            
            // 关闭按钮
            closeMoveHistory: document.getElementById('close-move-history'),
            closeChat: document.getElementById('close-chat'),
            closeSettings: document.getElementById('close-settings'),
            closeHelp: document.getElementById('close-help'),
            closeReplaySidebar: document.getElementById('close-replay-sidebar'),
            
            // 聊天
            chatInput: document.getElementById('chat-input'),
            chatSendBtn: document.getElementById('chat-send'),
            chatMessages: document.getElementById('chat-messages'),
            
            // 侧边栏
            moveHistoryPanel: document.getElementById('move-history-panel'),
            chatPanel: document.getElementById('chat-panel'),
            settingsPanel: document.getElementById('settings-panel'),
            helpPanel: document.getElementById('help-panel'),
            replaySidebar: document.getElementById('replay-sidebar')
        };
    }

    /**
     * 绑定所有事件
     * @param {Object} handlers - 事件处理函数集合
     */
    bindEvents(handlers) {
        this.initElements();
        
        // 初始化隐藏将军提示
        if (this.elements.checkAlert) {
            this.elements.checkAlert.style.display = 'none';
        }
        
        // Canvas点击事件
        if (this.elements.canvas) {
            this.elements.canvas.addEventListener('click', (e) => {
                const pos = this.getCanvasPosition(e);
                handlers.onCanvasClick(pos);
            });
        }

        // 工具栏按钮
        this.bindButton('homeBtn', handlers.onHome);
        this.bindButton('undoBtn', handlers.onUndo);
        this.bindButton('restartBtn', handlers.onRestart);
        this.bindButton('surrenderBtn', handlers.onSurrender);
        this.bindButton('newGameBtn', handlers.onNewGame);
        this.bindButton('darkModeBtn', handlers.onDarkMode);
        this.bindButton('moveHistoryBtn', handlers.onMoveHistory);
        this.bindButton('replayBtn', handlers.onReplay);
        this.bindButton('chatBtn', handlers.onChat);
        this.bindButton('settingsBtn', handlers.onSettings);
        this.bindButton('helpBtn', handlers.onHelp);

        // 关闭按钮
        this.bindButton('closeMoveHistory', () => this.togglePanel('moveHistoryPanel', false));
        this.bindButton('closeChat', () => this.togglePanel('chatPanel', false));
        this.bindButton('closeSettings', () => this.togglePanel('settingsPanel', false));
        this.bindButton('closeHelp', () => this.togglePanel('helpPanel', false));
        this.bindButton('closeReplaySidebar', () => this.togglePanel('replaySidebar', false));

        // 聊天发送
        if (this.elements.chatSendBtn) {
            this.elements.chatSendBtn.addEventListener('click', handlers.onChatSend);
        }
        
        if (this.elements.chatInput) {
            this.elements.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handlers.onChatSend();
                }
            });
        }
        
        // 设置对话框 - 背景音乐开关
        const btnToggleMusic = document.getElementById('btn-toggle-music');
        if (btnToggleMusic && handlers.onToggleMusic) {
            btnToggleMusic.addEventListener('click', handlers.onToggleMusic);
        }
        
        // 设置对话框 - 切换音乐风格
        const btnSwitchMusic = document.getElementById('btn-switch-music');
        if (btnSwitchMusic && handlers.onSwitchMusic) {
            btnSwitchMusic.addEventListener('click', handlers.onSwitchMusic);
        }
        
        // 设置对话框 - 音量滑块
        const volumeSlider = document.getElementById('volume-slider');
        if (volumeSlider && handlers.onVolumeChange) {
            volumeSlider.addEventListener('input', (e) => {
                handlers.onVolumeChange(parseInt(e.target.value));
            });
        }
        
        // 设置对话框 - 棋盘主题选择
        const boardThemeSelect = document.getElementById('board-theme-select');
        if (boardThemeSelect && handlers.onBoardThemeChange) {
            boardThemeSelect.addEventListener('change', (e) => {
                handlers.onBoardThemeChange(e.target.value);
            });
        }
        
        // 设置对话框 - 棋子样式选择
        const pieceStyleSelect = document.getElementById('piece-style-select');
        if (pieceStyleSelect && handlers.onPieceStyleChange) {
            pieceStyleSelect.addEventListener('change', (e) => {
                handlers.onPieceStyleChange(e.target.value);
            });
        }
        
        // 设置对话框 - 恢复默认按钮
        const btnResetSettings = document.getElementById('btn-reset-settings');
        if (btnResetSettings && handlers.onResetSettings) {
            btnResetSettings.addEventListener('click', handlers.onResetSettings);
        }
    }

    /**
     * 绑定按钮事件
     * @private
     */
    bindButton(elementName, handler) {
        if (this.elements[elementName] && handler) {
            this.elements[elementName].addEventListener('click', handler);
        }
    }

    /**
     * 获取Canvas坐标
     * @param {MouseEvent} event
     * @returns {Object} {row, col}
     */
    getCanvasPosition(event) {
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // 计算格子大小和偏移
        const boardSize = Math.min(this.canvas.width, this.canvas.height);
        const margin = boardSize * 0.08;
        const playableSize = boardSize - 2 * margin;
        this.cellSize = playableSize / 12; // 13x13棋盘有12个间隔
        
        // 转换为棋盘坐标
        const col = Math.round((x - margin) / this.cellSize);
        const row = Math.round((y - margin) / this.cellSize);
        
        return { row, col };
    }

    /**
     * 更新UI显示
     * @param {Object} gameState - 游戏状态
     * @param {Object} stats - 统计信息
     */
    updateUI(gameState, stats = {}) {
        this.updateTurnIndicator(gameState.playerTurn);
        this.updateStepCount(stats.stepCount || 0);
        this.updateTotalTime(stats.totalTime || 0);
        // 注意：使用inCheck而不是isCheck（inCheck是状态，isCheck是方法）
        this.updateCheckAlert(gameState.inCheck);
    }

    /**
     * 更新回合指示器
     */
    updateTurnIndicator(turn) {
        if (this.elements.turnIndicator) {
            const turnText = turn === 'red' ? '红方回合' : '黑方回合';
            this.elements.turnIndicator.textContent = turnText;
            this.elements.turnIndicator.className = `turn-indicator ${turn}`;
        }
    }

    /**
     * 更新步数显示
     */
    updateStepCount(count) {
        if (this.elements.stepCount) {
            this.elements.stepCount.textContent = `步数: ${count}`;
        }
    }

    /**
     * 更新总时间显示
     */
    updateTotalTime(seconds) {
        if (this.elements.totalTime) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            this.elements.totalTime.textContent = `时间: ${mins}:${secs.toString().padStart(2, '0')}`;
        }
    }

    /**
     * 更新将军提示
     */
    updateCheckAlert(isCheck) {
        if (this.elements.checkAlert) {
            if (isCheck) {
                this.elements.checkAlert.style.display = 'block';
                this.elements.checkAlert.textContent = '⚠️ 将军！';
            } else {
                this.elements.checkAlert.style.display = 'none';
            }
        }
    }

    /**
     * 更新棋谱列表
     * @param {Array} history - 移动历史
     */
    updateMoveHistory(history) {
        if (!this.elements.moveList) return;
        
        this.elements.moveList.innerHTML = '';
        
        history.forEach((move, index) => {
            const item = document.createElement('div');
            item.className = 'move-item';
            item.textContent = `${index + 1}. ${move.notation}`;
            this.elements.moveList.appendChild(item);
        });
        
        // 滚动到底部
        this.elements.moveList.scrollTop = this.elements.moveList.scrollHeight;
    }

    /**
     * 添加聊天消息
     * @param {string} player - 玩家名称
     * @param {string} message - 消息内容
     * @param {boolean} isSelf - 是否是自己发送的
     */
    addChatMessage(player, message, isSelf = true) {
        if (!this.elements.chatMessages) return;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${isSelf ? 'self' : 'other'}`;
        msgDiv.innerHTML = `
            <span class="chat-player">${player}</span>
            <span class="chat-text">${message}</span>
        `;
        
        this.elements.chatMessages.appendChild(msgDiv);
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    /**
     * 清空聊天输入框
     */
    clearChatInput() {
        if (this.elements.chatInput) {
            this.elements.chatInput.value = '';
        }
    }

    /**
     * 切换面板显示
     * @param {string} panelName - 面板名称
     * @param {boolean} show - 是否显示
     */
    togglePanel(panelName, show = null) {
        const panel = this.elements[panelName];
        if (!panel) return;
        
        if (show === null) {
            panel.classList.toggle('active');
        } else if (show) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    }

    /**
     * 切换暗黑模式
     * @param {boolean} enabled
     */
    toggleDarkMode(enabled = null) {
        if (enabled === null) {
            this.isDarkMode = !this.isDarkMode;
        } else {
            this.isDarkMode = enabled;
        }
        
        if (this.isDarkMode) {
            document.body.classList.add('dark-mode');
            if (this.elements.darkModeBtn) {
                this.elements.darkModeBtn.textContent = '☀️';
            }
        } else {
            document.body.classList.remove('dark-mode');
            if (this.elements.darkModeBtn) {
                this.elements.darkModeBtn.textContent = '🌙';
            }
        }
        
        // 保存偏好
        localStorage.setItem('darkMode', this.isDarkMode);
    }

    /**
     * 恢复暗黑模式设置
     */
    restoreDarkMode() {
        const saved = localStorage.getItem('darkMode') === 'true';
        this.toggleDarkMode(saved);
    }

    /**
     * 选中棋子高亮
     * @param {Object} pos - 位置 {row, col}
     */
    highlightSelectedPiece(pos) {
        this.selectedPiece = pos;
        // 触发重绘
        this.events.emit('ui:updated', { selectedPiece: pos });
    }

    /**
     * 清除选中高亮
     */
    clearSelection() {
        this.selectedPiece = null;
        this.events.emit('ui:updated', { selectedPiece: null });
    }

    /**
     * 显示加载状态
     * @param {string} message
     */
    showLoading(message = '加载中...') {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="spinner"></div>
            <p>${message}</p>
        `;
        document.body.appendChild(overlay);
    }

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * 获取选中的棋子
     * @returns {Object|null}
     */
    getSelectedPiece() {
        return this.selectedPiece;
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.UIController = UIController;
}
