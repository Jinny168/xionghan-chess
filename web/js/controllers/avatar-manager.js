/**
 * 头像管理器
 * 支持Canvas绘制默认头像和从网络加载自定义头像
 */
class AvatarManager {
    constructor() {
        this.avatars = {};
        this.cache = new Map();
        this.defaultColors = {
            red: ['#ff6b6b', '#c92a2a'],
            black: ['#495057', '#212529']
        };
    }
    
    /**
     * 获取玩家头像（Canvas元素）
     * @param {Object} player - 玩家信息
     * @param {string} player.camp - 阵营（red/black）
     * @param {string} player.name - 玩家名称
     * @param {string} [player.avatarUrl] - 自定义头像URL（可选）
     * @param {number} size - 头像尺寸
     * @returns {HTMLCanvasElement} 头像Canvas元素
     */
    getAvatar(player, size = 60) {
        const cacheKey = `${player}-${size}`;
        
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        let avatar;
        
        // 如果玩家有自定义头像URL，尝试加载
        if (player.avatarUrl) {
            avatar = this.loadCustomAvatar(player.avatarUrl, size);
        } else {
            // 使用默认绘制的头像
            avatar = this.drawDefaultAvatar(player, size);
        }
        
        this.cache.set(cacheKey, avatar);
        return avatar;
    }
    
    /**
     * 绘制默认头像
     */
    drawDefaultAvatar(player, size) {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        
        // 背景圆形
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = size / 2 - 2;
        
        // 渐变背景
        const gradient = ctx.createRadialGradient(
            centerX - radius/3, 
            centerY - radius/3, 
            0, 
            centerX, 
            centerY, 
            radius
        );
        
        const colors = player.camp === 'red' ? 
            this.defaultColors.red : 
            this.defaultColors.black;
        
        gradient.addColorStop(0, colors[0]);
        gradient.addColorStop(1, colors[1]);
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // 边框
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // 绘制文字（玩家首字母或阵营标识）
        ctx.font = `bold ${size * 0.5}px Arial`;
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const text = player.name ? player.name.charAt(0).toUpperCase() : 
                     (player.camp === 'red' ? '红' : '黑');
        ctx.fillText(text, centerX, centerY);
        
        return canvas;
    }
    
    /**
     * 加载自定义头像
     */
    loadCustomAvatar(url, size) {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        
        const img = new Image();
        img.crossOrigin = 'anonymous';
        
        img.onload = () => {
            // 裁剪为圆形
            ctx.save();
            ctx.beginPath();
            ctx.arc(size/2, size/2, size/2 - 2, 0, Math.PI * 2);
            ctx.closePath();
            ctx.clip();
            
            // 绘制图片
            ctx.drawImage(img, 0, 0, size, size);
            
            // 边框
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            ctx.restore();
        };
        
        img.onerror = () => {
            console.warn(`头像加载失败: ${url}，使用默认头像`);
            // 加载失败时使用默认头像
            const defaultPlayer = { camp: 'red', name: '?' };
            const defaultAvatar = this.drawDefaultAvatar(defaultPlayer, size);
            ctx.drawImage(defaultAvatar, 0, 0);
        };
        
        img.src = url;
        
        return canvas;
    }
    
    /**
     * 从DiceBear API获取随机头像
     */
    getRandomAvatar(seed, size = 60) {
        const styles = [
            'adventurer',
            'avatars',
            'big-ears',
            'bots',
            'cradles',
            'fun-emoji',
            'icons',
            'identicon',
            'initials',
            'lorelei',
            'micah',
            'minivans',
            'open-peeps',
            'personas',
            'pixel-art'
        ];
        
        const style = styles[Math.floor(Math.random() * styles.length)];
        const url = `https://api.dicebear.com/7.x/${style}/svg?seed=${seed}&backgroundColor=b6e3f4,c0aede,d1d4f9`;
        
        return this.loadCustomAvatar(url, size);
    }
    
    /**
     * 预加载多个头像
     */
    preloadAvatars(players, size = 60) {
        players.forEach(player => {
            this.getAvatar(player, size);
        });
    }
    
    /**
     * 清除缓存
     */
    clearCache() {
        this.cache.clear();
    }
    
    /**
     * 设置头像样式配置
     */
    setAvatarStyle(config) {
        this.defaultColors = config.colors || this.defaultColors;
    }
}

// 导出全局实例
window.AvatarManager = AvatarManager;
