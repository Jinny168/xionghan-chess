/**
 * 游戏状态管理
 */

class GameState {
    constructor() {
        // 初始化所有状态
        this.reset();
        
        // 初始化棋子
        this.initializePieces();
        
        // 初始化后检查将军状态(开局不应该将军)
        this.checkInitialState();
    }
    /**
     * 初始化棋子布局
     */
    initializePieces() {
        // 匈汉象棋布局
        this.setupXionghanLayout();
    }
    
    /**
     * 检查初始状态(确保开局不会误判将军)
     */
    checkInitialState() {
        const { GameRules } = window;
        if (GameRules && GameRules.isCheck) {
            this.inCheck = GameRules.isCheck(this.pieces, this.playerTurn);
        }
    }

    setupXionghanLayout() {
        const { Ju, Ma, Xiang, Shi, Han, Pao, Bing, She, Lei } = window;
        
        // 黑方布局
        const blackPieces = [
            [She, 0, 0], [She, 0, 12],
            [Lei, 0, 4], [Lei, 0, 8],
            [Ju, 0, 2], [Ju, 0, 10],
            [Ma, 1, 3], [Xiang, 1, 4], [Shi, 1, 5],
            [Han, 1, 6], [Shi, 1, 7], [Xiang, 1, 8], [Ma, 1, 9],
            [Pao, 3, 1], [Pao, 3, 11],
            [Bing, 4, 0], [Bing, 4, 2], [Bing, 4, 4], [Bing, 4, 6],
            [Bing, 4, 8], [Bing, 4, 10], [Bing, 4, 12]  // 7个兵，在同一行
        ];
                
        blackPieces.forEach(([PieceClass, row, col]) => {
            this.pieces.push(new PieceClass('black', row, col));
        });
                
        // 红方布局
        const redPieces = [
            [She, 12, 0], [She, 12, 12],
            [Lei, 12, 4], [Lei, 12, 8],
            [Ju, 12, 2], [Ju, 12, 10],
            [Ma, 11, 3], [Xiang, 11, 4], [Shi, 11, 5],
            [Han, 11, 6], [Shi, 11, 7], [Xiang, 11, 8], [Ma, 11, 9],
            [Pao, 9, 1], [Pao, 9, 11],
            [Bing, 8, 0], [Bing, 8, 2], [Bing, 8, 4], [Bing, 8, 6],
            [Bing, 8, 8], [Bing, 8, 10], [Bing, 8, 12]  // 7个兵，在同一行
        ];
        
        redPieces.forEach(([PieceClass, row, col]) => {
            this.pieces.push(new PieceClass('red', row, col));
        });
        
        // 记录兵的出生点位置（用于生成新兵）
        this.bingSpawnPoints = {
            'black': [[4, 0], [4, 2], [4, 4], [4, 6], [4, 8], [4, 10], [4, 12]],
            'red': [[8, 0], [8, 2], [8, 4], [8, 6], [8, 8], [8, 10], [8, 12]]
        };
    }
    
    /**
     * 获取指定位置的棋子
     */
    getPieceAt(row, col) {
        const { GameRules } = window;
        return GameRules.getPieceAt(this.pieces, row, col);
    }
    /**
     * 切换玩家回合
     * @private
     */
    switchTurn() {
        const previousPlayer = this.playerTurn;
        this.playerTurn = this.playerTurn === 'red' ? 'black' : 'red';
        this.currentTurnStartTime = Date.now();
        return previousPlayer;
    }
    
    /**
     * 在指定的出生点生成一个兵（消耗一次走子机会）
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @param {string|null} camp - 阵营颜色（可选，不传则使用当前玩家回合；网络对战中可显式指定）
     * @returns {boolean} 是否成功生成
     */
    spawnBing(row, col, camp = null) {
        // 确定阵营：优先使用传入的camp参数，否则使用当前玩家回合
        const actualCamp = camp || this.playerTurn;
        
        // 检查是否是当前玩家的回合
        if (this.gameOver) return false;
        
        // 检查该位置是否是合法的兵出生点
        const spawnPoints = this.bingSpawnPoints[actualCamp];
        if (!spawnPoints) return false;
        
        const isValidSpawnPoint = spawnPoints.some(([r, c]) => r === row && c === col);
        if (!isValidSpawnPoint) return false;
        
        // 检查该位置是否为空
        const existingPiece = this.getPieceAt(row, col);
        if (existingPiece) return false;
        
        // 创建新兵
        const { Bing } = window;
        const newBing = new Bing(actualCamp, row, col);
        this.pieces.push(newBing);
        
        // 记录移动历史（特殊移动类型：生成兵）
        this.moveHistory.push({
            piece: newBing,
            fromRow: null,
            fromCol: null,
            toRow: row,
            toCol: col,
            capturedPiece: null,
            wasInCheck: this.inCheck,
            isSpawn: true
        });
        this.movesCount++;
        
        // 切换回合并检查状态
        const previousPlayer = this.switchTurn();
        this.updateCheckState(null, previousPlayer);
        this.checkEndGame(previousPlayer);
        
        return true;
    }
    
    /**
     * 检查指定位置是否是兵的出生点
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @param {string|null} color - 颜色（可选，不传则检查所有出生点）
     * @returns {boolean}
     */
    isBingSpawnPoint(row, col, color = null) {
        if (color) {
            const spawnPoints = this.bingSpawnPoints[color];
            if (!spawnPoints) return false;
            return spawnPoints.some(([r, c]) => r === row && c === col);
        } else {
            // 检查所有出生点
            return [...this.bingSpawnPoints['black'], ...this.bingSpawnPoints['red']]
                .some(([r, c]) => r === row && c === col);
        }
    }
    
    /**
     * 移动棋子
     */
    movePiece(fromRow, fromCol, toRow, toCol) {
        // 减少调试日志输出
        // console.log('=== GameState.movePiece 被调用 ===');
        // console.log('起始:', [fromRow, fromCol], '目标:', [toRow, toCol]);
        
        const { GameRules } = window;
        const piece = this.getPieceAt(fromRow, fromCol);
        
        // console.log('选中的棋子:', piece ? piece.name : 'null', piece ? piece.color : 'null');
        
        if (!piece || piece.color !== this.playerTurn) {
            // console.log('❌ 移动失败：没有棋子或不是当前回合');
            return false;
        }
        
        // console.log('调用 GameRules.isValidMove...');
        if (!GameRules.isValidMove(this.pieces, piece, fromRow, fromCol, toRow, toCol)) {
            // console.log('❌ 移动失败：不符合规则');
            return false;
        }
        
        // console.log('✅ 移动符合规则，继续检查将军...');
        
        // 检查是否会导致自己被将军（禁止送将）
        if (this.wouldBeInCheckAfterMove(piece, toRow, toCol)) {
            return false;
        }
        
        // 记录移动历史
        const capturedPiece = this.getPieceAt(toRow, toCol);
        const moveRecord = {
            piece: piece,
            fromRow, fromCol, toRow, toCol,
            capturedPiece: capturedPiece,
            wasInCheck: this.inCheck  // 记录移动前是否被将军
        };
        
        // 执行移动
        if (capturedPiece) {
            this.pieces = this.pieces.filter(p => p !== capturedPiece);
            this.capturedPieces[capturedPiece.color].push(capturedPiece);
            
            // 检查是否吃掉对方将/帅
            if (capturedPiece instanceof window.Han) {
                this.gameOver = true;
                this.winner = piece.color;
            }
        }
        
        piece.moveTo(toRow, toCol);
        this.moveHistory.push(moveRecord);
        this.movesCount++;
        
        // 清除缓存（棋盘状态已改变）
        this._movesCache = {};
        
        // 切换回合并检查状态
        if (!this.gameOver) {
            const previousPlayer = this.switchTurn();
            this.updateCheckState(piece, previousPlayer);
            this.checkEndGame(previousPlayer);
        }
        
        return true;
    }
    
    /**
     * 检查游戏是否结束（将死或困毙）
     * @param {string} previousPlayer - 上一个移动的玩家
     * @private
     */
    checkEndGame(previousPlayer) {
        if (this.isCheckmate()) {
            this.gameOver = true;
            this.winner = previousPlayer;
        }
    }
    
    /**
     * 模拟移动并检查是否被将军
     * @param {Object} piece - 棋子
     * @param {number} toRow - 目标行
     * @param {number} toCol - 目标列
     * @returns {boolean} 是否会被将军
     * @private
     */
    simulateMoveAndCheck(piece, toRow, toCol) {
        const { GameRules } = window;
        const originalRow = piece.row;
        const originalCol = piece.col;
        const capturedPiece = this.getPieceAt(toRow, toCol);
        
        // 临时执行移动
        piece.moveTo(toRow, toCol);
        if (capturedPiece) {
            this.pieces = this.pieces.filter(p => p !== capturedPiece);
        }
        
        // 检查是否被将军
        const inCheck = GameRules.isCheck(this.pieces, piece.color);
        
        // 恢复状态
        piece.moveTo(originalRow, originalCol);
        if (capturedPiece) {
            this.pieces.push(capturedPiece);
        }
        
        return inCheck;
    }
    
    /**
     * 检查移动后是否会被将军
     */
    wouldBeInCheckAfterMove(piece, toRow, toCol) {
        return this.simulateMoveAndCheck(piece, toRow, toCol);
    }
    
    /**
     * 撤销移动
     */
    undoMove() {
        if (this.moveHistory.length === 0) {
            return false;
        }
        
        const lastMove = this.moveHistory.pop();
        const { piece, fromRow, fromCol, capturedPiece, isSpawn } = lastMove;
        
        // 如果是生成兵的操作，需要移除生成的兵
        if (isSpawn) {
            // 从棋子列表中移除该兵
            this.pieces = this.pieces.filter(p => p !== piece);
        } else {
            // 普通移动：恢复位置并恢复被吃的棋子
            piece.moveTo(fromRow, fromCol);
            
            if (capturedPiece) {
                this.pieces.push(capturedPiece);
                this.capturedPieces[capturedPiece.color].pop();
            }
        }
        
        // 切换玩家
        this.playerTurn = this.playerTurn === 'red' ? 'black' : 'red';
        this.gameOver = false;
        this.winner = null;
        this.movesCount--;
        
        // 清除缓存（棋盘状态已改变）
        this._movesCache = {};
        
        return true;
    }
    
    /**
     * 计算可能移动（过滤掉会导致送将的移动）
     * 带缓存优化：如果棋盘状态未改变，直接返回缓存结果
     */
    calculatePossibleMoves(row, col) {
        const { GameRules } = window;
        const piece = this.getPieceAt(row, col);
        
        if (!piece) {
            return { moves: [], capturable: [] };
        }
        
        // 生成缓存键：基于棋子位置和棋盘状态哈希
        const cacheKey = `${piece.name}_${row}_${col}_${this.movesCount}`;
        
        // 检查缓存
        if (this._movesCache && this._movesCache[cacheKey]) {
            return this._movesCache[cacheKey];
        }
        
        // 获取所有符合基本规则的移动
        const { moves, capturable } = GameRules.calculatePossibleMoves(this.pieces, piece);
        
        // 过滤掉会导致自己被将军的移动（禁止送将）
        const validMoves = moves.filter(move => 
            !this.wouldBeInCheckAfterMove(piece, move.row, move.col)
        );
        const validCapturable = capturable.filter(move => 
            !this.wouldBeInCheckAfterMove(piece, move.row, move.col)
        );
        
        const result = { moves: validMoves, capturable: validCapturable };
        
        // 缓存结果（限制缓存大小）
        if (!this._movesCache) {
            this._movesCache = {};
        }
        this._movesCache[cacheKey] = result;
        
        // 清理旧缓存（保留最近100个）
        const keys = Object.keys(this._movesCache);
        if (keys.length > 100) {
            delete this._movesCache[keys[0]];
        }
        
        return result;
    }
    
    /**
     * 检查是否将军
     */
    isCheck() {
        const { GameRules } = window;
        return GameRules.isCheck(this.pieces, this.playerTurn);
    }
    
    /**
     * 检查是否将死或困毙
     * 将死：被将军 + 无合法移动 → 判负
     * 困毙：未被将军 + 无合法移动 → 判负
     */
    isCheckmate() {
        // 检查所有己方棋子是否有任何合法移动
        const currentPieces = this.pieces.filter(p => p.color === this.playerTurn);
        let hasValidMove = false;
        
        for (const piece of currentPieces) {
            // 使用 this.calculatePossibleMoves 过滤掉送将的移动
            const { moves, capturable } = this.calculatePossibleMoves(piece.row, piece.col);
            
            // 如果有任何合法移动，说明不是将死/困毙
            if (moves.length > 0 || capturable.length > 0) {
                hasValidMove = true;
                
                // 如果被将军，需要检查是否有移动能解将
                if (this.inCheck) {
                    for (const move of [...moves, ...capturable]) {
                        // 使用模拟移动检查是否能解将
                        if (!this.simulateMoveAndCheck(piece, move.row, move.col)) {
                            return false;
                        }
                    }
                } else {
                    // 未被将军，但有合法移动，不是困毙
                    return false;
                }
            }
        }
        
        // 如果没有任何合法移动
        if (!hasValidMove) {
            if (this.inCheck) {
                // 将死：被将军 + 无合法移动
                console.log('🎯 将死！' + (this.playerTurn === 'red' ? '红方' : '黑方') + '被将死');
            } else {
                // 困毙：未被将军 + 无合法移动
                console.log('🎯 困毙！' + (this.playerTurn === 'red' ? '红方' : '黑方') + '无棋可走');
            }
            return true;
        }
        
        // 被将军但所有移动都无法解将
        if (this.inCheck) {
            console.log('🎯 将死！' + (this.playerTurn === 'red' ? '红方' : '黑方') + '无法解将');
            return true;
        }
        
        // 未被将军且有合法移动
        return false;
    }
    
    /**
     * 获取用时
     */
    getTimes() {
        const currentTime = Date.now();
        const elapsed = Math.floor((currentTime - this.currentTurnStartTime) / 1000);
        
        let redTime = this.redTime;
        let blackTime = this.blackTime;
        
        if (this.playerTurn === 'red') {
            redTime += elapsed;
        } else {
            blackTime += elapsed;
        }
        
        return { redTime, blackTime };
    }
    

    
    /**
     * 更新将军状态（提取公共逻辑）
     * @private
     */
    updateCheckState(piece, previousPlayer) {
        const { GameRules } = window;
        this.inCheck = GameRules.isCheck(this.pieces, this.playerTurn);
        
        if (this.inCheck) {
            this.consecutiveChecks++;
            this.lastCheckBy = previousPlayer;
            
            // 禁止连将：如果连续将军超过3次，判违规
            if (this.consecutiveChecks > 3) {
                console.warn('⚠️ 连续将军超过3次，判违规');
                // TODO: 实现判负逻辑
            }
        } else {
            this.consecutiveChecks = 0;
            this.lastCheckBy = null;
        }
    }
    
    /**
     * 重置游戏
     */
    reset() {
        // 重置基本状态
        this.pieces = [];
        this.playerTurn = 'red';
        this.gameOver = false;
        this.winner = null;
        this.moveHistory = [];
        this.capturedPieces = { red: [], black: [] };
        this.redTime = 0;
        this.blackTime = 0;
        this.currentTurnStartTime = Date.now();
        this.movesCount = 0;
        
        // 重置将军状态
        this.inCheck = false;
        this.checkWarningShown = false;
        this.consecutiveChecks = 0;
        this.lastCheckBy = null;
        
        // 清除缓存
        this._movesCache = {};
    }
    

}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameState = GameState;
}
