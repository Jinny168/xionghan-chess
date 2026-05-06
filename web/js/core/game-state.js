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
        const { Ju, Ma, Xiang, Shi, Han, Pao, Bing, Wei, She, Lei, Xun } = window;
        
        // 黑方布局（已移除甲/胄、刺/伺、盾/碷）
        const blackPieces = [
            [She, 0, 0], [She, 0, 12],
            [Lei, 0, 4], [Lei, 0, 8], [Wei, 0, 6],
            [Ju, 1, 2], [Ma, 1, 3], [Xiang, 1, 4], [Shi, 1, 5],
            [Han, 1, 6], [Shi, 1, 7], [Xiang, 1, 8], [Ma, 1, 9], [Ju, 1, 10],
            [Pao, 3, 1], [Pao, 3, 11],
            [Bing, 4, 0], [Bing, 4, 2], [Bing, 4, 4], [Bing, 4, 6],
            [Bing, 4, 8], [Bing, 4, 10], [Bing, 4, 12],
            [Xun, 5, 0], [Xun, 5, 12]
        ];
        
        blackPieces.forEach(([PieceClass, row, col]) => {
            this.pieces.push(new PieceClass('black', row, col));
        });
        
        // 红方布局（已移除甲/胄、刺/伺、盾/碷）
        const redPieces = [
            [She, 12, 0], [She, 12, 12],
            [Lei, 12, 4], [Lei, 12, 8], [Wei, 12, 6],
            [Ju, 11, 2], [Ma, 11, 3], [Xiang, 11, 4], [Shi, 11, 5],
            [Han, 11, 6], [Shi, 11, 7], [Xiang, 11, 8], [Ma, 11, 9], [Ju, 11, 10],
            [Pao, 9, 1], [Pao, 9, 11],
            [Bing, 8, 0], [Bing, 8, 2], [Bing, 8, 4], [Bing, 8, 6],
            [Bing, 8, 8], [Bing, 8, 10], [Bing, 8, 12],
            [Xun, 7, 0], [Xun, 7, 12]
        ];
        
        redPieces.forEach(([PieceClass, row, col]) => {
            this.pieces.push(new PieceClass('red', row, col));
        });
    }
    
    /**
     * 获取指定位置的棋子
     */
    getPieceAt(row, col) {
        const { GameRules } = window;
        return GameRules.getPieceAt(this.pieces, row, col);
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
        const { piece, fromRow, fromCol, toRow, toCol, capturedPiece } = lastMove;
        
        // 移回原位置
        piece.moveTo(fromRow, fromCol);
        
        // 恢复被吃的棋子
        if (capturedPiece) {
            this.pieces.push(capturedPiece);
            this.capturedPieces[capturedPiece.color].pop();
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
        
        this.initializePieces();
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
