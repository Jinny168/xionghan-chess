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
    
    /**
     * 生成HTML格式的统计报告（用于展示）
     * @returns {string} HTML字符串
     */
    generateStatisticsHTML() {
        const report = this.getStatisticsReport();
        const stats = this.data;
        
        // 棋子名称映射
        const pieceNames = {
            ju: '車', ma: '马', xiang: '相/象', shi: '士/仕', king: '将/帅',
            pao: '炮', pawn: '兵/卒', wei: '尉/卫', she: '射', lei: '檑',
            jia: '甲', ci: '刺', dun: '盾', xun: '巡'
        };
        
        let html = `
            <div class="statistics-container" style="padding: 20px; line-height: 1.8;">
                <!-- 总体数据 -->
                <div class="stat-section">
                    <h3 style="color: #2f54eb; margin-bottom: 15px;">📊 总体数据</h3>
                    <div class="stat-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        <div class="stat-item"><strong>总游戏数：</strong>${report.totalGames} 局</div>
                        <div class="stat-item"><strong>总走子数：</strong>${report.totalMoves} 步</div>
                        <div class="stat-item"><strong>总游戏时长：</strong>${report.totalTime}</div>
                        <div class="stat-item"><strong>最长单局：</strong>${report.longestGame}</div>
                    </div>
                </div>
                
                <!-- 胜率统计 -->
                <div class="stat-section" style="margin-top: 20px;">
                    <h3 style="color: #2f54eb; margin-bottom: 15px;">🏆 胜率统计</h3>
                    <div class="stat-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        <div class="stat-item" style="color: #d32f2f;"><strong>红方胜利：</strong>${stats.gamesWon.red} 次 (${report.winRate.red})</div>
                        <div class="stat-item"><strong>黑方胜利：</strong>${stats.gamesWon.black} 次 (${report.winRate.black})</div>
                        <div class="stat-item"><strong>平局：</strong>${stats.gamesWon.draw} 次 (${report.winRate.draw})</div>
                    </div>
                </div>
                
                <!-- 连胜记录 -->
                <div class="stat-section" style="margin-top: 20px;">
                    <h3 style="color: #2f54eb; margin-bottom: 15px;">🔥 连胜记录</h3>
                    <div class="stat-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        <div class="stat-item"><strong>红方最高连胜：</strong>${report.maxStreak.red} 局</div>
                        <div class="stat-item"><strong>黑方最高连胜：</strong>${report.maxStreak.black} 局</div>
                        <div class="stat-item" style="color: #d32f2f;"><strong>红方当前连胜：</strong>${report.currentStreak.red} 局</div>
                        <div class="stat-item"><strong>黑方当前连胜：</strong>${report.currentStreak.black} 局</div>
                    </div>
                </div>
                
                <!-- 最快胜利 -->
                <div class="stat-section" style="margin-top: 20px;">
                    <h3 style="color: #2f54eb; margin-bottom: 15px;">⚡ 最快胜利</h3>
                    <div class="stat-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        <div class="stat-item" style="color: #d32f2f;"><strong>红方最快胜利：</strong>${report.fastestWin.red}</div>
                        <div class="stat-item"><strong>黑方最快胜利：</strong>${report.fastestWin.black}</div>
                    </div>
                </div>
                
                <!-- 被吃棋子统计 -->
                <div class="stat-section" style="margin-top: 20px;">
                    <h3 style="color: #2f54eb; margin-bottom: 15px;">♟️ 被吃棋子统计</h3>
                    <div class="stat-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
        `;
        
        // 添加棋子统计
        Object.entries(stats.piecesCaptured).forEach(([piece, count]) => {
            if (count > 0) {
                const pieceName = pieceNames[piece] || piece;
                html += `<div class="stat-item"><strong>${pieceName}：</strong>${count} 个</div>`;
            }
        });
        
        html += `
                    </div>
                </div>
                
                <!-- 最后游戏时间 -->
                <div class="stat-section" style="margin-top: 20px;">
                    <h3 style="color: #2f54eb; margin-bottom: 15px;">🕒 最近游戏</h3>
                    <div class="stat-item"><strong>最后游戏时间：</strong>${report.lastPlayed}</div>
                </div>
            </div>
        `;
        
        return html;
    }
    
    /**
     * 显示统计数据对话框
     */
    showStatisticsDialog() {
        const html = this.generateStatisticsHTML();
        
        window.dialogManager.showConfirm(
            '📊 游戏统计数据',
            html,
            () => {
                // 确认按钮 - 导出数据
                this.exportStatistics();
            },
            null,
            '📤 导出数据',
            '关闭'
        );
    }
    
    /**
     * 导出统计数据为JSON文件
     * @param {string|null} filename - 文件名（可选，默认为null）
     */
    exportStatistics(filename = null) {
        try {
            // 生成文件名
            if (!filename) {
                const now = new Date();
                const dateStr = now.toISOString().replace(/[:.]/g, '-').split('T')[0];
                filename = `xionghan_chess_stats_${dateStr}.json`;
            }
            
            // 准备导出数据
            const exportData = {
                title: '匈汉象棋统计数据',
                exportTime: new Date().toISOString(),
                statistics: this.data
            };
            
            // 转换为JSON字符串
            const jsonStr = JSON.stringify(exportData, null, 2);
            
            // 创建Blob对象
            const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8' });
            
            // 创建下载链接
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.style.display = 'none';
            
            // 触发下载
            document.body.appendChild(a);
            a.click();
            
            // 清理
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            console.log('✅ 统计数据已导出:', filename);
            alert('✅ 统计数据已成功导出！');
        } catch (error) {
            console.error('❌ 导出统计数据失败:', error);
            alert('❌ 导出失败：' + error.message);
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.StatisticsManager = StatisticsManager;
}
