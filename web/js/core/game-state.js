/**
 * 游戏状态管理
 */

class GameState {
    constructor() {
        this.pieces = [];
        this.playerTurn = 'red';
        this.gameOver = false;
        this.winner = null;
        this.moveHistory = [];
        this.capturedPieces = { red: [], black: [] };
        this.startTime = Date.now();
        this.redTime = 0;
        this.blackTime = 0;
        this.currentTurnStartTime = Date.now();
        this.movesCount = 0;
        
        // 将军相关
        this.inCheck = false;       // 当前是否被将军
        this.checkWarningShown = false; // 将军提示是否已显示
        this.consecutiveChecks = 0; // 连续将军次数（用于禁止连将）
        this.lastCheckBy = null;    // 最后一次将军的玩家
        
        // 棋子价值配置（平衡型方案）
        this.pieceValues = {
            // 将帅
            '漢': 10000, '汗': 10000,
            
            // 强子
            '俥': 900, '車': 900,
            '炮': 450, '砲': 450,
            
            // 中等棋子
            '檑': 400, '礌': 400,
            '傌': 400, '馬': 400,
            '射': 330, '䠶': 330,
            
            // 弱子
            '相': 260, '象': 260,
            '仕': 200, '士': 200,
            
            // 兵卒（基础值，实际应动态调整）
            '兵': 100, '卒': 100
        };
        
        // 初始化棋子
        this.initializePieces();
    }
    
    /**
     * 初始化棋子布局
     */
    initializePieces() {
        // 匈汉象棋布局
        this.setupXionghanLayout();
    }
    
    setupTraditionalLayout() {
        const { Ju, Ma, Xiang, Shi, Han, Pao, Bing } = window;
        
        // 黑方
        this.pieces.push(new Ju('black', 0, 0));
        this.pieces.push(new Ma('black', 0, 1));
        this.pieces.push(new Xiang('black', 0, 2));
        this.pieces.push(new Shi('black', 0, 3));
        this.pieces.push(new Han('black', 0, 4));
        this.pieces.push(new Shi('black', 0, 5));
        this.pieces.push(new Xiang('black', 0, 6));
        this.pieces.push(new Ma('black', 0, 7));
        this.pieces.push(new Ju('black', 0, 8));
        this.pieces.push(new Pao('black', 2, 1));
        this.pieces.push(new Pao('black', 2, 7));
        this.pieces.push(new Bing('black', 3, 0));
        this.pieces.push(new Bing('black', 3, 2));
        this.pieces.push(new Bing('black', 3, 4));
        this.pieces.push(new Bing('black', 3, 6));
        this.pieces.push(new Bing('black', 3, 8));
        
        // 红方
        this.pieces.push(new Ju('red', 9, 0));
        this.pieces.push(new Ma('red', 9, 1));
        this.pieces.push(new Xiang('red', 9, 2));
        this.pieces.push(new Shi('red', 9, 3));
        this.pieces.push(new Han('red', 9, 4));
        this.pieces.push(new Shi('red', 9, 5));
        this.pieces.push(new Xiang('red', 9, 6));
        this.pieces.push(new Ma('red', 9, 7));
        this.pieces.push(new Ju('red', 9, 8));
        this.pieces.push(new Pao('red', 7, 1));
        this.pieces.push(new Pao('red', 7, 7));
        this.pieces.push(new Bing('red', 6, 0));
        this.pieces.push(new Bing('red', 6, 2));
        this.pieces.push(new Bing('red', 6, 4));
        this.pieces.push(new Bing('red', 6, 6));
        this.pieces.push(new Bing('red', 6, 8));
    }
    
    setupXionghanLayout() {
        const { Ju, Ma, Xiang, Shi, Han, Pao, Bing, She, Lei } = window;
        
        // 黑方布局（已移除甲/胄、刺/伺、盾/碷、尉/衛、巡/廵）
        // 调整：车移到第0行，与礌、射同行；移除边缘的兵（col=0和col=12）
        const blackPieces = [
            [She, 0, 0], [She, 0, 12],
            [Lei, 0, 4], [Lei, 0, 8],
            [Ju, 0, 2], [Ju, 0, 10],  // 车移到第0行，与礌、射同行
            [Ma, 1, 3], [Xiang, 1, 4], [Shi, 1, 5],
            [Han, 1, 6], [Shi, 1, 7], [Xiang, 1, 8], [Ma, 1, 9],
            [Pao, 3, 1], [Pao, 3, 11],
            [Bing, 4, 2], [Bing, 4, 4], [Bing, 4, 6],
            [Bing, 4, 8], [Bing, 4, 10]  // 移除边缘的兵（col=0和col=12）
        ];
        
        blackPieces.forEach(([PieceClass, row, col]) => {
            this.pieces.push(new PieceClass('black', row, col));
        });
        
        // 红方布局（已移除甲/胄、刺/伺、盾/碷、尉/衛、巡/廵）
        // 调整：车移到第12行，与礌、射同行；移除边缘的兵（col=0和col=12）
        const redPieces = [
            [She, 12, 0], [She, 12, 12],
            [Lei, 12, 4], [Lei, 12, 8],
            [Ju, 12, 2], [Ju, 12, 10],  // 车移到第12行，与礌、射同行
            [Ma, 11, 3], [Xiang, 11, 4], [Shi, 11, 5],
            [Han, 11, 6], [Shi, 11, 7], [Xiang, 11, 8], [Ma, 11, 9],
            [Pao, 9, 1], [Pao, 9, 11],
            [Bing, 8, 2], [Bing, 8, 4], [Bing, 8, 6],
            [Bing, 8, 8], [Bing, 8, 10]  // 移除边缘的兵（col=0和col=12）
        ];
        
        redPieces.forEach(([PieceClass, row, col]) => {
            this.pieces.push(new PieceClass('red', row, col));
        });
        
        // 记录兵的出生点位置（用于生成新兵）
        this.bingSpawnPoints = {
            'black': [[4, 2], [4, 4], [4, 6], [4, 8], [4, 10]],
            'red': [[8, 2], [8, 4], [8, 6], [8, 8], [8, 10]]
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
     * 获取棋子的基础价值
     * @param {Object} piece - 棋子对象
     * @returns {number} 棋子价值
     */
    getPieceValue(piece) {
        if (!piece) return 0;
        return this.pieceValues[piece.name] || 0;
    }
    
    /**
     * 获取棋子的动态价值（考虑位置、状态等因素）
     * @param {Object} piece - 棋子对象
     * @returns {number} 动态价值
     */
    getDynamicPieceValue(piece) {
        if (!piece) return 0;
        
        let value = this.getPieceValue(piece);
        
        // 兵/卒的动态价值
        if (piece instanceof window.Bing) {
            value = this.getPawnDynamicValue(piece);
        }
        // 相/象的动态价值
        else if (piece instanceof window.Xiang) {
            value = this.getXiangDynamicValue(piece);
        }
        // 仕/士的动态价值
        else if (piece instanceof window.Shi) {
            value = this.getShiDynamicValue(piece);
        }
        
        return value;
    }
    
    /**
     * 计算兵/卒的动态价值
     */
    getPawnDynamicValue(pawn) {
        let baseValue = 100;
        
        // 过河加成
        const hasCrossedRiver = (pawn.color === 'red' && pawn.row <= 5) ||
                                (pawn.color === 'black' && pawn.row >= 7);
        if (hasCrossedRiver) {
            baseValue += 20;
        }
        
        // 接近九宫加成
        let distanceToPalace;
        if (pawn.color === 'red') {
            distanceToPalace = Math.max(0, pawn.row - 3); // 黑方九宫在1-3行
        } else {
            distanceToPalace = Math.max(0, 9 - pawn.row); // 红方九宫在9-11行
        }
        
        if (distanceToPalace < 4) {
            baseValue += (4 - distanceToPalace) * 10;
        }
        
        return baseValue;
    }
    
    /**
     * 计算相/象的动态价值
     */
    getXiangDynamicValue(xiang) {
        let baseValue = 260;
        
        // 越河后获得横竖吃子能力
        const hasCrossedGreatWall = (xiang.color === 'red' && xiang.row <= 5) ||
                                    (xiang.color === 'black' && xiang.row >= 7);
        if (hasCrossedGreatWall) {
            baseValue += 40; // 提升到300
        }
        
        return baseValue;
    }
    
    /**
     * 计算仕/士的动态价值
     */
    getShiDynamicValue(shi) {
        let baseValue = 200;
        
        // 检查是否在九宫内
        const isInPalace = (shi.color === 'red' && shi.row >= 9 && shi.row <= 11 && shi.col >= 5 && shi.col <= 7) ||
                          (shi.color === 'black' && shi.row >= 1 && shi.row <= 3 && shi.col >= 5 && shi.col <= 7);
        
        // 出九宫后获得直走能力
        if (!isInPalace) {
            baseValue += 50; // 提升到250
        }
        
        return baseValue;
    }
    
    /**
     * 在指定的出生点生成一个兵（消耗一次走子机会）
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @returns {boolean} 是否成功生成
     */
    spawnBing(row, col) {
        // 检查是否是当前玩家的回合
        if (this.gameOver) return false;
        
        // 检查该位置是否是合法的兵出生点
        const spawnPoints = this.bingSpawnPoints[this.playerTurn];
        if (!spawnPoints) return false;
        
        const isValidSpawnPoint = spawnPoints.some(([r, c]) => r === row && c === col);
        if (!isValidSpawnPoint) return false;
        
        // 检查该位置是否为空
        const existingPiece = this.getPieceAt(row, col);
        if (existingPiece) return false;
        
        // 创建新兵
        const { Bing } = window;
        const newBing = new Bing(this.playerTurn, row, col);
        this.pieces.push(newBing);
        
        // 记录移动历史（特殊移动类型：生成兵）
        const moveRecord = {
            piece: newBing,
            fromRow: null,  // 特殊标记：生成操作
            fromCol: null,
            toRow: row,
            toCol: col,
            capturedPiece: null,
            wasInCheck: this.inCheck,
            isSpawn: true  // 标记为生成操作
        };
        this.moveHistory.push(moveRecord);
        this.movesCount++;
        
        // 切换玩家
        const previousPlayer = this.playerTurn;
        this.playerTurn = this.playerTurn === 'red' ? 'black' : 'red';
        this.currentTurnStartTime = Date.now();
        
        // 检查对方是否被将军
        const { GameRules } = window;
        this.inCheck = GameRules.isCheck(this.pieces, this.playerTurn);
        
        // 将军逻辑处理
        if (this.inCheck) {
            this.consecutiveChecks++;
            this.lastCheckBy = previousPlayer;
            
            // 禁止连将：如果连续将军超过3次，判违规
            if (this.consecutiveChecks > 3) {
                console.warn('⚠️ 连续将军超过3次，判违规');
            }
        } else {
            this.consecutiveChecks = 0;
            this.lastCheckBy = null;
        }
        
        // 检查是否将死或困毙
        if (this.isCheckmate()) {
            this.gameOver = true;
            this.winner = previousPlayer;
        }
        
        return true;
    }
    
    /**
     * 检查指定位置是否是兵的出生点
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @param {string} color - 颜色（可选，不传则检查所有出生点）
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
        const { GameRules } = window;
        const piece = this.getPieceAt(fromRow, fromCol);
        
        if (!piece || piece.color !== this.playerTurn) {
            return false;
        }
        
        if (!GameRules.isValidMove(this.pieces, piece, fromRow, fromCol, toRow, toCol)) {
            return false;
        }
        
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
        
        // 切换玩家
        if (!this.gameOver) {
            const previousPlayer = this.playerTurn;
            this.playerTurn = this.playerTurn === 'red' ? 'black' : 'red';
            this.currentTurnStartTime = Date.now();
            
            // 检查对方是否被将军
            this.inCheck = GameRules.isCheck(this.pieces, this.playerTurn);
            
            // 将军逻辑处理
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
            
            // 检查是否将死或困毙
            if (this.isCheckmate()) {
                this.gameOver = true;
                this.winner = previousPlayer;
            }
        }
        
        return true;
    }
    
    /**
     * 检查移动后是否会被将军
     */
    wouldBeInCheckAfterMove(piece, toRow, toCol) {
        const { GameRules } = window;
        
        // 模拟移动
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
     * 撤销移动
     */
    undoMove() {
        if (this.moveHistory.length === 0) {
            return false;
        }
        
        const lastMove = this.moveHistory.pop();
        const { piece, fromRow, fromCol, toRow, toCol, capturedPiece, isSpawn } = lastMove;
        
        // 如果是生成兵的操作，需要移除生成的兵
        if (isSpawn) {
            // 从棋子列表中移除该兵
            this.pieces = this.pieces.filter(p => p !== piece);
            // 不需要恢复被吃的棋子（生成时不会有吃子）
        } else {
            // 普通移动：移回原位置
            piece.moveTo(fromRow, fromCol);
            
            // 恢复被吃的棋子
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
        
        return true;
    }
    
    /**
     * 计算可能移动（过滤掉会导致送将的移动）
     */
    calculatePossibleMoves(row, col) {
        const { GameRules } = window;
        const piece = this.getPieceAt(row, col);
        
        if (!piece) {
            return { moves: [], capturable: [] };
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
        
        return { moves: validMoves, capturable: validCapturable };
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
        const { GameRules } = window;
        
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
                        // 临时执行移动
                        const originalRow = piece.row;
                        const originalCol = piece.col;
                        const targetPiece = this.getPieceAt(move.row, move.col);
                        
                        piece.moveTo(move.row, move.col);
                        if (targetPiece) {
                            this.pieces = this.pieces.filter(p => p !== targetPiece);
                        }
                        
                        // 检查是否仍被将军
                        const stillInCheck = GameRules.isCheck(this.pieces, this.playerTurn);
                        
                        // 恢复状态
                        piece.moveTo(originalRow, originalCol);
                        if (targetPiece) {
                            this.pieces.push(targetPiece);
                        }
                        
                        // 如果有移动能解将，不是将死
                        if (!stillInCheck) {
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
     * 序列化状态(用于网络传输)
     */
    serialize() {
        return {
            pieces: this.pieces.map(p => ({
                name: p.name,
                color: p.color,
                row: p.row,
                col: p.col
            })),
            playerTurn: this.playerTurn,
            gameOver: this.gameOver,
            winner: this.winner,
            movesCount: this.movesCount
        };
    }
    
    /**
     * 从序列化数据恢复状态
     */
    deserialize(data) {
        const { PieceFactory } = window;
        
        this.pieces = data.pieces.map(p => 
            PieceFactory.createPieceByName(p.name, p.color, p.row, p.col)
        );
        this.playerTurn = data.playerTurn;
        this.gameOver = data.gameOver;
        this.winner = data.winner;
        this.movesCount = data.movesCount;
    }
    
    /**
     * 重置游戏
     */
    reset() {
        this.pieces = [];
        this.playerTurn = 'red';
        this.gameOver = false;
        this.winner = null;
        this.moveHistory = [];
        this.capturedPieces = { red: [], black: [] };
        this.startTime = Date.now();
        this.redTime = 0;
        this.blackTime = 0;
        this.currentTurnStartTime = Date.now();
        this.movesCount = 0;
        
        // 重置棋子价值配置
        this.pieceValues = {
            '漢': 10000, '汗': 10000,
            '俥': 900, '車': 900,
            '炮': 450, '砲': 450,
            '檑': 400, '礌': 400,
            '傌': 400, '馬': 400,
            '射': 330, '䠶': 330,
            '相': 260, '象': 260,
            '仕': 200, '士': 200,
            '兵': 100, '卒': 100
        };
        
        this.initializePieces();
        
        // 重新设置兵的出生点
        this.bingSpawnPoints = {
            'black': [[4, 2], [4, 4], [4, 6], [4, 8], [4, 10]],
            'red': [[8, 2], [8, 4], [8, 6], [8, 8], [8, 10]]
        };
    }
    
    /**
     * 评估局面分数（正分对红方有利，负分对黑方有利）
     * @param {string} perspective - 评估视角 ('red' 或 'black')
     * @returns {number} 局面分数
     */
    evaluate(perspective = 'red') {
        let score = 0;
        
        for (const piece of this.pieces) {
            // 使用动态价值评估
            const pieceValue = this.getDynamicPieceValue(piece);
            
            if (piece.color === perspective) {
                score += pieceValue;
            } else {
                score -= pieceValue;
            }
        }
        
        return score;
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameState;
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameState = GameState;
}
