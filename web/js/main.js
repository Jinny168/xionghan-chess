/**
 * 雄汉象棋网页版主入口
 */

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', () => {
    console.log('雄汉象棋网页版启动');
    
    // 解析URL参数获取游戏模式
    const urlParams = new URLSearchParams(window.location.search);
    const gameMode = urlParams.get('mode') || 'local'; // 默认单机模式
    const roomId = urlParams.get('room') || urlParams.get('roomId'); // 兼容两种参数名
    
    console.log(`游戏模式: ${gameMode}, 房间号: ${roomId || '无'}`);
    
    // 恢复暗黑模式设置
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        document.body.classList.add('dark-mode');
        const darkModeBtn = document.getElementById('btn-dark-mode');
        if (darkModeBtn) {
            darkModeBtn.textContent = '☀️';
        }
    }
    
    // 设置Canvas尺寸（在初始化GameController之前）
    const canvas = document.getElementById('chess-board');
    const container = document.querySelector('.board-container');
    if (canvas && container) {
        // 根据容器大小自适应设置Canvas尺寸
        let resizeTimer;
        const updateCanvasSize = () => {
            // 清除之前的定时器
            clearTimeout(resizeTimer);
            // 使用requestAnimationFrame优化性能
            resizeTimer = setTimeout(() => {
                requestAnimationFrame(() => {
                    const containerWidth = container.clientWidth - 80; // 减去padding (40*2)
                    const containerHeight = container.clientHeight - 80;
                    const size = Math.min(containerWidth, containerHeight, 1200); // 最大1200px，更充分利用空间
                    canvas.width = size;
                    canvas.height = size;
                    console.log(`Canvas尺寸设置为: ${size}x${size}`);
                    
                    // 如果游戏已初始化，重新渲染
                    if (window.game && window.game.renderer) {
                        window.game.renderer.calculateDimensions();
                        window.game.render();
                    }
                });
            }, 150); // 150ms防抖延迟
        };
        
        // 初始设置
        updateCanvasSize();
        
        // 监听窗口大小变化
        window.addEventListener('resize', updateCanvasSize);
    }
    
    // 创建游戏控制器
    const game = new GameController();
    
    // 初始化游戏
    game.init({ mode: gameMode, roomId: roomId });
    
    // 暴露到全局(方便调试)
    window.game = game;
    
    // 确保ruleConfig可以被GameRules访问
    if (game.ruleConfig) {
        window.game.ruleConfig = game.ruleConfig;
        console.log('✅ 规则配置已绑定到全局');
    }
    
    // 显示欢迎信息
    showWelcomeMessage(gameMode, roomId);
});

/**
 * 显示欢迎信息
 */
function showWelcomeMessage(mode, roomId) {
    if (mode === 'local') {
        console.log('游戏模式: 匈汉象棋 - 单机双人对战');
        setTimeout(() => {
            console.log('点击棋子开始游戏!');
        }, 1000);
    } else if (mode === 'online') {
        console.log(`游戏模式: 匈汉象棋 - 联机对战`);
        console.log(`房间号: ${roomId}`);
        setTimeout(() => {
            console.log('正在连接服务器...');
        }, 1000);
    }
}


