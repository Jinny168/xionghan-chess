/**
 * 游戏规则引擎
 * 负责验证棋子移动合法性和计算可能移动
 */

class GameRules {
    /**
     * 获取游戏规则配置
     * @returns {Object} 规则配置对象
     */
    static getRuleConfig() {
        // 如果window中有ruleConfig，则使用它
        if (window.game && window.game.ruleConfig) {
            return window.game.ruleConfig.getAll();
        }
        // 否则返回默认配置
        return {
            horseStraightThree: false,
            advisorOutPalace: false,
            elephantCrossRiver: false,
            kingOutPalace: false,
            kingPalaceEightDirection: false,  // 默认关闭，等同传统将帅
            kingKeepEightDirection: false,
            pawnFastMove: true,         // 默认开启，兵可以快速移动
            pawnResurrection: false     // 默认关闭，兵不能复活
        };
    }
    
    /**
     * 获取指定位置的棋子
     * @param {Array} pieces - 棋子列表
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @returns {Object|null} 棋子对象，如果该位置没有棋子则返回null
     */
    static getPieceAt(pieces, row, col) {
        return pieces.find(p => p.row === row && p.col === col) || null;
    }
    
    /**
     * 检查位置是否在棋盘范围内（匈汉象棋13x13棋盘）
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @returns {boolean} 位置是否在棋盘内
     */
    static isPositionOnBoard(row, col) {
        return row >= 0 && row < 13 && col >= 0 && col < 13;
    }
    
    /**
     * 检查斜向移动是否存在夹逼
     * @param {number} checkRow - 要检查的行
     * @param {number} checkCol - 要检查的列
     * @param {number} stepRow - 移动方向的行步长(1或-1)
     * @param {number} stepCol - 移动方向的列步长(1或-1)
     * @param {Array} pieces - 棋子列表
     * @returns {boolean} - 如果存在夹逼返回true
     */
    static hasPinch(checkRow, checkCol, stepRow, stepCol, pieces) {
        // 夹逼方向：与移动方向相关的两个侧向方向
        const crossDirs = [[0, stepCol], [stepRow, 0]];
        let adjacentPieces = 0;
        
        for (const [crossDr, crossDc] of crossDirs) {
            const adjRow = checkRow + crossDr;
            const adjCol = checkCol + crossDc;
            if (this.isPositionOnBoard(adjRow, adjCol)) {
                if (this.getPieceAt(pieces, adjRow, adjCol)) {
                    adjacentPieces++;
                }
            }
        }
        
        // 如果在移动方向的两个侧向位置都有棋子，则形成夹逼
        return adjacentPieces === 2;
    }
    
    /**
     * 检查移动是否合法（主入口函数）
     * @param {Array} pieces - 棋盘上所有棋子
     * @param {Object} piece - 要移动的棋子对象
     * @param {number} fromRow - 起始行
     * @param {number} fromCol - 起始列
     * @param {number} toRow - 目标行
     * @param {number} toCol - 目标列
     * @returns {boolean} 移动是否合法
     */
    static isValidMove(pieces, piece, fromRow, fromCol, toRow, toCol) {
        // 基本检查
        if (piece.row !== fromRow || piece.col !== fromCol) {
            return false;
        }
        
        if (!this.isPositionOnBoard(toRow, toCol)) {
            return false;
        }
        
        // 检查目标位置是否有己方棋子
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        if (targetPiece && targetPiece.color === piece.color) {
            return false;
        }
        
        // 检查将帅照面限制：任何棋子移动后如果导致将帅照面，则不允许移动
        if (this.wouldCauseKingsFacing(pieces, piece.color, fromRow, fromCol, toRow, toCol)) {
            return false;
        }
        
        // 根据棋子类型检查移动规则
        if (piece instanceof Ju) {
            return this.isValidJuMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Ma) {
            return this.isValidMaMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Xiang) {
            return this.isValidXiangMove(pieces, piece.color, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Shi) {
            return this.isValidShiMove(pieces, piece.color, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Han) {
            return this.isValidKingMove(pieces, piece.color, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Pao) {
            return this.isValidPaoMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Bing) {
            return this.isValidPawnMove(pieces, piece.color, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof She) {
            return this.isValidSheMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Lei) {
            return this.isValidLeiMove(pieces, fromRow, fromCol, toRow, toCol);
        // 已移除: Jia, Ci, Dun, Wei, Xun
        }
        
        return false;
    }
    
    /**
     * 车的移动规则：只能横向或纵向直线移动，路径上不能有阻挡
     * @param {Array} pieces - 棋盘上所有棋子
     * @param {number} fromRow - 起始行
     * @param {number} fromCol - 起始列
     * @param {number} toRow - 目标行
     * @param {number} toCol - 目标列
     * @returns {boolean} 移动是否合法
     */
    static isValidJuMove(pieces, fromRow, fromCol, toRow, toCol) {
        // 只能横向或纵向移动
        if (fromRow !== toRow && fromCol !== toCol) {
            return false;
        }
        
        // 检查路径上是否有其他棋子
        if (fromRow === toRow) {
            const start = Math.min(fromCol, toCol) + 1;
            const end = Math.max(fromCol, toCol);
            for (let col = start; col < end; col++) {
                if (this.getPieceAt(pieces, fromRow, col)) {
                    return false;
                }
            }
        } else {
            const start = Math.min(fromRow, toRow) + 1;
            const end = Math.max(fromRow, toRow);
            for (let row = start; row < end; row++) {
                if (this.getPieceAt(pieces, row, fromCol)) {
                    return false;
                }
            }
        }
        
        return true;
    }
    
    /**
     * 马的移动规则：日字走法 + 直三走法（可配置），检查蹩马腿
     * @param {Array} pieces - 棋盘上所有棋子
     * @param {number} fromRow - 起始行
     * @param {number} fromCol - 起始列
     * @param {number} toRow - 目标行
     * @param {number} toCol - 目标列
     * @returns {boolean} 移动是否合法
     */
    static isValidMaMove(pieces, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 获取规则配置
        const config = this.getRuleConfig();
        
        // 日字走法
        const isNormalMove = (absRowDiff === 2 && absColDiff === 1) || (absRowDiff === 1 && absColDiff === 2);
        
        // 直三走法：横向或纵向走3格（需要配置开启）
        const isStraightThree = config.horseStraightThree && 
                                ((absRowDiff === 3 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 3));
        
        if (!isNormalMove && !isStraightThree) {
            return false;
        }
        
        // 检查蹩马腿（日字走法）
        if (isNormalMove) {
            if (absRowDiff === 2) {
                const blockRow = fromRow + (rowDiff > 0 ? 1 : -1);
                if (this.getPieceAt(pieces, blockRow, fromCol)) {
                    return false;
                }
            } else if (absColDiff === 2) {
                const blockCol = fromCol + (colDiff > 0 ? 1 : -1);
                if (this.getPieceAt(pieces, fromRow, blockCol)) {
                    return false;
                }
            }
        }
        
        // 直三走法：检查路径上的阻挡
        if (isStraightThree) {
            const stepRow = rowDiff === 0 ? 0 : (rowDiff > 0 ? 1 : -1);
            const stepCol = colDiff === 0 ? 0 : (colDiff > 0 ? 1 : -1);
            
            // 检查前两个位置是否有阻挡
            for (let i = 1; i <= 2; i++) {
                const checkRow = fromRow + i * stepRow;
                const checkCol = fromCol + i * stepCol;
                if (this.getPieceAt(pieces, checkRow, checkCol)) {
                    return false; // 有阻挡
                }
            }
        }
        
        return true;
    }
    
    /**
     * 相/象的移动规则（匈汉象棋增强版，可配置）
     * 1. 基本移动：田字走法（斜向两格），遵循塞象眼规则
     * 2. 越过长城后：获得前后左右隔一格移动吃子的能力（仍遵循塞象眼）
     * 3. 斜向移动时不能有"夹逼"
     * 4. 可配置是否允许跨越长城（默认不允许）
     */
    static isValidXiangMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 获取规则配置
        const config = this.getRuleConfig();
        
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        
        // 检查是否已越过长城（长城在第6行）
        // 如果配置允许跨河，则始终认为已越过长城
        const hasCrossedGreatWall = config.elephantCrossRiver || 
                                    (color === 'red' && fromRow <= 5) || 
                                    (color === 'black' && fromRow >= 7);
        
        // 如果已越过长城，检查是否是隔一格直线移动（吃子或移动到空位）
        if (hasCrossedGreatWall) {
            if ((absRowDiff === 2 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 2)) {
                // 检查中间是否有棋子（塞象眼）
                const midRow = fromRow + rowDiff / 2;
                const midCol = fromCol + colDiff / 2;
                if (this.getPieceAt(pieces, midRow, midCol)) {
                    return false; // 中间有棋子，不能移动
                }
                
                // 如果是吃子，目标必须是敌方棋子
                if (targetPiece && targetPiece.color === color) {
                    return false; // 不能吃己方棋子
                }
                
                return true; // 可以吃子或移动到空位
            }
        }
        
        // 基本移动：田字走法（斜向两格）
        if (absRowDiff === 2 && absColDiff === 2) {
            // 检查塞象眼
            const centerRow = (fromRow + toRow) / 2;
            const centerCol = (fromCol + toCol) / 2;
            if (this.getPieceAt(pieces, centerRow, centerCol)) {
                return false; // 塞象眼，不能移动
            }
            
            // 检查夹逼：在中心位置检查
            const stepRow = rowDiff > 0 ? 1 : -1;
            const stepCol = colDiff > 0 ? 1 : -1;
            if (this.hasPinch(centerRow, centerCol, stepRow, stepCol, pieces)) {
                return false; // 存在夹逼，不能移动
            }
            
            return true;
        }
        
        return false;
    }
    
    /**
     * 士/仕的移动规则(匈汉象棋增强版，可配置)
     * 1. 在九宫内:只能斜向一格移动
     * 2. 出了九宫:保留斜走能力,同时获得前后左右移动一格的能力(可控制周围8格)
     * 3. 斜向移动时不能有"夹逼"
     * 4. 可配置是否允许出九宫（默认不允许）
     */
    static isValidShiMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 获取规则配置
        const config = this.getRuleConfig();
        
        // 检查目标位置是否在棋盘范围内
        if (!this.isPositionOnBoard(toRow, toCol)) {
            return false;
        }
        
        // 检查目标位置是否有己方棋子
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        if (targetPiece && targetPiece.color === color) {
            return false;
        }
        
        // 匈汉象棋九宫位置（判断起始位置）
        const isInPalace = (color === 'red' && fromRow >= 9 && fromRow <= 11 && fromCol >= 5 && fromCol <= 7) ||
                          (color === 'black' && fromRow >= 1 && fromRow <= 3 && fromCol >= 5 && fromCol <= 7);
        
        // 如果配置允许出九宫，则移除九宫限制
        if (config.advisorOutPalace) {
            // 可以移动到任意位置，但必须是一格
            if (Math.max(absRowDiff, absColDiff) !== 1) {
                return false; // 必须走一格
            }
            
            if (absRowDiff === 1 && absColDiff === 1) {
                // 斜走：检查夹逼
                const stepRow = rowDiff > 0 ? 1 : -1;
                const stepCol = colDiff > 0 ? 1 : -1;
                // 在起点位置检查夹逼
                if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
                    return false; // 存在夹逼，不能移动
                }
                return true;
            } else if ((absRowDiff === 1 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 1)) {
                // 直走：不需要检查夹逼
                return true;
            }
            return false;
        }
        
        // 默认规则：受九宫限制
        if (isInPalace) {
            // 在九宫内:只能斜走一格
            if (absRowDiff === 1 && absColDiff === 1) {
                // 检查夹逼：虽然只移动1格，但仍需检查起点位置的夹逼
                const stepRow = rowDiff > 0 ? 1 : -1;
                const stepCol = colDiff > 0 ? 1 : -1;
                // 在起点位置检查夹逼
                if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
                    return false; // 存在夹逼，不能移动
                }
                return true;
            }
            return false; // 在九宫内不能直走
        } else {
            // 出了九宫:可以斜走或直走一格（控制周围8格）
            if (Math.max(absRowDiff, absColDiff) !== 1) {
                return false; // 必须走一格
            }
            
            if (absRowDiff === 1 && absColDiff === 1) {
                // 斜走：检查夹逼
                const stepRow = rowDiff > 0 ? 1 : -1;
                const stepCol = colDiff > 0 ? 1 : -1;
                // 在起点位置检查夹逼
                if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
                    return false; // 存在夹逼，不能移动
                }
                return true;
            } else if ((absRowDiff === 1 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 1)) {
                // 直走：不需要检查夹逼
                return true;
            }
            return false;
        }
    }
    
    /**
     * 将/帅/汉/汗的移动规则（匈汉象棋，可配置）
     * 1. 在九宫内：默认可以前后左右斜向移动一格（8方向），可配置为只能直线移动（4方向）
     * 2. 出了九宫：默认只能直线移动一格（4方向：前后左右）
     * 3. 将帅对脸规则（禁止照面）
     * 4. 可配置是否允许出九宫（默认不允许）
     * 5. 可配置九宫内是否保持8方向能力（默认开启）
     * 6. 可配置出了九宫后是否保持8方向能力（默认不保持，即宫外4方向）
     */
    static isValidKingMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 获取规则配置
        const config = this.getRuleConfig();
        
        // 检查目标位置是否在棋盘范围内
        if (!this.isPositionOnBoard(toRow, toCol)) {
            return false;
        }
        
        // 检查目标位置是否有己方棋子
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        if (targetPiece && targetPiece.color === color) {
            return false;
        }
        
        // 匈汉象棋九宫位置（判断起始位置）
        const isInPalace = (color === 'red' && fromRow >= 9 && fromRow <= 11 && fromCol >= 5 && fromCol <= 7) ||
                          (color === 'black' && fromRow >= 1 && fromRow <= 3 && fromCol >= 5 && fromCol <= 7);
        
        // 如果配置允许出九宫
        if (config.kingOutPalace) {
            // 可以移动到任意位置，但必须是一格
            if (Math.max(absRowDiff, absColDiff) !== 1) {
                return false; // 必须走一格
            }
            
            // 判断是否应该保持8方向能力
            const keepEightDirection = isInPalace ? config.kingPalaceEightDirection : config.kingKeepEightDirection;
            
            // 如果在九宫内且配置要求8方向，或者在宫外且配置要求保持8方向，则允许斜向移动
            if (keepEightDirection) {
                // 允许8方向移动
                // 如果是斜向移动，检查夹逼
                if (absRowDiff === 1 && absColDiff === 1) {
                    const stepRow = rowDiff > 0 ? 1 : -1;
                    const stepCol = colDiff > 0 ? 1 : -1;
                    // 在起点位置检查夹逼
                    if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
                        return false; // 存在夹逼，不能移动
                    }
                }
            } else {
                // 不保持8方向，只能直线移动（4方向）
                if (!((absRowDiff === 1 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 1))) {
                    return false; // 只能直线移动一格
                }
            }
        } else {
            // 默认规则：受九宫限制
            // 根据起始位置应用不同的移动规则
            if (isInPalace) {
                // 在九宫内：根据配置决定是8方向还是4方向
                if (config.kingPalaceEightDirection) {
                    // 8方向模式：可以横竖斜走一格
                    if (Math.max(absRowDiff, absColDiff) !== 1) {
                        return false; // 必须走一格
                    }
                    
                    // 如果是斜向移动，检查夹逼
                    if (absRowDiff === 1 && absColDiff === 1) {
                        const stepRow = rowDiff > 0 ? 1 : -1;
                        const stepCol = colDiff > 0 ? 1 : -1;
                        // 在起点位置检查夹逼
                        if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
                            return false; // 存在夹逼，不能移动
                        }
                    }
                } else {
                    // 4方向模式：只能横竖走一格（类似传统将帅）
                    if (!((absRowDiff === 1 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 1))) {
                        return false; // 只能直线移动一格
                    }
                }
            } else {
                // 在九宫外：只能横竖走一格（4方向），失去斜走能力
                if (!((absRowDiff === 1 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 1))) {
                    return false; // 只能直线移动一格
                }
            }
        }
        
        // 汉/汗进入敌方九宫直接获胜（在移动合法的基础上）
        if (color === 'red') {
            // 红方汉进入黑方九宫(1-3行, 5-7列)获胜
            if (toRow >= 1 && toRow <= 3 && toCol >= 5 && toCol <= 7) {
                // 检查是否会导致将帅照面（送将）
                if (this.wouldCauseKingsFacing(pieces, color, fromRow, fromCol, toRow, toCol)) {
                    return false; // 不能送将
                }
                return true;
            }
        } else {
            // 黑方汗进入红方九宫(9-11行, 5-7列)获胜
            if (toRow >= 9 && toRow <= 11 && toCol >= 5 && toCol <= 7) {
                // 检查是否会导致将帅照面（送将）
                if (this.wouldCauseKingsFacing(pieces, color, fromRow, fromCol, toRow, toCol)) {
                    return false; // 不能送将
                }
                return true;
            }
        }
        
        // 将帅对脸规则（禁止照面）
        // 检查移动后是否会导致将帅照面
        if (this.wouldCauseKingsFacing(pieces, color, fromRow, fromCol, toRow, toCol)) {
            return false;
        }
        
        return true;
    }
    
    /**
     * 检查移动后是否会导致将帅照面
     * @param {Array} pieces - 棋盘上所有棋子
     * @param {string} color - 移动方的颜色
     * @param {number} fromRow - 起始行
     * @param {number} fromCol - 起始列
     * @param {number} toRow - 目标行
     * @param {number} toCol - 目标列
     * @returns {boolean} 如果会导致将帅照面返回true
     */
    static wouldCauseKingsFacing(pieces, color, fromRow, fromCol, toRow, toCol) {
        // 模拟移动
        const movedPiece = this.getPieceAt(pieces, fromRow, fromCol);
        if (!movedPiece) return false;
        
        const originalRow = movedPiece.row;
        const originalCol = movedPiece.col;
        const capturedPiece = this.getPieceAt(pieces, toRow, toCol);
        
        // 临时执行移动
        movedPiece.moveTo(toRow, toCol);
        if (capturedPiece) {
            pieces = pieces.filter(p => p !== capturedPiece);
        }
        
        // 查找双方的将帅
        const redKing = pieces.find(p => p instanceof Han && p.color === 'red');
        const blackKing = pieces.find(p => p instanceof Han && p.color === 'black');
        
        let kingsFacing = false;
        
        // 如果双方将帅都在，检查是否照面
        if (redKing && blackKing) {
            // 必须在同一列
            if (redKing.col === blackKing.col) {
                // 检查中间是否有棋子
                let hasPieceBetween = false;
                const start = Math.min(redKing.row, blackKing.row) + 1;
                const end = Math.max(redKing.row, blackKing.row);
                for (let row = start; row < end; row++) {
                    if (this.getPieceAt(pieces, row, redKing.col)) {
                        hasPieceBetween = true;
                        break;
                    }
                }
                // 如果中间没有棋子，说明将帅照面
                if (!hasPieceBetween) {
                    kingsFacing = true;
                }
            }
        }
        
        // 恢复状态
        movedPiece.moveTo(originalRow, originalCol);
        if (capturedPiece) {
            pieces.push(capturedPiece);
        }
        
        return kingsFacing;
    }
    
    /**
     * 炮的移动规则
     */
    static isValidPaoMove(pieces, fromRow, fromCol, toRow, toCol) {
        if (fromRow !== toRow && fromCol !== toCol) {
            return false;
        }
        
        // 计算路径上的棋子数量
        let piecesInPath = 0;
        if (fromRow === toRow) {
            // 横向移动
            const start = Math.min(fromCol, toCol) + 1;
            const end = Math.max(fromCol, toCol);
            for (let col = start; col < end; col++) {
                if (this.getPieceAt(pieces, fromRow, col)) {
                    piecesInPath++;
                }
            }
        } else {
            // 纵向移动
            const start = Math.min(fromRow, toRow) + 1;
            const end = Math.max(fromRow, toRow);
            for (let row = start; row < end; row++) {
                if (this.getPieceAt(pieces, row, fromCol)) {
                    piecesInPath++;
                }
            }
        }
        
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        
        // 吃子时必须有一个炮架
        if (targetPiece) {
            return piecesInPath === 1;
        }
        
        // 移动时不能有棋子
        return piecesInPath === 0;
    }
    
    /**
     * 兵/卒的移动规则（增强版）
     * 核心规则：
     * 1. 一格移动（前后左右）：都能吃子
     * 2. 大于一格的移动（只能向前）：不能吃子
     * 3. 未进入敌阵：只能向前，不能左右
     * 4. 进入敌阵：可以左右移动一格
     */
    static isValidPawnMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        const distance = absRowDiff + absColDiff;
        
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        
        // 检查是否是三子相连吃子
        if (targetPiece && targetPiece.color !== color) {
            if (this.canPawnCaptureByConnection(pieces, color, fromRow, fromCol, toRow, toCol)) {
                return true;
            }
        }
        
        // 检查是否已进入敌方阵地
        const hasCrossedGreatWall = (color === 'red' && fromRow <= 5) ||
                                    (color === 'black' && fromRow >= 7);
        
        // 规则1：不能后退
        if (color === 'red' && rowDiff > 0) return false;
        if (color === 'black' && rowDiff < 0) return false;
        
        // 规则2：未进入敌阵，不能左右移动
        if (!hasCrossedGreatWall && rowDiff === 0) return false;
        
        // 规则3：大于一格的移动不能吃子
        if (distance > 1 && targetPiece) return false;
        
        // 规则4：大于一格必须向前直走
        if (distance > 1 && colDiff !== 0) return false;
        
        // 获取规则配置：是否允许快速移动
        const config = this.getRuleConfig();
        const allowFastMove = config.pawnFastMove !== undefined ? config.pawnFastMove : true;
        
        // 如果不允许快速移动，则限制最多只能走一格
        if (!allowFastMove && distance > 1) {
            return false;
        }
        
        // 规则5：检查路径阻挡（仅大于一格时需要）
        if (distance > 1) {
            const stepRow = color === 'red' ? -1 : 1;
            for (let row = fromRow + stepRow; row !== toRow; row += stepRow) {
                if (this.getPieceAt(pieces, row, fromCol)) {
                    return false; // 有阻挡
                }
            }
        }
        
        return true;
    }
    
    /**
     * 检查兵是否可以三子相连吃子
     * 条件：两个己方棋子和一个敌方棋子在一条直线上相连，且目标必须与兵相邻
     * 三种情况：
     *   1. [己方]-[兵]-[敌方] (兵在中间)
     *   2. [兵]-[己方]-[敌方] (兵在一端，己方在中间)
     *   3. [敌方]-[己方]-[兵] (兵在一端，己方在中间，反向)
     */
    static canPawnCaptureByConnection(pieces, color, fromRow, fromCol, toRow, toCol) {
        // 首先检查目标位置是否与兵相邻（距离为 1 格）
        const rowDiff = Math.abs(toRow - fromRow);
        const colDiff = Math.abs(toCol - fromCol);
        if (rowDiff + colDiff !== 1) {
            // 目标不相邻，不能使用该规则吃子
            return false;
        }
        
        // 确定移动方向
        const dirRow = toRow - fromRow; // -1, 0, or 1
        const dirCol = toCol - fromCol; // -1, 0, or 1
        
        // 情况1: [己方]-[兵]-[敌方] (兵在中间，检查反方向是否有己方棋子)
        const backRow = fromRow - dirRow;
        const backCol = fromCol - dirCol;
        if (backRow >= 0 && backRow < 13 && backCol >= 0 && backCol < 13) {
            const backPiece = this.getPieceAt(pieces, backRow, backCol);
            if (backPiece && backPiece.color === color) {
                return true; // 形成 [己方]-[兵]->[敌方]
            }
        }
        
        // 情况2: [兵]-[己方]-[敌方] (兵在一端，检查目标位置的下一个位置是否有己方棋子)
        const nextRow = toRow + dirRow;
        const nextCol = toCol + dirCol;
        if (nextRow >= 0 && nextRow < 13 && nextCol >= 0 && nextCol < 13) {
            const nextPiece = this.getPieceAt(pieces, nextRow, nextCol);
            if (nextPiece && nextPiece.color === color) {
                return true; // 形成 [兵]->[敌方]-[己方]
            }
        }
        
        return false;
    }


    
    /**
     * 射/䠶的移动规则（匈汉象棋）
     * 1. 只能斜向移动和吃子（类似斜向版的车）
     * 2. 斜向移动时不能有"夹逼"(两侧都有棋子)
     * 3. 最大移动距离为斜向3格
     * 4. 不能跨越星点（路径上不能经过坐标都是3的倍数的位置）
     */
    static isValidSheMove(pieces, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 必须是斜向移动（行差等于列差）
        if (absRowDiff !== absColDiff || absRowDiff === 0) {
            return false;
        }
        
        // 移动距离限制：最多3格
        if (absRowDiff > 3) {
            return false;
        }
        
        // 检查目标位置是否在棋盘范围内
        if (toRow < 0 || toRow >= 13 || toCol < 0 || toCol >= 13) {
            return false;
        }
        
        // 检查目标位置是否有己方棋子
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        const movingPiece = this.getPieceAt(pieces, fromRow, fromCol);
        if (targetPiece && targetPiece.color === movingPiece.color) {
            return false;
        }
        
        // 检查路径上是否有阻挡
        const stepRow = rowDiff > 0 ? 1 : -1;
        const stepCol = colDiff > 0 ? 1 : -1;
        
        // 首先检查起点位置的夹逼（即使只移动一格也需要检查）
        if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
            return false; // 起点位置存在夹逼，不能移动
        }
        
        // 然后检查路径上的阻挡、夹逼和星点跨越
        for (let i = 1; i < absRowDiff; i++) {
            const checkRow = fromRow + i * stepRow;
            const checkCol = fromCol + i * stepCol;
            
            // 检查是否有棋子阻挡
            if (this.getPieceAt(pieces, checkRow, checkCol)) {
                return false; // 路径上有阻挡
            }
            
            // 检查是否跨越星点（路径上的中间点如果是星点，则不能跨越）
            const isStarPoint = (row, col) => row % 3 === 0 && col % 3 === 0;
            if (isStarPoint(checkRow, checkCol)) {
                return false; // 不能跨越星点
            }
            
            // 使用通用方法检查夹逼
            if (this.hasPinch(checkRow, checkCol, stepRow, stepCol, pieces)) {
                return false; // 存在夹逼，不能移动
            }
        }
        
        // 路径畅通，可以移动或吃子
        return true;
    }
    
    /**
     * 檑/礌的移动规则（匈汉象棋）
     * 1. 可以沿直线或斜线无限移动
     * 2. 不能越过其他棋子
     * 3. 只能攻击落单的敌方棋子，且必须在相邻8格内
     */
    static isValidLeiMove(pieces, fromRow, fromCol, toRow, toCol) {
        // 获取当前棋子的颜色
        const piece = this.getPieceAt(pieces, fromRow, fromCol);
        if (!piece) return false;
        
        // 不能不动
        if (fromRow === toRow && fromCol === toCol) {
            return false;
        }
        
        // 计算偏移量
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 必须是直线或斜线方向
        if (!(rowDiff === 0 || colDiff === 0 || absRowDiff === absColDiff)) {
            return false;
        }
        
        // 检查目标位置是否有棋子
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        
        // 如果目标位置有棋子，判断是否是可攻击的落单敌方棋子
        if (targetPiece) {
            // 不能攻击己方棋子
            if (targetPiece.color === piece.color) {
                return false;
            }
            
            // 只能攻击相邻的敌方棋子（8邻域内）
            if (absRowDiff > 1 || absColDiff > 1) {
                return false;
            }
            
            // 必须是落单的棋子才能攻击
            if (!this.isIsolated(targetPiece, pieces, piece)) {
                return false;
            }
            
            // 是合法的吃子
            return true;
        } else {
            // 如果目标位置为空，检查路径上是否有阻挡
            const steps = Math.max(absRowDiff, absColDiff);
            if (steps > 1) {
                const stepRow = rowDiff > 0 ? 1 : (rowDiff < 0 ? -1 : 0);
                const stepCol = colDiff > 0 ? 1 : (colDiff < 0 ? -1 : 0);
                
                for (let i = 1; i < steps; i++) {
                    const checkRow = fromRow + i * stepRow;
                    const checkCol = fromCol + i * stepCol;
                    
                    if (this.getPieceAt(pieces, checkRow, checkCol)) {
                        return false; // 路径上有阻挡
                    }
                    
                    // 检查斜向移动时是否存在夹逼
                    if (absRowDiff === absColDiff && absRowDiff > 0) {
                        // 使用通用方法检查夹逼
                        if (this.hasPinch(checkRow, checkCol, stepRow, stepCol, pieces)) {
                            return false; // 存在夹逼，不能移动
                        }
                    }
                }
            }
            
            // 是合法的移动到空位
            return true;
        }
    }
    
    /**
     * 检查敌方棋子是否落单（上下左右四个方向没有任何棋子）
     * @param {Object} piece - 要检查的棋子
     * @param {Array} pieces - 棋盘上所有棋子
     * @param {Object} excludePiece - 要排除的棋子（通常是攻击者，如礌），不计入相邻判断
     * @returns {boolean} 如果棋子落单返回true，否则返回false
     */
    static isIsolated(piece, pieces, excludePiece = null) {
        if (!piece) return false;
        
        // 检查四个方向：上、下、左、右
        const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        const { row, col } = piece;
        
        // 检查每个方向是否有棋子
        for (const [dr, dc] of directions) {
            const adjacentRow = row + dr;
            const adjacentCol = col + dc;
            
            // 检查相邻位置是否在棋盘范围内
            if (adjacentRow >= 0 && adjacentRow < 13 && adjacentCol >= 0 && adjacentCol < 13) {
                const adjacentPiece = this.getPieceAt(pieces, adjacentRow, adjacentCol);
                // 如果相邻位置有任何棋子，则目标棋子不是孤立的
                // 但要排除攻击者本身（礌）
                if (adjacentPiece) {
                    // 如果这个相邻棋子就是攻击者，跳过不计
                    if (excludePiece && adjacentPiece === excludePiece) {
                        continue;
                    }
                    return false; // 发现相邻的棋子，不是孤立的
                }
            }
        }
        
        // 四个方向都没有棋子，说明是孤立的
        return true;
    }
    


    
    /**
     * 计算所有可能的移动位置
     */
    static calculatePossibleMoves(pieces, piece) {
        const moves = [];      // 可移动位置
        const capturable = []; // 可吃子位置
        
        // 遍历所有可能的位置(匈汉象棋13x13棋盘)
        for (let row = 0; row < 13; row++) {
            for (let col = 0; col < 13; col++) {
                if (this.isValidMove(pieces, piece, piece.row, piece.col, row, col)) {
                    const targetPiece = this.getPieceAt(pieces, row, col);
                    if (targetPiece) {
                        capturable.push({ row, col });
                    } else {
                        moves.push({ row, col });
                    }
                }
            }
        }
        
        return { moves, capturable };
    }
    
    /**
     * 检查是否将军
     */
    static isCheck(pieces, color) {
        // 找到己方的将/帅
        const king = pieces.find(p => p instanceof Han && p.color === color);
        if (!king) return false;
        
        // 检查对方是否有棋子可以攻击到将/帅
        const opponentColor = color === 'red' ? 'black' : 'red';
        const opponentPieces = pieces.filter(p => p.color === opponentColor);
        
        for (const piece of opponentPieces) {
            if (this.isValidMove(pieces, piece, piece.row, piece.col, king.row, king.col)) {
                return true;
            }
        }
        
        return false;
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameRules;
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.GameRules = GameRules;
}
