/**
 * 游戏规则配置管理器
 * 管理自定义棋子规则的启用/禁用状态
 */

class GameRuleConfig {
    constructor() {
        // 默认规则配置
        this.defaultConfig = {
            horseStraightThree: false,  // 马可以走直三
            advisorOutPalace: false,    // 仕/士可以出九宫
            elephantCrossRiver: false,  // 相/象可以跨越长城
            kingOutPalace: false,       // 汉/汗可以出九宫
            kingPalaceEightDirection: false,  // 汉/汗在九宫内保持8方向能力（默认关闭，等同传统将帅）
            kingKeepEightDirection: false  // 汉/汗出了九宫后保持8方向能力
        };
        
        // 当前配置
        this.config = { ...this.defaultConfig };
        
        // 从localStorage加载配置
        this.loadConfig();
    }
    
    /**
     * 从localStorage加载配置
     */
    loadConfig() {
        try {
            const saved = localStorage.getItem('xionghanChessRuleConfig');
            if (saved) {
                const parsed = JSON.parse(saved);
                this.config = { ...this.defaultConfig, ...parsed };
                console.log('✅ 已加载自定义规则配置:', this.config);
            }
        } catch (e) {
            console.error('❌ 加载规则配置失败:', e);
            this.config = { ...this.defaultConfig };
        }
    }
    
    /**
     * 保存配置到localStorage
     */
    saveConfig() {
        try {
            localStorage.setItem('xionghanChessRuleConfig', JSON.stringify(this.config));
            console.log('✅ 已保存自定义规则配置');
        } catch (e) {
            console.error('❌ 保存规则配置失败:', e);
        }
    }
    
    /**
     * 重置为默认配置
     */
    resetToDefault() {
        this.config = { ...this.defaultConfig };
        this.saveConfig();
        console.log('✅ 已重置为默认规则配置');
    }
    
    /**
     * 获取配置值
     */
    get(key) {
        return this.config[key] !== undefined ? this.config[key] : this.defaultConfig[key];
    }
    
    /**
     * 设置配置值
     */
    set(key, value) {
        if (this.config.hasOwnProperty(key) || this.defaultConfig.hasOwnProperty(key)) {
            this.config[key] = value;
            this.saveConfig();
            return true;
        }
        return false;
    }
    
    /**
     * 获取所有配置
     */
    getAll() {
        return { ...this.config };
    }
    
    /**
     * 绑定UI控件
     */
    bindUI() {
        // 马可以走直三
        const horseCheckbox = document.getElementById('rule-horse-straight-three');
        if (horseCheckbox) {
            horseCheckbox.checked = this.get('horseStraightThree');
            horseCheckbox.addEventListener('change', (e) => {
                this.set('horseStraightThree', e.target.checked);
                console.log(`🐴 马走直三规则: ${e.target.checked ? '开启' : '关闭'}`);
            });
        }
        
        // 仕/士可以出九宫
        const advisorCheckbox = document.getElementById('rule-advisor-out-palace');
        if (advisorCheckbox) {
            advisorCheckbox.checked = this.get('advisorOutPalace');
            advisorCheckbox.addEventListener('change', (e) => {
                this.set('advisorOutPalace', e.target.checked);
                console.log(`🛡️ 仕出九宫规则: ${e.target.checked ? '开启' : '关闭'}`);
            });
        }
        
        // 相/象可以跨越长城
        const elephantCheckbox = document.getElementById('rule-elephant-cross-river');
        if (elephantCheckbox) {
            elephantCheckbox.checked = this.get('elephantCrossRiver');
            elephantCheckbox.addEventListener('change', (e) => {
                this.set('elephantCrossRiver', e.target.checked);
                console.log(`🐘 相跨河规则: ${e.target.checked ? '开启' : '关闭'}`);
            });
        }
        
        // 汉/汗可以出九宫
        const kingCheckbox = document.getElementById('rule-king-out-palace');
        const kingPalaceDirectionCheckbox = document.getElementById('rule-king-palace-eight-direction');
        const kingDirectionCheckbox = document.getElementById('rule-king-keep-eight-direction');
        
        if (kingCheckbox) {
            kingCheckbox.checked = this.get('kingOutPalace');
            
            // 根据第一个选项的状态更新第二个和第三个选项的启用状态
            const updateDirectionCheckboxesState = () => {
                if (kingDirectionCheckbox) {
                    if (kingCheckbox.checked) {
                        // 允许出九宫时，启用第二个选项
                        kingDirectionCheckbox.disabled = false;
                        kingDirectionCheckbox.parentElement.style.opacity = '1';
                        kingDirectionCheckbox.parentElement.style.cursor = 'pointer';
                    } else {
                        // 不允许出九宫时，禁用第二个选项
                        kingDirectionCheckbox.disabled = true;
                        kingDirectionCheckbox.parentElement.style.opacity = '0.5';
                        kingDirectionCheckbox.parentElement.style.cursor = 'not-allowed';
                    }
                }
            };
            
            // 初始设置状态
            updateDirectionCheckboxesState();
            
            // 监听变化
            kingCheckbox.addEventListener('change', (e) => {
                this.set('kingOutPalace', e.target.checked);
                console.log(`👑 汉出九宫规则: ${e.target.checked ? '开启' : '关闭'}`);
                updateDirectionCheckboxesState();
            });
        }
        
        // 汉/汗在九宫内保持8方向能力
        if (kingPalaceDirectionCheckbox) {
            kingPalaceDirectionCheckbox.checked = this.get('kingPalaceEightDirection');
            kingPalaceDirectionCheckbox.addEventListener('change', (e) => {
                this.set('kingPalaceEightDirection', e.target.checked);
                console.log(`👑 汉宫内8方向规则: ${e.target.checked ? '开启' : '关闭'}`);
            });
        }
        
        // 汉/汗出了九宫后保持8方向能力
        if (kingDirectionCheckbox) {
            kingDirectionCheckbox.checked = this.get('kingKeepEightDirection');
            kingDirectionCheckbox.addEventListener('change', (e) => {
                this.set('kingKeepEightDirection', e.target.checked);
                console.log(`👑 汉宫外8方向规则: ${e.target.checked ? '开启' : '关闭'}`);
            });
        }
        
        // 恢复默认按钮
        const resetBtn = document.getElementById('btn-reset-settings');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetToDefault();
                this.updateUI();
                alert('✅ 已恢复默认规则配置');
            });
        }
    }
    
    /**
     * 更新UI显示
     */
    updateUI() {
        const horseCheckbox = document.getElementById('rule-horse-straight-three');
        if (horseCheckbox) horseCheckbox.checked = this.get('horseStraightThree');
        
        const advisorCheckbox = document.getElementById('rule-advisor-out-palace');
        if (advisorCheckbox) advisorCheckbox.checked = this.get('advisorOutPalace');
        
        const elephantCheckbox = document.getElementById('rule-elephant-cross-river');
        if (elephantCheckbox) elephantCheckbox.checked = this.get('elephantCrossRiver');
        
        const kingCheckbox = document.getElementById('rule-king-out-palace');
        const kingPalaceDirectionCheckbox = document.getElementById('rule-king-palace-eight-direction');
        const kingDirectionCheckbox = document.getElementById('rule-king-keep-eight-direction');
        
        if (kingCheckbox) {
            kingCheckbox.checked = this.get('kingOutPalace');
            
            // 更新第二个选项的状态
            if (kingDirectionCheckbox) {
                if (kingCheckbox.checked) {
                    kingDirectionCheckbox.disabled = false;
                    kingDirectionCheckbox.parentElement.style.opacity = '1';
                    kingDirectionCheckbox.parentElement.style.cursor = 'pointer';
                } else {
                    kingDirectionCheckbox.disabled = true;
                    kingDirectionCheckbox.parentElement.style.opacity = '0.5';
                    kingDirectionCheckbox.parentElement.style.cursor = 'not-allowed';
                }
            }
        }
        
        if (kingPalaceDirectionCheckbox) {
            kingPalaceDirectionCheckbox.checked = this.get('kingPalaceEightDirection');
        }
        
        if (kingDirectionCheckbox) {
            kingDirectionCheckbox.checked = this.get('kingKeepEightDirection');
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameRuleConfig = GameRuleConfig;
}
