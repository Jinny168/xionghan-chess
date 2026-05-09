/**
 * 棋盘渲染器 - 使用Canvas绘制棋盘和棋子
 */

class ChessBoardRenderer {
    constructor(canvas, traditionalMode = false) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.traditionalMode = traditionalMode;
        
        // 棋盘主题配置
        this.boardTheme = 'classic'; // 默认经典木纹
        this.pieceStyle = 'traditional'; // 默认传统书法
        
        // 主题配置
        this.themeConfig = {
            classic: {
                background: '#f9e8c4',
                gridColor: '#8b4513',
                lineColor: '#6d3c11',
                textColor: '#8b4513',
                textureColor: '#d4b896'
            },
            green: {
                background: '#e8f5e8',
                gridColor: '#2d5016',
                lineColor: '#3a6b1e',
                textColor: '#2d5016',
                textureColor: '#a8d8a8'
            },
            blue: {
                background: '#e8f4f8',
                gridColor: '#1a5276',
                lineColor: '#2471a3',
                textColor: '#1a5276',
                textureColor: '#a8d8e8'
            },
            purple: {
                background: '#f3e8f7',
                gridColor: '#6c3483',
                lineColor: '#7d3c98',
                textColor: '#6c3483',
                textureColor: '#d8a8e8'
            },
            dark: {
                background: '#2c2c2c',
                gridColor: '#555555',
                lineColor: '#666666',
                textColor: '#aaaaaa',
                textureColor: '#444444'
            }
        };
        
        // 边距配置
        this.marginLeft = 40;
        this.marginTop = 40;
        
        // 计算尺寸
        this.calculateDimensions();
        
        // 加载棋子图片
        this.pieceImages = {};
        this.imagesLoaded = false;
        this.loadPieceImages();
        
        // 高亮和提示
        this.highlighted = null;
        this.possibleMoves = [];
        this.capturablePositions = [];
    }
    
    /**
     * 设置棋盘主题
     */
    setBoardTheme(theme) {
        if (this.themeConfig[theme]) {
            this.boardTheme = theme;
            // 重新绘制棋盘
            if (window.game) {
                window.game.render();
            }
            console.log(`棋盘主题已切换为: ${theme}`);
        }
    }
    
    /**
     * 设置棋子样式
     */
    setPieceStyle(style) {
        console.log(`切换棋子样式: ${this.pieceStyle} -> ${style}`);
        
        // 如果样式相同，不需要重新加载
        if (this.pieceStyle === style) {
            console.log('样式未改变，跳过重新加载');
            return;
        }
        
        this.pieceStyle = style;
        
        // 清空之前的图片缓存
        this.pieceImages = {};
        this.imagesLoaded = false;
        
        // 重新加载棋子图片（加载完成后会自动重绘）
        this.loadPieceImages();
        
        console.log(`棋子样式已切换为: ${style}，等待图片加载...`);
    }
    
    /**
     * 加载棋子图片
     * 棋子名称使用拼音：hong(红)/hei(黑) + 棋子类型拼音
     */
    loadPieceImages() {
        console.log(`开始加载${this.pieceStyle}风格棋子图片...`);
        
        // 棋子图片文件名使用拼音命名：红方(hong)/黑方(hei) + 棋子类型
        const pieceNames = [
            'honghan', 'hongshi', 'hongxiang', 'hongche', 'hongma', 'hongpao', 'hongbing',
            'hongshe', 'honglei', 'hongwei', 'hongxun',
            'heihan', 'heishi', 'heixiang', 'heiche', 'heima', 'heipao', 'heibing',
            'heishe', 'heilei', 'heiwei', 'heixun'
        ];
        
        let loadedCount = 0;
        let errorCount = 0;
        const totalCount = pieceNames.length;
        
        // 使用时间戳绕过浏览器缓存
        const cacheBuster = Date.now();
        
        pieceNames.forEach(name => {
            const img = new Image();
            
            // 根据棋子样式选择不同目录
            let imagePath;
            if (this.pieceStyle === 'modern') {
                imagePath = `images/pieces/modern/${name}.png`;
            } else if (this.pieceStyle === 'cartoon') {
                imagePath = `images/pieces/cartoon/${name}.png`;
            } else {
                // traditional - 从traditional子目录加载
                imagePath = `images/pieces/traditional/${name}.png`;
            }
            
            // 添加缓存破坏参数
            const imageUrlWithCache = `${imagePath}?v=${cacheBuster}`;
            
            img.onload = () => {
                this.pieceImages[name] = img;
                loadedCount++;
                
                if (loadedCount + errorCount === totalCount) {
                    this.imagesLoaded = true;
                    console.log(`✅ ${this.pieceStyle}风格棋子图片加载完成: ${loadedCount}/${totalCount}成功, ${errorCount}失败`);
                    
                    // 所有图片加载完成后，重绘棋盘
                    if (window.game && window.game.renderer) {
                        window.game.render();
                        console.log('棋盘已重绘');
                    }
                }
            };
            
            img.onerror = () => {
                errorCount++;
                console.error(`❌ 无法加载棋子图片: ${imagePath}`);
                
                if (loadedCount + errorCount === totalCount) {
                    this.imagesLoaded = true;
                    console.warn(`⚠️ ${this.pieceStyle}风格棋子图片部分加载失败: ${loadedCount}/${totalCount}成功, ${errorCount}失败`);
                    
                    // 即使有失败也要重绘
                    if (window.game && window.game.renderer) {
                        window.game.render();
                    }
                }
            };
            
            // 最后设置src，确保事件监听器已绑定
            img.src = imageUrlWithCache;
        });
    }
    
    /**
     * 获取棋子图片名称
     */
    getPieceImageName(piece) {
        // 根据棋子类型和颜色返回对应的图片文件名
        const colorPrefix = piece.color === 'red' ? 'hong' : 'hei';
        
        // 棋子类型映射 - 使用棋子类名而不是显示名称
        const typeMap = {
            // 传统象棋
            '汉': 'han', '汗': 'han', '漢': 'han',
            '仕': 'shi', '士': 'shi',
            '相': 'xiang', '象': 'xiang',
            '车': 'che', '車': 'che', '俥': 'che',
            '马': 'ma', '馬': 'ma', '傌': 'ma',
            '炮': 'pao', '砲': 'pao',
            '兵': 'bing', '卒': 'bing',
            // 匈汉象棋特殊棋子
            '射': 'she', '䠶': 'she',
            '檑': 'lei', '礌': 'lei',
            '尉': 'wei', '衛': 'wei',
            '巡': 'xun', '廵': 'xun'
        };
        
        const typeName = typeMap[piece.name];
        if (!typeName) {
            console.warn(`⚠️ 未找到棋子类型映射: ${piece.name} (${piece.color})`);
            return null;
        }
        
        return `${colorPrefix}${typeName}`;
    }
    
    /**
     * 绘制单个棋子（使用图片）- 自适应棋盘格子尺寸
     * 
     * 根据天天象棋设计规范：
     * - 棋子直径 = 棋盘格子尺寸 × 80%-85%
     * - 本实现采用85%的比例，确保棋子清晰可见且不会过于拥挤
     * - 投影效果也随棋子尺寸动态调整，保持视觉一致性
     */
    drawPiece(piece) {
        const ctx = this.ctx;
        const x = this.marginLeft + piece.col * this.gridSize;
        const y = this.marginTop + piece.row * this.gridSize;
        
        // ===== 动态计算棋子尺寸 =====
        // 天天象棋标准：棋子直径占格子尺寸的80%-85%
        // 选择85%以获得更好的视觉效果和可读性
        const PIECE_SCALE = 0.85; // 棋子占格子的比例（85%）
        const pieceSize = this.gridSize * PIECE_SCALE;
        
        const imageName = this.getPieceImageName(piece);
        if (!imageName) {
            console.error(`无法获取棋子图片名称: ${piece.name} (${piece.color}) at (${piece.row}, ${piece.col})`);
            return;
        }
        
        const img = this.pieceImages[imageName];
        
        if (img && img.complete) {
            // ===== 投影效果（增强立体感）=====
            // 投影参数根据棋子尺寸动态计算，保持比例一致性
            ctx.save();
            
            // 投影模糊度：棋子尺寸的8%，营造柔和的阴影效果
            const shadowBlur = pieceSize * 0.08;
            // 投影偏移：棋子尺寸的6%，模拟光源从左上角照射的效果
            const shadowOffset = pieceSize * 0.06;
            
            ctx.shadowColor = 'rgba(0, 0, 0, 0.3)'; // 半透明黑色阴影
            ctx.shadowBlur = shadowBlur;
            ctx.shadowOffsetX = shadowOffset;
            ctx.shadowOffsetY = shadowOffset;
            
            // 绘制棋子图片（居中对齐）
            ctx.drawImage(img, x - pieceSize/2, y - pieceSize/2, pieceSize, pieceSize);
            
            // 恢复Canvas状态（清除阴影设置）
            ctx.restore();
        } else {
            // 图片尚未加载完成时，静默跳过，避免控制台刷屏
            // 这通常只在首次加载时发生，图片加载完成后会自动重绘
        }
    }
    
    /**
     * 计算棋盘尺寸
     */
    calculateDimensions() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        if (this.traditionalMode) {
            // 传统象棋：9x10棋盘，宽高比9:10
            this.boardWidth = width - 2 * this.marginLeft;
            this.boardHeight = this.boardWidth * 10 / 9;
            this.gridSize = this.boardWidth / 8;
        } else {
            // 匈汉象棋：13x13棋盘，正方形
            this.boardWidth = width - 2 * this.marginLeft;
            this.boardHeight = this.boardWidth; // 正方形棋盘
            this.gridSize = this.boardWidth / 12;
        }
        
        // 确保不超出画布
        if (this.boardHeight > height - 2 * this.marginTop) {
            this.boardHeight = height - 2 * this.marginTop;
            if (this.traditionalMode) {
                // 根据高度重新计算宽度，保持9:10比例
                this.boardWidth = this.boardHeight * 9 / 10;
                this.gridSize = this.boardWidth / 8;
            } else {
                // 正方形棋盘，宽高相等
                this.boardWidth = this.boardHeight; // 正方形棋盘，宽高相等
                this.gridSize = this.boardWidth / 12;
            }
        }
    }
    
    /**
     * 清空画布
     */
    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    /**
     * 绘制整个棋盘
     */
    draw(pieces, gameState) {
        this.clear();
        this.drawBoard();
        this.drawBingSpawnPoints(gameState);
        this.drawPossibleMoves();
        this.drawCapturablePositions();
        this.drawPieces(pieces);
        this.drawLastMove(gameState);
        this.drawHighlight();
    }
    
    /**
     * 渲染棋盘（与draw方法相同，提供兼容性）
     */
    render(pieces, lastMove) {
        console.log('ChessBoardRenderer.render 被调用:', {
            piecesCount: pieces ? pieces.length : 0,
            hasLastMove: !!lastMove,
            traditionalMode: this.traditionalMode,
            canvasSize: `${this.canvas.width}x${this.canvas.height}`,
            gridSize: this.gridSize
        });
        
        // 将lastMove转换为gameState格式
        const gameState = lastMove ? { lastMove } : null;
        this.draw(pieces, gameState);
    }
    
    /**
     * 绘制棋盘 - 根据主题配置动态生成
     */
    drawBoard() {
        const ctx = this.ctx;
        const theme = this.themeConfig[this.boardTheme];
        
        // 背景 - 根据主题配置
        const extraBottom = this.gridSize * 0.8; // 额外底部空间
        ctx.fillStyle = theme.background;
        ctx.fillRect(
            this.marginLeft - 20,
            this.marginTop - 40,
            this.boardWidth + 40,
            this.boardHeight + 40 + extraBottom
        );
        
        // 添加纹理效果（根据主题）
        ctx.save();
        ctx.globalAlpha = 0.08;
        ctx.strokeStyle = theme.textureColor;
        ctx.lineWidth = 1;
        for (let i = 0; i < this.boardWidth; i += 8) {
            ctx.beginPath();
            ctx.moveTo(this.marginLeft + i, this.marginTop - 20);
            ctx.lineTo(this.marginLeft + i, this.marginTop + this.boardHeight + extraBottom + 20);
            ctx.stroke();
        }
        ctx.restore();
        
        // 外边框 - 根据主题配置
        ctx.strokeStyle = theme.gridColor;
        ctx.lineWidth = 3;
        ctx.strokeRect(
            this.marginLeft,
            this.marginTop,
            this.boardWidth,
            this.boardHeight
        );
        
        if (this.traditionalMode) {
            this.drawTraditionalGrid(theme);
        } else {
            this.drawXionghanGrid(theme);
        }
    }
    
    /**
     * 绘制传统象棋网格
     */
    drawTraditionalGrid(theme) {
        const ctx = this.ctx;
        ctx.strokeStyle = theme.gridColor;
        ctx.lineWidth = 1;
        
        // 横线 (10条)
        for (let i = 0; i < 10; i++) {
            const y = this.marginTop + i * this.gridSize;
            ctx.beginPath();
            ctx.moveTo(this.marginLeft, y);
            ctx.lineTo(this.marginLeft + this.boardWidth, y);
            ctx.stroke();
        }
        
        // 竖线 (9条)
        for (let i = 0; i < 9; i++) {
            const x = this.marginLeft + i * this.gridSize;
            ctx.beginPath();
            ctx.moveTo(x, this.marginTop);
            ctx.lineTo(x, this.marginTop + this.boardHeight);
            ctx.stroke();
        }
        
        // 九宫格斜线
        // 黑方九宫
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 3 * this.gridSize, this.marginTop);
        ctx.lineTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 2 * this.gridSize);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 5 * this.gridSize, this.marginTop);
        ctx.lineTo(this.marginLeft + 3 * this.gridSize, this.marginTop + 2 * this.gridSize);
        ctx.stroke();
        
        // 红方九宫
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 3 * this.gridSize, this.marginTop + 7 * this.gridSize);
        ctx.lineTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 9 * this.gridSize);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 7 * this.gridSize);
        ctx.lineTo(this.marginLeft + 3 * this.gridSize, this.marginTop + 9 * this.gridSize);
        ctx.stroke();
        
        // 楚河汉界
        const fontFamily = 'KaiTi, STKaiti, SimSun, serif';
        ctx.font = `bold ${this.gridSize * 0.6}px ${fontFamily}`;
        ctx.fillStyle = theme.textColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const riverY = this.marginTop + 4.5 * this.gridSize;
        ctx.fillText('楚 河', this.marginLeft + 2 * this.gridSize, riverY);
        ctx.fillText('漢 界', this.marginLeft + 6 * this.gridSize, riverY);
    }
    
    /**
     * 绘制匈汉象棋网格 - 参考天天象棋风格
     */
    drawXionghanGrid(theme) {
        const ctx = this.ctx;
        ctx.strokeStyle = theme.lineColor;
        ctx.lineWidth = 1;
        
        // 横线 (13条)，但第6行（楚河汉界）不绘制完整线
        for (let i = 0; i < 13; i++) {
            if (i === 6) continue; // 跳过第6行
            const y = this.marginTop + i * this.gridSize;
            ctx.beginPath();
            ctx.moveTo(this.marginLeft, y);
            ctx.lineTo(this.marginLeft + this.boardWidth, y);
            ctx.stroke();
        }
        
        // 竖线，但在长城阴山区域（第6行）断开
        for (let i = 0; i < 13; i++) {
            const x = this.marginLeft + i * this.gridSize;
            // 上半部分（0-5行）
            ctx.beginPath();
            ctx.moveTo(x, this.marginTop);
            ctx.lineTo(x, this.marginTop + 5 * this.gridSize);
            ctx.stroke();
            
            // 下半部分（7-12行）
            ctx.beginPath();
            ctx.moveTo(x, this.marginTop + 7 * this.gridSize);
            ctx.lineTo(x, this.marginTop + 12 * this.gridSize);
            ctx.stroke();
        }
        
        // 绘制第6行的特殊点位标记
        const separatorY = this.marginTop + 6 * this.gridSize;
        for (let col = 0; col < 13; col++) {
            const x = this.marginLeft + col * this.gridSize;
            const lineLength = 8;
            
            // 绘制横向标记 - 边缘位置只绘制内部半边
            if (col === 0) {
                // 左边缘：只绘制右半边
                ctx.beginPath();
                ctx.moveTo(x, separatorY);
                ctx.lineTo(x + lineLength, separatorY);
                ctx.stroke();
            } else if (col === 12) {
                // 右边缘：只绘制左半边
                ctx.beginPath();
                ctx.moveTo(x - lineLength, separatorY);
                ctx.lineTo(x, separatorY);
                ctx.stroke();
            } else {
                // 中间位置：绘制完整横线
                ctx.beginPath();
                ctx.moveTo(x - lineLength, separatorY);
                ctx.lineTo(x + lineLength, separatorY);
                ctx.stroke();
            }
            
            // 纵向短线（非边缘列）
            if (col > 0 && col < 12) {
                ctx.beginPath();
                ctx.moveTo(x, separatorY - lineLength);
                ctx.lineTo(x, separatorY + lineLength);
                ctx.stroke();
            }
        }
        
        // 九宫格
        // 黑方九宫 (1-3行, 5-7列)
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 1 * this.gridSize);
        ctx.lineTo(this.marginLeft + 7 * this.gridSize, this.marginTop + 3 * this.gridSize);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 7 * this.gridSize, this.marginTop + 1 * this.gridSize);
        ctx.lineTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 3 * this.gridSize);
        ctx.stroke();
        
        // 红方九宫 (9-11行, 5-7列)
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 9 * this.gridSize);
        ctx.lineTo(this.marginLeft + 7 * this.gridSize, this.marginTop + 11 * this.gridSize);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.marginLeft + 7 * this.gridSize, this.marginTop + 9 * this.gridSize);
        ctx.lineTo(this.marginLeft + 5 * this.gridSize, this.marginTop + 11 * this.gridSize);
        ctx.stroke();
        
        // 绘制“长城阴山” - 楷体，深棕色，不粗体，字号为格子的55%
        const fontFamily = 'KaiTi, STKaiti, SimSun, serif';
        ctx.font = `${this.gridSize * 0.55}px ${fontFamily}`;
        ctx.fillStyle = theme.textColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        ctx.fillText('长 城', this.marginLeft + this.boardWidth/4, separatorY);
        ctx.fillText('阴 山', this.marginLeft + 3*this.boardWidth/4, separatorY);
        
        // 绘制兵、炮位置标记
        this.drawPositionMarks(ctx);
        
        // 绘制星点标记（射的移动限制点）
        this.drawStarPoints(ctx);
        
        // 绘制列标识
        this.drawColumnLabels(ctx);
    }
    
    /**
     * 绘制棋子
     */
    drawPieces(pieces) {
        console.log('绘制棋子:', pieces ? pieces.length : 0, '个');
        if (pieces && pieces.length > 0) {
            console.log('前3个棋子:', pieces.slice(0, 3).map(p => ({
                name: p.name,
                color: p.color,
                row: p.row,
                col: p.col
            })));
        }
        
        pieces.forEach(piece => {
            this.drawPiece(piece);
        });
    }
    
    /**
     * 绘制可能移动位置
     */
    drawPossibleMoves() {
        const ctx = this.ctx;
        ctx.fillStyle = 'rgba(50, 205, 50, 0.6)';
        
        this.possibleMoves.forEach(pos => {
            const x = this.marginLeft + pos.col * this.gridSize;
            const y = this.marginTop + pos.row * this.gridSize;
            const radius = this.gridSize * 0.2;
            
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
        });
    }
    
    /**
     * 绘制可吃子位置
     */
    drawCapturablePositions() {
        const ctx = this.ctx;
        ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
        ctx.lineWidth = 3;
        
        this.capturablePositions.forEach(pos => {
            const x = this.marginLeft + pos.col * this.gridSize;
            const y = this.marginTop + pos.row * this.gridSize;
            const size = this.gridSize * 0.35;
            
            // 绘制X标记
            ctx.beginPath();
            ctx.moveTo(x - size, y - size);
            ctx.lineTo(x + size, y + size);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.moveTo(x + size, y - size);
            ctx.lineTo(x - size, y + size);
            ctx.stroke();
        });
    }
    
    /**
     * 绘制上一步移动
     */
    drawLastMove(gameState) {
        if (!gameState || !gameState.lastMove) return;
        
        const ctx = this.ctx;
        const [fromRow, fromCol, toRow, toCol] = gameState.lastMove;
        
        ctx.strokeStyle = 'rgba(255, 255, 0, 0.6)';
        ctx.lineWidth = 3;
        
        // 起点
        const fromX = this.marginLeft + fromCol * this.gridSize;
        const fromY = this.marginTop + fromRow * this.gridSize;
        ctx.beginPath();
        ctx.arc(fromX, fromY, this.gridSize * 0.45, 0, Math.PI * 2);
        ctx.stroke();
        
        // 终点
        const toX = this.marginLeft + toCol * this.gridSize;
        const toY = this.marginTop + toRow * this.gridSize;
        ctx.beginPath();
        ctx.arc(toX, toY, this.gridSize * 0.45, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    /**
     * 绘制兵出生点标记（空的出生点显示半透明圆圈）
     */
    drawBingSpawnPoints(gameState) {
        if (!gameState || !gameState.bingSpawnPoints) return;
        
        // 检查是否启用了兵复活规则
        const ruleConfig = window.GameRules ? window.GameRules.getRuleConfig() : {};
        if (!ruleConfig.pawnResurrection) return;
        
        const ctx = this.ctx;
        const currentTurn = gameState.playerTurn;
        
        // 获取当前玩家的出生点
        const spawnPoints = gameState.bingSpawnPoints[currentTurn];
        if (!spawnPoints) return;
        
        // 遍历所有出生点，如果为空则显示标记
        spawnPoints.forEach(([row, col]) => {
            // 检查该位置是否有棋子
            const piece = gameState.getPieceAt(row, col);
            if (!piece) {
                // 空位置，绘制半透明圆圈提示
                const x = this.marginLeft + col * this.gridSize;
                const y = this.marginTop + row * this.gridSize;
                
                ctx.save();
                ctx.globalAlpha = 0.3;
                ctx.strokeStyle = currentTurn === 'red' ? '#ff0000' : '#000000';
                ctx.lineWidth = 2;
                ctx.setLineDash([5, 5]); // 虚线
                ctx.beginPath();
                ctx.arc(x, y, this.gridSize * 0.35, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }
        });
    }
    
    /**
     * 绘制高亮
     */
    drawHighlight() {
        if (!this.highlighted) return;
        
        const ctx = this.ctx;
        const [row, col] = this.highlighted;
        const x = this.marginLeft + col * this.gridSize;
        const y = this.marginTop + row * this.gridSize;
        
        ctx.strokeStyle = 'rgba(255, 255, 0, 0.8)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(x, y, this.gridSize * 0.45, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    /**
     * 获取鼠标点击的网格位置
     */
    getGridPosition(mouseX, mouseY) {
        const col = Math.round((mouseX - this.marginLeft) / this.gridSize);
        const row = Math.round((mouseY - this.marginTop) / this.gridSize);
        
        const maxRow = this.traditionalMode ? 9 : 12;
        const maxCol = this.traditionalMode ? 8 : 12;
        
        if (row >= 0 && row <= maxRow && col >= 0 && col <= maxCol) {
            return { row, col };
        }
        
        return null;
    }
    
    /**
     * 设置高亮
     */
    highlightPosition(row, col) {
        this.highlighted = [row, col];
    }
    
    /**
     * 清除高亮
     */
    clearHighlights() {
        this.highlighted = null;
        this.possibleMoves = [];
        this.capturablePositions = [];
    }
    
    /**
     * 设置可能移动
     */
    setPossibleMoves(moves) {
        this.possibleMoves = moves;
    }
    
    /**
     * 设置可吃子位置
     */
    setCapturablePositions(positions) {
        this.capturablePositions = positions;
    }
    
    /**
     * 绘制星点标记（射的移动限制点）
     * 星点是坐标为3的倍数的位置：(0,0), (0,3), (0,6), (0,9), (3,0), (3,3)等
     * 注意：不标注棋盘边缘的星点（row=0, row=12, col=0, col=12）
     */
    drawStarPoints(ctx) {
        // 星点颜色 - 使用淡红色，与棋盘背景形成对比但不突兀
        ctx.fillStyle = 'rgba(180, 30, 30, 0.4)';
        
        // 遍历所有星点（坐标为3的倍数），但排除边缘
        for (let row = 3; row <= 9; row += 3) {  // 从3开始，到9结束，排除0和12
            for (let col = 3; col <= 9; col += 3) {  // 从3开始，到9结束，排除0和12
                const x = this.marginLeft + col * this.gridSize;
                const y = this.marginTop + row * this.gridSize;
                
                // 绘制小圆点作为星点标记
                const radius = this.gridSize * 0.08; // 半径为格子尺寸的8%
                ctx.beginPath();
                ctx.arc(x, y, radius, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
    
    /**
     * 绘制兵、炮位置标记
     */
    drawPositionMarks(ctx) {
        const positions = [
            // 黑方兵位置 (第4行)
            [4, 0], [4, 2], [4, 4], [4, 6], [4, 8], [4, 10], [4, 12],
            // 黑方炮位置 (第3行)
            [3, 1], [3, 11],
            // 红方兵位置 (第8行)
            [8, 0], [8, 2], [8, 4], [8, 6], [8, 8], [8, 10], [8, 12],
            // 红方炮位置 (第9行)
            [9, 1], [9, 11]
        ];
        
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        
        positions.forEach(([row, col]) => {
            const x = this.marginLeft + col * this.gridSize;
            const y = this.marginTop + row * this.gridSize;
            this.drawPositionMark(ctx, x, y);
        });
    }
    
    /**
     * 绘制单个位置标记（四个角）
     */
    drawPositionMark(ctx, x, y) {
        const offset = this.gridSize * 0.15;
        const lineLength = this.gridSize * 0.25;
        
        // 左上
        ctx.beginPath();
        ctx.moveTo(x - offset, y - offset);
        ctx.lineTo(x - offset, y - offset - lineLength);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x - offset, y - offset);
        ctx.lineTo(x - offset - lineLength, y - offset);
        ctx.stroke();
        
        // 右上
        ctx.beginPath();
        ctx.moveTo(x + offset, y - offset);
        ctx.lineTo(x + offset, y - offset - lineLength);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x + offset, y - offset);
        ctx.lineTo(x + offset + lineLength, y - offset);
        ctx.stroke();
        
        // 左下
        ctx.beginPath();
        ctx.moveTo(x - offset, y + offset);
        ctx.lineTo(x - offset, y + offset + lineLength);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x - offset, y + offset);
        ctx.lineTo(x - offset - lineLength, y + offset);
        ctx.stroke();
        
        // 右下
        ctx.beginPath();
        ctx.moveTo(x + offset, y + offset);
        ctx.lineTo(x + offset, y + offset + lineLength);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x + offset, y + offset);
        ctx.lineTo(x + offset + lineLength, y + offset);
        ctx.stroke();
    }
    
    /**
     * 绘制列标识 - 去除白色背景框，使用简洁样式
     */
    drawColumnLabels(ctx) {
        const redLabels = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"];
        const blackLabels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"];
        
        const fontFamily = 'KaiTi, STKaiti, SimSun, serif';
        const labelFontSize = Math.floor(this.gridSize * 0.4);
        
        // 绘制红方（下方）列标识 - 从右到左
        ctx.font = `${labelFontSize}px ${fontFamily}`;
        ctx.fillStyle = '#b41e1e'; // 正红色
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        
        for (let i = 0; i < 13; i++) {
            const colIndex = 12 - i; // 从右到左
            const x = this.marginLeft + i * this.gridSize;
            const y = this.marginTop + this.boardHeight + 10;
            
            ctx.fillText(redLabels[colIndex], x, y);
        }
        
        // 绘制黑方（上方）列标识 - 从右到左
        ctx.fillStyle = '#2d2d2d'; // 深黑色，避免纯黑
        ctx.textBaseline = 'bottom';
        
        for (let i = 0; i < 13; i++) {
            const colIndex = 12 - i; // 从右到左
            const x = this.marginLeft + i * this.gridSize;
            const y = this.marginTop - 10;
            
            ctx.fillText(blackLabels[colIndex], x, y);
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.ChessBoardRenderer = ChessBoardRenderer;
}
