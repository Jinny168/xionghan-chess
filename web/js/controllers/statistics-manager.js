/**
 * 匈汉象棋数据统计管理器
 * 负责统计和保存游戏数据
 */
class StatisticsManager {
    constructor() {
        this.storageKey = 'xionghan_chess_statistics';
        this.data = this.loadStatistics();
    }
    
    /**
     * 获取默认统计数据结构
     */
    getDefaultStatistics() {
        return {
            gamesPlayed: 0,                    // 总游戏数
            gamesWon: {                        // 各方胜利次数
                red: 0,
                black: 0,
                draw: 0
            },
            totalTimePlayed: 0,                // 总游戏时长（秒）
            piecesCaptured: {                  // 各类棋子被吃总数
                ju: 0,                         // 車
                ma: 0,                         // 馬
                xiang: 0,                      // 相/象
                shi: 0,                        // 士/仕
                king: 0,                       // 将/帥
                pao: 0,                        // 炮/砲
                pawn: 0,                       // 兵/卒
                wei: 0,                        // 尉/衛
                she: 0,                        // 射/䠶
                lei: 0,                        // 檑/礌
                jia: 0,                        // 甲/
                ci: 0,                         // 刺
                dun: 0,                        // 盾
                xun: 0                         // 巡/廵
            },
            fastestWin: {                      // 最快胜利记录（秒）
                red: Infinity,
                black: Infinity
            },
            longestGame: 0,                    // 最长单局时长（秒）
            favoritePiece: {                   // 最喜欢使用的棋子
                red: '',
                black: ''
            },
            winStreak: {                       // 连胜记录
                red: 0,
                black: 0,
                currentStreak: { red: 0, black: 0 }
            },
            lastPlayed: '',                    // 最后游戏时间
            totalMovesMade: 0                  // 总走子数
        };
    }
    
    /**
     * 加载统计数据，如果不存在则创建默认数据
     */
    loadStatistics() {
        try {
            const data = localStorage.getItem(this.storageKey);
            if (data) {
                const parsed = JSON.parse(data);
                // 确保数据结构完整
                return this.ensureStructure(parsed);
            } else {
                // 文件不存在，返回默认数据
                return this.getDefaultStatistics();
            }
        } catch (error) {
            console.error(`加载统计数据失败: ${error.message}`);
            // 文件损坏或读取错误，返回默认数据
            return this.getDefaultStatistics();
        }
    }
    
    /**
     * 确保统计数据结构完整，补充缺失字段
     */
    ensureStructure(data) {
        const defaultData = this.getDefaultStatistics();
        
        // 检查顶层字段
        for (const key in defaultData) {
            if (!(key in data)) {
                data[key] = defaultData[key];
            } else if (typeof defaultData[key] === 'object' && !Array.isArray(defaultData[key]) && data[key] !== null) {
                // 递归处理嵌套对象
                for (const subKey in defaultData[key]) {
                    if (!(subKey in data[key])) {
                        data[key][subKey] = defaultData[key][subKey];
                    }
                }
            }
        }
        
        return data;
    }
    
    /**
     * 保存统计数据到localStorage
     */
    saveStatistics() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.data));
        } catch (error) {
            console.error(`保存统计数据失败: ${error.message}`);
        }
    }
    
    /**
     * 更新游戏次数
     */
    updateGamesPlayed(increment = 1) {
        this.data.gamesPlayed += increment;
        this.data.lastPlayed = new Date().toISOString();
        this.saveStatistics();
    }
    
    /**
     * 更新游戏结果
     * 
     * @param {string} winner - 获胜方 ("red", "black", "draw")
     * @param {number} gameDuration - 游戏时长（秒）
     */
    updateGameResult(winner, gameDuration = 0) {
        if (winner === 'red' || winner === 'black') {
            this.data.gamesWon[winner]++;
            
            // 更新最快胜利记录
            if (gameDuration > 0 && gameDuration < this.data.fastestWin[winner]) {
                this.data.fastestWin[winner] = gameDuration;
            }
            
            // 更新连胜记录
            this.data.winStreak.currentStreak[winner]++;
            if (this.data.winStreak.currentStreak[winner] > this.data.winStreak[winner]) {
                this.data.winStreak[winner] = this.data.winStreak.currentStreak[winner];
            }
            
            // 更新其他方连败记录
            const otherSide = winner === 'red' ? 'black' : 'red';
            this.data.winStreak.currentStreak[otherSide] = 0;
            
        } else if (winner === 'draw') {
            this.data.gamesWon.draw++;
            // 和局重置双方连胜记录
            this.data.winStreak.currentStreak.red = 0;
            this.data.winStreak.currentStreak.black = 0;
        }
        
        // 更新总游戏时长和最长游戏记录
        if (gameDuration > 0) {
            this.data.totalTimePlayed += gameDuration;
            if (gameDuration > this.data.longestGame) {
                this.data.longestGame = gameDuration;
            }
        }
        
        this.saveStatistics();
    }
    
    /**
     * 更新被吃棋子统计
     * 
     * @param {string} pieceType - 棋子类型
     * @param {number} increment - 增量
     */
    updatePiecesCaptured(pieceType, increment = 1) {
        if (pieceType in this.data.piecesCaptured) {
            this.data.piecesCaptured[pieceType] += increment;
        }
        this.saveStatistics();
    }
    
    /**
     * 更新总走子数
     */
    updateTotalMoves(increment = 1) {
        this.data.totalMovesMade += increment;
        this.saveStatistics();
    }
    
    /**
     * 获取所有统计数据
     */
    getStatistics() {
        return { ...this.data };
    }
    
    /**
     * 重置所有统计数据
     */
    resetStatistics() {
        this.data = this.getDefaultStatistics();
        this.saveStatistics();
        console.log('统计数据已重置');
    }
    
    /**
     * 获取格式化后的统计报告
     */
    getStatisticsReport() {
        const stats = this.data;
        
        // 格式化时间
        const formatTime = (seconds) => {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            if (hours > 0) {
                return `${hours}小时${minutes}分钟${secs}秒`;
            } else if (minutes > 0) {
                return `${minutes}分钟${secs}秒`;
            } else {
                return `${secs}秒`;
            }
        };
        
        // 格式化最快胜利时间
        const formatFastestWin = (time) => {
            return time === Infinity ? '无记录' : formatTime(time);
        };
        
        return {
            totalGames: stats.gamesPlayed,
            winRate: {
                red: stats.gamesPlayed > 0 ? ((stats.gamesWon.red / stats.gamesPlayed) * 100).toFixed(1) + '%' : '0%',
                black: stats.gamesPlayed > 0 ? ((stats.gamesWon.black / stats.gamesPlayed) * 100).toFixed(1) + '%' : '0%',
                draw: stats.gamesPlayed > 0 ? ((stats.gamesWon.draw / stats.gamesPlayed) * 100).toFixed(1) + '%' : '0%'
            },
            totalTime: formatTime(stats.totalTimePlayed),
            longestGame: formatTime(stats.longestGame),
            fastestWin: {
                red: formatFastestWin(stats.fastestWin.red),
                black: formatFastestWin(stats.fastestWin.black)
            },
            currentStreak: {
                red: stats.winStreak.currentStreak.red,
                black: stats.winStreak.currentStreak.black
            },
            maxStreak: {
                red: stats.winStreak.red,
                black: stats.winStreak.black
            },
            totalMoves: stats.totalMovesMade,
            lastPlayed: stats.lastPlayed ? new Date(stats.lastPlayed).toLocaleString('zh-CN') : '从未'
        };
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.StatisticsManager = StatisticsManager;
}
