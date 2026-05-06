/**
 * 复盘控制器模块
 * 负责处理复盘相关的所有逻辑，包括进度控制、状态回溯等
 */

class ReplayController {
    constructor(gameState) {
        // 保留对游戏状态的引用
        this.gameState = gameState;
        
        // 存储历史状态的列表
        this.historyStates = [];
        
        // 当前步骤索引
        this.currentStep = 0;
        
        // 最大步骤数
        this.maxSteps = 0;
        
        // 复盘模式标志
        this.isReplayMode = false;
        
        // 原始游戏状态（用于恢复）
        this.originalState = null;
    }
    
    /**
     * 进入复盘模式的工厂方法
     */
    static enterReplayMode(gameState) {
        const controller = new ReplayController(gameState);
        controller.startReplay();
        return controller;
    }
    
    /**
     * 开始复盘模式
     */
    startReplay() {
        // 深拷贝保存原始状态
        this.originalState = this.deepCopyGameState(this.gameState);
        
        // 创建临时游戏状态，从初始位置开始重现每一步
        const tempGameState = new GameState();
        
        // 重建历史状态列表
        this.historyStates = [this.deepCopyGameState(tempGameState)];
        
        // 逐步执行历史中的每一步
        for (const moveRecord of this.gameState.moveHistory) {
            const { piece, fromRow, fromCol, toRow, toCol, capturedPiece } = moveRecord;
            
            // 在临时状态上执行移动
            const tempPiece = tempGameState.getPieceAt(fromRow, fromCol);
            if (tempPiece) {
                // 移除被吃的棋子
                if (capturedPiece) {
                    tempGameState.pieces = tempGameState.pieces.filter(p => p !== capturedPiece);
                }
                
                // 移动棋子
                tempPiece.moveTo(toRow, toCol);
                
                // 切换玩家
                tempGameState.playerTurn = tempGameState.playerTurn === 'red' ? 'black' : 'red';
                tempGameState.movesCount++;
                
                // 更新将军状态
                const { GameRules } = window;
                tempGameState.inCheck = GameRules.isCheck(tempGameState.pieces, tempGameState.playerTurn);
                
                // 添加该步骤的状态到历史
                this.historyStates.push(this.deepCopyGameState(tempGameState));
            }
        }
        
        // 如果没有历史记录，至少保存初始状态
        if (this.historyStates.length === 0) {
            this.historyStates = [this.deepCopyGameState(tempGameState)];
        }
        
        // 默认跳转到开局
        this.currentStep = 0;
        this.maxSteps = this.historyStates.length - 1;
        
        // 应用初始状态
        this.applyState(this.historyStates[0]);
        
        this.isReplayMode = true;
    }
    
    /**
     * 跳转到开局
     */
    goToBeginning() {
        if (this.historyStates.length > 0) {
            this.currentStep = 0;
            this.applyState(this.historyStates[0]);
            return true;
        }
        return false;
    }
    
    /**
     * 跳转到终局
     */
    goToEnd() {
        if (this.historyStates.length > 0) {
            this.currentStep = this.historyStates.length - 1;
            this.applyState(this.historyStates[this.currentStep]);
            return true;
        }
        return false;
    }
    
    /**
     * 上一步
     */
    goToPrevious() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.applyState(this.historyStates[this.currentStep]);
            return true;
        }
        return false;
    }
    
    /**
     * 下一步
     */
    goToNext() {
        if (this.currentStep < this.historyStates.length - 1) {
            this.currentStep++;
            this.applyState(this.historyStates[this.currentStep]);
            return true;
        }
        return false;
    }
    
    /**
     * 跳转到指定步骤
     */
    jumpToStep(step) {
        if (step >= 0 && step < this.historyStates.length) {
            this.currentStep = step;
            this.applyState(this.historyStates[step]);
            return true;
        }
        return false;
    }
    
    /**
     * 获取复盘进度百分比
     */
    getProgressPercentage() {
        if (this.historyStates.length <= 1) {
            return this.historyStates.length > 0 ? 100 : 0;
        }
        return Math.floor((this.currentStep / (this.historyStates.length - 1)) * 100);
    }
    
    /**
     * 设置复盘进度
     */
    setProgress(percentage) {
        if (this.historyStates.length === 0) {
            return false;
        }
        
        const targetStep = Math.floor((percentage / 100) * (this.historyStates.length - 1));
        const clampedStep = Math.max(0, Math.min(targetStep, this.historyStates.length - 1));
        
        this.currentStep = clampedStep;
        this.applyState(this.historyStates[clampedStep]);
        return true;
    }
    
    /**
     * 恢复原始游戏状态
     */
    restoreOriginalState() {
        if (this.originalState) {
            this.copyGameState(this.originalState, this.gameState);
            this.isReplayMode = false;
            return true;
        }
        return false;
    }
    
    /**
     * 应用指定的状态到当前游戏状态
     */
    applyState(state) {
        if (state) {
            this.copyGameState(state, this.gameState);
        }
    }
    
    /**
     * 深拷贝游戏状态
     */
    deepCopyGameState(gameState) {
        return {
            pieces: gameState.pieces.map(p => this.copyPiece(p)),
            playerTurn: gameState.playerTurn,
            gameOver: gameState.gameOver,
            winner: gameState.winner,
            moveHistory: [...gameState.moveHistory],
            capturedPieces: {
                red: [...gameState.capturedPieces.red],
                black: [...gameState.capturedPieces.black]
            },
            movesCount: gameState.movesCount,
            inCheck: gameState.inCheck,
            checkWarningShown: gameState.checkWarningShown,
            consecutiveChecks: gameState.consecutiveChecks,
            lastCheckBy: gameState.lastCheckBy,
            lastMove: gameState.lastMove ? [...gameState.lastMove] : null
        };
    }
    
    /**
     * 复制游戏状态（浅拷贝到目标对象）
     */
    copyGameState(source, target) {
        target.pieces = source.pieces.map(p => this.copyPiece(p));
        target.playerTurn = source.playerTurn;
        target.gameOver = source.gameOver;
        target.winner = source.winner;
        target.moveHistory = [...source.moveHistory];
        target.capturedPieces = {
            red: [...source.capturedPieces.red],
            black: [...source.capturedPieces.black]
        };
        target.movesCount = source.movesCount;
        target.inCheck = source.inCheck;
        target.checkWarningShown = source.checkWarningShown;
        target.consecutiveChecks = source.consecutiveChecks;
        target.lastCheckBy = source.lastCheckBy;
        target.lastMove = source.lastMove ? [...source.lastMove] : null;
    }
    
    /**
     * 复制棋子
     */
    copyPiece(piece) {
        const { PieceFactory } = window;
        const newPiece = PieceFactory.createPieceByName(piece.name, piece.color, piece.row, piece.col);
        return newPiece;
    }
    
    /**
     * 获取当前步骤信息
     */
    getCurrentStepInfo() {
        return {
            current: this.currentStep,
            total: this.maxSteps,
            percentage: this.getProgressPercentage()
        };
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.ReplayController = ReplayController;
}
