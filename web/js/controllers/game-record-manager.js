/**
 * 游戏记录管理器
 * 负责保存和加载对局记录
 */

class GameRecordManager {
    constructor() {
        this.storageKey = 'xionghan_chess_game_records';
        this.maxRecords = 50; // 最多保存50条记录
    }
    
    /**
     * 保存对局记录
     */
    saveGameRecord(gameState, gameMode = 'local') {
        try {
            const record = {
                id: Date.now().toString(),
                timestamp: new Date().toISOString(),
                gameMode: gameMode,
                winner: gameState.winner,
                movesCount: gameState.movesCount,
                duration: this.calculateDuration(gameState),
                moveHistory: gameState.moveHistory.map(move => ({
                    pieceName: move.piece.name,
                    pieceColor: move.piece.color,
                    fromRow: move.fromRow,
                    fromCol: move.fromCol,
                    toRow: move.toRow,
                    toCol: move.toCol,
                    capturedPiece: move.capturedPiece ? move.capturedPiece.name : null,
                    wasInCheck: move.wasInCheck || false
                })),
                finalState: this.serializeGameState(gameState)
            };
            
            const records = this.loadAllRecords();
            records.unshift(record); // 新记录添加到开头
            
            // 限制记录数量
            if (records.length > this.maxRecords) {
                records.length = this.maxRecords;
            }
            
            localStorage.setItem(this.storageKey, JSON.stringify(records));
            return record.id;
        } catch (error) {
            console.error('保存对局记录失败:', error);
            return null;
        }
    }
    
    /**
     * 加载所有对局记录
     */
    loadAllRecords() {
        try {
            const data = localStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : [];
        } catch (error) {
            console.error('加载对局记录失败:', error);
            return [];
        }
    }
    
    /**
     * 加载指定记录
     */
    loadRecord(recordId) {
        const records = this.loadAllRecords();
        return records.find(r => r.id === recordId);
    }
    
    /**
     * 删除对局记录
     */
    deleteRecord(recordId) {
        try {
            let records = this.loadAllRecords();
            records = records.filter(r => r.id !== recordId);
            localStorage.setItem(this.storageKey, JSON.stringify(records));
            return true;
        } catch (error) {
            console.error('删除对局记录失败:', error);
            return false;
        }
    }
    
    /**
     * 清空所有记录
     */
    clearAllRecords() {
        try {
            localStorage.removeItem(this.storageKey);
            return true;
        } catch (error) {
            console.error('清空对局记录失败:', error);
            return false;
        }
    }
    
    /**
     * 从记录恢复到游戏状态
     */
    restoreFromRecord(record, gameState) {
        try {
            // 重新初始化游戏
            gameState.reset();
            
            // 清空moveHistory，准备重新构建
            gameState.moveHistory = [];
            
            // 重新执行所有移动
            for (const moveData of record.moveHistory) {
                const piece = gameState.getPieceAt(moveData.fromRow, moveData.fromCol);
                if (piece) {
                    // 移除被吃的棋子
                    if (moveData.capturedPiece) {
                        const capturedPiece = gameState.getPieceAt(moveData.toRow, moveData.toCol);
                        if (capturedPiece) {
                            gameState.pieces = gameState.pieces.filter(p => p !== capturedPiece);
                            gameState.capturedPieces[capturedPiece.color].push(capturedPiece);
                        }
                    }
                    
                    // 移动棋子
                    piece.moveTo(moveData.toRow, moveData.toCol);
                    gameState.playerTurn = gameState.playerTurn === 'red' ? 'black' : 'red';
                    gameState.movesCount++;
                    
                    // 更新将军状态
                    const { GameRules } = window;
                    gameState.inCheck = GameRules.isCheck(gameState.pieces, gameState.playerTurn);
                    
                    // 将移动添加到历史记录中
                    gameState.moveHistory.push({
                        piece: piece,
                        fromRow: moveData.fromRow,
                        fromCol: moveData.fromCol,
                        toRow: moveData.toRow,
                        toCol: moveData.toCol,
                        capturedPiece: moveData.capturedPiece ? piece : null,
                        wasInCheck: moveData.wasInCheck || false
                    });
                }
            }
            
            gameState.gameOver = !!record.winner;
            gameState.winner = record.winner;
            
            return true;
        } catch (error) {
            console.error('从记录恢复失败:', error);
            return false;
        }
    }
    
    /**
     * 计算对局时长
     */
    calculateDuration(gameState) {
        const { redTime, blackTime } = gameState.getTimes();
        return redTime + blackTime;
    }
    
    /**
     * 序列化游戏状态
     */
    serializeGameState(gameState) {
        return {
            pieces: gameState.pieces.map(p => ({
                name: p.name,
                color: p.color,
                row: p.row,
                col: p.col
            })),
            playerTurn: gameState.playerTurn,
            gameOver: gameState.gameOver,
            winner: gameState.winner,
            movesCount: gameState.movesCount
        };
    }
    
    /**
     * 格式化时间显示
     */
    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    /**
     * 格式化日期显示
     */
    formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameRecordManager = GameRecordManager;
}
