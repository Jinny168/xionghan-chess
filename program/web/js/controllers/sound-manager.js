/**
 * 音效管理器 - Web版本
 * 支持真实音频文件和Web Audio API合成音效（降级方案）
 */
class SoundManager {
    constructor() {
        this.audioContext = null;
        this.sounds = {};
        this.soundEnabled = true;
        this.musicEnabled = true;
        this.volume = 0.7;
        this.useRealSounds = true; // 优先使用真实音频文件
        
        // 音效文件映射（对应桌面版）
        this.soundFiles = {
            move: 'drop.wav',        // 走子音效
            capture: 'eat.wav',      // 吃子音效
            check: 'warn.wav',       // 将军语音
            select: 'choose.wav',    // 选子音效
            button: 'button.wav',    // 按钮点击
            victory: 'fc_victory_sound.wav',  // 胜利音效
            defeat: 'fc_defeat_sound.wav'     // 失败音效
        };
        
        // 背景音乐
        this.backgroundMusic = null;
        this.currentMusicStyle = 'fc'; // 'fc' 或 'qq'
        
        // 初始化音频上下文
        this.initAudioContext();
        
        // 预加载音效
        this.preloadSounds();
    }
    
    /**
     * 初始化AudioContext
     */
    initAudioContext() {
        try {
            // 兼容不同浏览器的AudioContext实现
            // webkitAudioContext 是 Safari 等 WebKit 内核浏览器的实现
            /** @type {AudioContext|webkitAudioContext} */
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                this.audioContext = new AudioContextClass();
            }
        } catch (e) {
            console.warn('Web Audio API 不支持:', e);
        }
    }
    
    /**
     * 预加载音效
     */
    preloadSounds() {
        if (this.useRealSounds) {
            // 尝试加载真实音频文件
            this.loadRealSounds();
        } else {
            // 使用合成音效作为降级方案
            this.loadSynthSounds();
        }
    }
    
    /**
     * 加载真实音频文件
     */
    loadRealSounds() {
        Object.keys(this.soundFiles).forEach(type => {
            const filename = this.soundFiles[type];
            const audio = new Audio(`sounds/${filename}`);
            audio.volume = this.volume;
            audio.preload = 'auto';
            
            // 监听加载错误，降级到合成音效
            audio.onerror = () => {
                console.warn(`无法加载音效文件: ${filename}，将使用合成音效`);
                this.useRealSounds = false;
                this.loadSynthSounds();
            };
            
            this.sounds[type] = audio;
        });
        
        console.log('真实音效文件加载完成');
    }
    
    /**
     * 加载合成音效（降级方案）
     */
    loadSynthSounds() {
        console.log('使用Web Audio API合成音效');
        
        // 定义各种音效类型
        const soundTypes = [
            'move',      // 移动棋子
            'capture',   // 吃子
            'check',     // 将军
            'select',    // 选择棋子
            'button',    // 按钮点击
            'victory',   // 胜利
            'defeat'     // 失败
        ];
        
        soundTypes.forEach(type => {
            this.sounds[type] = this.createSynthSound(type);
        });
    }
    
    /**
     * 创建合成音效
     */
    createSynthSound(type) {
        if (!this.audioContext) return null;
        
        const duration = this.getSoundDuration(type);
        const frequency = this.getSoundFrequency(type);
        const waveType = this.getWaveType(type);
        
        return {
            duration,
            frequency,
            waveType,
            type
        };
    }
    
    /**
     * 获取音效时长
     */
    getSoundDuration(type) {
        const durations = {
            move: 0.1,
            capture: 0.15,
            check: 0.3,
            select: 0.08,
            button: 0.05,
            victory: 0.5,
            defeat: 0.6
        };
        return durations[type] || 0.1;
    }
    
    /**
     * 获取音效频率
     */
    getSoundFrequency(type) {
        const frequencies = {
            move: 440,        // A4
            capture: 330,     // E4
            check: 880,       // A5
            select: 523,      // C5
            button: 600,
            victory: 523,     // C大调和弦
            defeat: 262       // C4
        };
        return frequencies[type] || 440;
    }
    
    /**
     * 获取波形类型
     */
    getWaveType(type) {
        const waveTypes = {
            move: 'sine',
            capture: 'square',
            check: 'triangle',
            select: 'sine',
            button: 'sine',
            victory: 'sine',
            defeat: 'sawtooth'
        };
        return waveTypes[type] || 'sine';
    }
    
    /**
     * 播放音效
     */
    play(soundType) {
        if (!this.soundEnabled) return;
        
        const sound = this.sounds[soundType];
        if (!sound) {
            console.warn(`音效不存在: ${soundType}`);
            return;
        }
        
        try {
            // 如果是HTMLAudioElement（真实音频文件）
            if (sound instanceof HTMLAudioElement) {
                sound.currentTime = 0; // 重置到开头
                sound.volume = this.volume;
                sound.play().catch(e => {
                    console.error(`播放音效失败: ${soundType}`, e);
                });
            } 
            // 如果是合成音效对象
            else if (this.audioContext) {
                // 恢复AudioContext（浏览器策略要求用户交互后才能播放）
                if (this.audioContext.state === 'suspended') {
                    this.audioContext.resume();
                }
                
                const oscillator = this.audioContext.createOscillator();
                const gainNode = this.audioContext.createGain();
                
                oscillator.type = sound.waveType;
                oscillator.frequency.setValueAtTime(sound.frequency, this.audioContext.currentTime);
                
                gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + sound.duration);
                
                oscillator.connect(gainNode);
                gainNode.connect(this.audioContext.destination);
                
                oscillator.start(this.audioContext.currentTime);
                oscillator.stop(this.audioContext.currentTime + sound.duration);
            }
            
        } catch (e) {
            console.error(`播放音效失败: ${soundType}`, e);
        }
    }
    
    /**
     * 播放移动音效
     */
    playMove() {
        this.play('move');
    }
    
    /**
     * 播放吃子音效
     */
    playCapture() {
        this.play('capture');
    }
    
    /**
     * 播放将军音效
     */
    playCheck() {
        this.play('check');
    }
    
    /**
     * 播放选择音效
     */
    playSelect() {
        this.play('select');
    }
    
    /**
     * 播放按钮音效
     */
    playButton() {
        this.play('button');
    }
    
    /**
     * 播放胜利音效
     */
    playVictory() {
        this.play('victory');
        // 播放和弦效果
        setTimeout(() => this.playNote(659), 100);  // E5
        setTimeout(() => this.playNote(784), 200);  // G5
    }
    
    /**
     * 播放失败音效
     */
    playDefeat() {
        this.play('defeat');
        setTimeout(() => this.playNote(220), 150);  // A3
    }
    
    /**
     * 播放单个音符
     */
    playNote(frequency) {
        if (!this.audioContext) return;
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
            
            gainNode.gain.setValueAtTime(this.volume * 0.5, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.2);
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + 0.2);
            
        } catch (e) {
            console.error('播放音符失败:', e);
        }
    }
    
    /**
     * 设置音量
     */
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
    }
    
    /**
     * 启用/禁用音效
     */
    setSoundEnabled(enabled) {
        this.soundEnabled = enabled;
    }
    
    /**
     * 检查并播放游戏音效（将军/绝杀）
     */
    checkAndPlayGameSound(gameState) {
        if (!gameState) return;
        
        // 优先处理绝杀
        if (gameState.isCheckmate && gameState.isCheckmate()) {
            this.playDefeat();
        } 
        // 普通将军
        else if (gameState.isCheck && gameState.isCheck()) {
            this.playCheck();
        }
    }
    
    /**
     * 播放背景音乐
     */
    playBackgroundMusic(style = 'fc') {
        if (!this.musicEnabled) return;
        
        this.currentMusicStyle = style;
        const filename = style === 'qq' ? 'qq_background_sound.wav' : 'fc_background_sound.wav';
        
        // 停止当前音乐
        if (this.backgroundMusic) {
            this.backgroundMusic.pause();
            this.backgroundMusic.currentTime = 0;
        }
        
        // 加载新音乐
        this.backgroundMusic = new Audio(`sounds/${filename}`);
        this.backgroundMusic.loop = true; // 循环播放
        this.backgroundMusic.volume = this.volume * 0.5; // 背景音乐音量稍低
        
        this.backgroundMusic.play().catch(e => {
            console.warn('背景音乐播放失败:', e);
        });
        
        console.log(`开始播放背景音乐: ${style}`);
    }
    
    /**
     * 停止背景音乐
     */
    stopBackgroundMusic() {
        if (this.backgroundMusic) {
            this.backgroundMusic.pause();
            this.backgroundMusic.currentTime = 0;
        }
    }
    
    /**
     * 切换背景音乐风格
     */
    toggleMusicStyle() {
        const newStyle = this.currentMusicStyle === 'fc' ? 'qq' : 'fc';
        this.playBackgroundMusic(newStyle);
        return newStyle;
    }
    
    /**
     * 设置音乐音量
     */
    setMusicVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        if (this.backgroundMusic) {
            this.backgroundMusic.volume = this.volume * 0.5;
        }
    }
}

// 导出全局实例
window.SoundManager = SoundManager;
