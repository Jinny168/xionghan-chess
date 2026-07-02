/**
 * 嘲讽语句管理器
 * 负责管理和随机获取嘲讽语句
 */
class TauntManager {
    constructor(tauntsUrl = null) {
        // 默认使用 docs 目录下的 taunts.json
        this.tauntsUrl = tauntsUrl || 'docs/taunts.json';
        this.taunts = [];

        
        // 异步加载嘲讽语句
        this.loadTaunts().catch(error => {
            console.error('加载嘲讽语句失败:', error);
        });
    }
    
    /**
     * 从配置文件加载嘲讽语句列表
     * @returns {Promise<void>}
     */
    async loadTaunts() {
        try {
            const response = await fetch(this.tauntsUrl);
            if (!response.ok) {
                console.warn(`警告: HTTP ${response.status} 错误，使用默认语句`);
                this.taunts = ['是我天下无敌啦！'];

                return;
            }
            
            const taunts = await response.json();
            
            // 确保返回的是数组
            if (Array.isArray(taunts)) {
                this.taunts = taunts;

                console.log(`成功加载 ${this.taunts.length} 条嘲讽语句`);
            } else {
                console.warn(`警告: ${this.tauntsUrl} 中的嘲讽语句格式不正确，应为数组格式`);
                this.taunts = ['是我天下无敌啦！']; // 默认嘲讽语句

            }
        } catch (error) {
            console.warn(`警告: 加载嘲讽语句时出错: ${error.message}，使用默认语句`);
            this.taunts = ['是我天下无敌啦！'];

        }
    }
    
    /**
     * 获取一个随机的嘲讽语句
     * @returns {string} 随机选择的嘲讽语句，如果没有可用语句则返回默认语句
     */
    getRandomTaunt() {
        if (this.taunts.length > 0) {
            const randomIndex = Math.floor(Math.random() * this.taunts.length);
            return this.taunts[randomIndex];
        } else {
            return '是我天下无敌啦！';
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.TauntManager = TauntManager;
}
