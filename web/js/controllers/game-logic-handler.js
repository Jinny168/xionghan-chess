/**
 * 游戏逻辑处理器 - 处理所有游戏核心逻辑
 * 职责：棋子移动、规则验证、胜负判断、兵复活等
 */

class GameLogicHandler {
    constructor(gameState, ruleConfig, eventDispatcher) {
        this.gameState = gameState;
        this.ruleConfig = ruleConfig;
        this.events = eventDispatcher;
        
        this.moveHistory = [];
        this.lastMoveNotation = '';
    }

    /**
     * 验证并执行移动
     * @param {Object} fromPos - 起始位置 {row, col}
     * @param {Object} toPos - 目标位置 {row, col}
     * @returns {Object} {success, message, moveData}
     */
    executeMove(fromPos, toPos) {
        const piece = this.gameState.getPieceAt(fromPos.row, fromPos.col);
        
        if (!piece) {
            return { success: false, message: '该位置没有棋子' };
        }

        // 验证是否是当前回合方的棋子
        if (piece.camp !== this.gameState.playerTurn) {
            return { success: false, message: '不是你的回合' };
        }

        // 验证移动合法性
        const isValid = this.gameState.isValidMove(piece, toPos.row, toPos.col);
        if (!isValid) {
            return { success: false, message: '非法移动' };
        }

        // 记录移动前的状态（用于悔棋）
        const moveSnapshot = this.createMoveSnapshot(piece, fromPos, toPos);

        // 执行移动
        const capturedPiece = this.gameState.movePiece(fromPos.row, fromPos.col, toPos.row, toPos.col);
        
        // 生成棋谱记号
        const notation = this.generateMoveNotation(piece, fromPos, toPos, capturedPiece);
        this.lastMoveNotation = notation;

        // 记录到历史
        const moveData = {
            from: fromPos,
            to: toPos,
            piece: piece.name,
            camp: piece.camp,
            captured: capturedPiece ? capturedPiece.name : null,
            notation: notation,
            timestamp: Date.now()
        };
        
        this.moveHistory.push(moveData);

        // 检查是否有吃子
        if (capturedPiece) {
            this.events.emit('piece:captured', {
                capturedPiece: capturedPiece.name,
                captorCamp: piece.camp
            });
        }

        // 触发移动事件
        this.events.emit('piece:moved', moveData);

        // 检查将军
        const isCheck = this.gameState.isCheck(this.gameState.playerTurn);
        if (isCheck) {
            this.events.emit('check:detected', { camp: this.gameState.playerTurn });
        }

        // 检查绝杀
        const isCheckmate = this.gameState.isCheckmate(this.gameState.playerTurn);
        if (isCheckmate) {
            this.events.emit('checkmate:detected', { 
                winner: piece.camp,
                loser: this.gameState.playerTurn
            });
            
            return {
                success: true,
                message: '绝杀！',
                moveData: { ...moveData, gameOver: true, winner: piece.camp }
            };
        }

        // 切换回合
        this.switchTurn();

        return {
            success: true,
            message: '移动成功',
            moveData: { ...moveData, isCheck }
        };
    }

    /**
     * 尝试复活兵
     * @param {number} row - 行
     * @param {number} col - 列
     * @returns {Object} {success, message, piece}
     */
    trySpawnBing(row, col) {
        // 获取规则配置
        const config = this.ruleConfig.getConfig();
        
        if (!config.pawnResurrection) {
            return { success: false, message: '兵复活功能已禁用' };
        }

        // 检查是否满足复活条件（三子相连）
        const canSpawn = this.checkBingSpawnCondition(row, col);
        if (!canSpawn) {
            return { success: false, message: '不满足复活条件' };
        }

        // 执行复活（传入当前玩家回合作为阵营参数，网络对战中可显式指定）
        const success = this.gameState.spawnBing(row, col, this.gameState.playerTurn);
        
        if (success) {
            const spawnedPiece = this.gameState.getPieceAt(row, col);
            
            this.events.emit('piece:spawned', {
                piece: spawnedPiece.name,
                position: { row, col },
                camp: this.gameState.playerTurn === 'red' ? 'black' : 'red' // 注意：已切换回合
            });
            
            return { success: true, message: '兵复活成功', piece: spawnedPiece };
        }

        return { success: false, message: '复活失败' };
    }

    /**
     * 检查兵复活条件（三子相连）
     * @private
     */
    checkBingSpawnCondition(row, col) {
        // 检查该位置周围是否有三个己方棋子相连
        const camp = this.gameState.playerTurn;
        const directions = [
            [-1, 0], [1, 0], [0, -1], [0, 1], // 上下左右
            [-1, -1], [-1, 1], [1, -1], [1, 1] // 对角线
        ];

        let connectedCount = 0;
        
        for (const [dr, dc] of directions) {
            const newRow = row + dr;
            const newCol = col + dc;
            
            if (this.gameState.isValidPosition(newRow, newCol)) {
                const piece = this.gameState.getPieceAt(newRow, newCol);
                if (piece && piece.camp === camp) {
                    connectedCount++;
                }
            }
        }

        return connectedCount >= 3;
    }

    /**
     * 悔棋
     * @returns {Object} {success, message}
     */
    undo() {
        if (this.moveHistory.length === 0) {
            return { success: false, message: '没有可悔的棋' };
        }

        // 撤销最后一步
        const lastMove = this.moveHistory.pop();
        this.gameState.undoLastMove();

        // 如果是在线模式，需要撤销两步（自己和对手）
        if (lastMove.camp !== this.gameState.playerTurn) {
            const secondLastMove = this.moveHistory.pop();
            if (secondLastMove) {
                this.gameState.undoLastMove();
            }
        }

        this.events.emit('history:updated', {
            history: this.moveHistory,
            action: 'undo'
        });

        return { success: true, message: '悔棋成功' };
    }

    /**
     * 重新开始
     */
    restart() {
        this.gameState.reset();
        this.moveHistory = [];
        this.lastMoveNotation = '';
        
        this.events.emit('game:reset');
        this.events.emit('history:updated', {
            history: [],
            action: 'restart'
        });
    }

    /**
     * 切换回合
     * @private
     */
    switchTurn() {
        const oldTurn = this.gameState.playerTurn;
        this.gameState.playerTurn = oldTurn === 'red' ? 'black' : 'red';
        
        this.events.emit('turn:changed', {
            from: oldTurn,
            to: this.gameState.playerTurn
        });
    }

    /**
     * 生成棋谱记号
     * @private
     */
    generateMoveNotation(piece, fromPos, toPos, capturedPiece) {
        const pieceNames = {
            '車': '车', '马': '马', '相': '相', '士': '士',
            '将': '将', '炮': '炮', '兵': '兵',
            '尉': '尉', '射': '射', '檑': '檑',
            '甲': '甲', '刺': '刺', '盾': '盾', '巡': '巡'
        };

        const pieceName = pieceNames[piece.name] || piece.name;
        const fromCol = String.fromCharCode(65 + fromPos.col); // A, B, C...
        const toCol = String.fromCharCode(65 + toPos.col);
        
        let notation = `${pieceName}${fromCol}${13 - fromPos.row}`;
        
        if (capturedPiece) {
            notation += '×';
        } else {
            notation += '-';
        }
        
        notation += `${toCol}${13 - toPos.row}`;
        
        return notation;
    }

    /**
     * 创建移动快照（用于悔棋）
     * @private
     */
    createMoveSnapshot(piece, fromPos, toPos) {
        return {
            piece: { ...piece },
            from: { ...fromPos },
            to: { ...toPos },
            turn: this.gameState.playerTurn,
            boardState: this.gameState.cloneBoard()
        };
    }

    /**
     * 获取移动历史
     * @returns {Array}
     */
    getMoveHistory() {
        return [...this.moveHistory];
    }

    /**
     * 清空移动历史
     */
    clearHistory() {
        this.moveHistory = [];
        this.lastMoveNotation = '';
    }

    /**
     * 获取最后一步记号
     * @returns {string}
     */
    getLastMoveNotation() {
        return this.lastMoveNotation;
    }

    /**
     * 检查游戏是否结束
     * @returns {Object} {gameOver, winner, reason}
     */
    checkGameEnd() {
        if (this.gameState.gameOver) {
            return {
                gameOver: true,
                winner: this.gameState.winner,
                reason: this.gameState.gameReason
            };
        }

        return { gameOver: false };
    }

    /**
     * 认输
     * @param {string} camp - 认输方 'red' 或 'black'
     * @returns {Object}
     */
    resign(camp) {
        const winner = camp === 'red' ? 'black' : 'red';
        
        this.gameState.endGame(winner, 'resign');
        
        this.events.emit('game:end', {
            winner,
            reason: 'resign',
            loser: camp
        });

        return {
            success: true,
            winner,
            reason: 'resign'
        };
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameLogicHandler = GameLogicHandler;
}
