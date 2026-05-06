/**
 * 游戏规则引擎
 * 负责验证棋子移动合法性和计算可能移动
 */

class GameRules {
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
        
        // 检查尉的照面限制：如果移动的棋子被敌方尉照面，则不允许移动
        for (const p of pieces) {
            if (p instanceof Wei && p.color !== piece.color) {
                // 直接检查当前移动的棋子是否被这个尉照面
                if (this.isPieceFacingWei(piece, p, pieces)) {
                    // 被尉照面的敌方棋子禁止移动
                    return false;
                }
            }
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
        } else if (piece instanceof King) {
            return this.isValidKingMove(pieces, piece.color, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Pao) {
            return this.isValidPaoMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Pawn) {
            return this.isValidPawnMove(pieces, piece.color, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Wei) {
            return this.isValidWeiMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof She) {
            return this.isValidSheMove(pieces, fromRow, fromCol, toRow, toCol);
        } else if (piece instanceof Lei) {
            return this.isValidLeiMove(pieces, fromRow, fromCol, toRow, toCol);
        // 已移除: Jia, Ci, Dun
        } else if (piece instanceof Xun) {
            return this.isValidXunMove(pieces, fromRow, fromCol, toRow, toCol);
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
     * 马的移动规则：日字走法 + 直三走法，检查蹩马腿
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
        
        // 日字走法
        const isNormalMove = (absRowDiff === 2 && absColDiff === 1) || (absRowDiff === 1 && absColDiff === 2);
        
        // 直三走法：横向或纵向走3格
        const isStraightThree = (absRowDiff === 3 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 3);
        
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
     * 相/象的移动规则（匈汉象棋增强版）
     * 1. 基本移动：田字走法（斜向两格），遵循塞象眼规则
     * 2. 越过长城后：获得前后左右隔一格移动吃子的能力（仍遵循塞象眼）
     * 3. 斜向移动时不能有"夹逼"
     */
    static isValidXiangMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        
        // 检查是否已越过长城（长城在第6行）
        const hasCrossedGreatWall = (color === 'red' && fromRow <= 5) || 
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
     * 士/仕的移动规则(匈汉象棋增强版)
     * 1. 在九宫内:只能斜向一格移动
     * 2. 出了九宫:保留斜走能力,同时获得前后左右移动一格的能力(可控制周围8格)
     * 3. 斜向移动时不能有"夹逼"
     */
    static isValidShiMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
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
     * 将/帅/汉/汗的移动规则（匈汉象棋）
     * 1. 在九宫内：可以前后左右斜向移动一格（8方向），斜向有夹逼限制
     * 2. 出了九宫：只能直线移动一格（4方向：前后左右）
     * 3. 将帅对脸规则（禁止照面）
     */
    static isValidKingMove(pieces, color, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
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
        
        // 根据起始位置应用不同的移动规则
        if (isInPalace) {
            // 在九宫内：可以横竖斜走一格（8方向）
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
            // 在九宫外：只能横竖走一格（4方向），失去斜走能力
            if (!((absRowDiff === 1 && absColDiff === 0) || (absRowDiff === 0 && absColDiff === 1))) {
                return false; // 只能直线移动一格
            }
        }
        
        // 汉/汗进入敌方九宫直接获胜（在移动合法的基础上）
        if (color === 'red') {
            // 红方汉进入黑方九宫(1-3行, 5-7列)获胜
            if (toRow >= 1 && toRow <= 3 && toCol >= 5 && toCol <= 7) {
                return true;
            }
        } else {
            // 黑方汗进入红方九宫(9-11行, 5-7列)获胜
            if (toRow >= 9 && toRow <= 11 && toCol >= 5 && toCol <= 7) {
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
        const redKing = pieces.find(p => p instanceof King && p.color === 'red');
        const blackKing = pieces.find(p => p instanceof King && p.color === 'black');
        
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
     */
    static canPawnCaptureByConnection(pieces, color, fromRow, fromCol, toRow, toCol) {
        // 首先检查目标位置是否与兵相邻（距离为 1 格）
        const rowDiff = Math.abs(toRow - fromRow);
        const colDiff = Math.abs(toCol - fromCol);
        if (rowDiff + colDiff !== 1) {
            // 目标不相邻，不能使用该规则吃子
            return false;
        }
        
        // 检查水平方向
        if (fromRow === toRow) {
            // 检查左侧是否有己方棋子
            if (fromCol > 0) {
                const leftPiece = this.getPieceAt(pieces, fromRow, fromCol - 1);
                if (leftPiece && leftPiece.color === color) {
                    return true; // 左侧有己方棋子，形成三连
                }
            }
            // 检查右侧是否有己方棋子
            if (fromCol < 12) {
                const rightPiece = this.getPieceAt(pieces, fromRow, fromCol + 1);
                if (rightPiece && rightPiece.color === color) {
                    return true; // 右侧有己方棋子，形成三连
                }
            }
        }
        
        // 检查垂直方向
        if (fromCol === toCol) {
            // 检查上方是否有己方棋子
            if (fromRow > 0) {
                const upPiece = this.getPieceAt(pieces, fromRow - 1, fromCol);
                if (upPiece && upPiece.color === color) {
                    return true; // 上方有己方棋子，形成三连
                }
            }
            // 检查下方是否有己方棋子
            if (fromRow < 12) {
                const downPiece = this.getPieceAt(pieces, fromRow + 1, fromCol);
                if (downPiece && downPiece.color === color) {
                    return true; // 下方有己方棋子，形成三连
                }
            }
        }
        
        return false;
    }
    
    // 其他棋子的移动规则实现...
    /**
     * 尉/衛的移动规则（匈汉象棋）
     * 1. 类似炮的移动方式（横向、纵向、斜向）
     * 2. 必须跨越一个棋子才能移动
     * 3. 不能吃子，只能移动到空位
     * 4. 被其照面的敌方棋子禁止移动和攻击
     */
    static isValidWeiMove(pieces, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 必须是横向、纵向或斜向移动
        if (!(rowDiff === 0 || colDiff === 0 || absRowDiff === absColDiff)) {
            return false;
        }
        
        // 不能原地不动
        if (absRowDiff === 0 && absColDiff === 0) {
            return false;
        }
        
        // 检查目标位置是否有棋子（尉不能吃子）
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        if (targetPiece) {
            return false;
        }
        
        // 计算移动方向和步数
        const stepRow = rowDiff === 0 ? 0 : (rowDiff > 0 ? 1 : -1);
        const stepCol = colDiff === 0 ? 0 : (colDiff > 0 ? 1 : -1);
        const steps = Math.max(absRowDiff, absColDiff);
        
        // 统计路径上的棋子数量（不包括起点和终点）
        let pieceCount = 0;
        for (let i = 1; i < steps; i++) {
            const checkRow = fromRow + i * stepRow;
            const checkCol = fromCol + i * stepCol;
            
            // 检查是否超出棋盘边界
            if (checkRow < 0 || checkRow >= 13 || checkCol < 0 || checkCol >= 13) {
                return false;
            }
            
            if (this.getPieceAt(pieces, checkRow, checkCol)) {
                pieceCount++;
            }
        }
        
        // 必须恰好跨越一个棋子（类似炮的移动）
        return pieceCount === 1;
    }
    
    /**
     * 检查尉是否照面某个敌方棋子
     * 尉的照面规则：如果尉和敌方棋子之间没有其他棋子，则形成照面
     */
    static isWeiFacing(piece, pieces) {
        if (!piece || piece.name !== '尉' && piece.name !== '衛') {
            return false;
        }
        
        const enemyColor = piece.color === 'red' ? 'black' : 'red';
        
        // 检查四个方向：上、下、左、右
        const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        
        for (const [dr, dc] of directions) {
            let checkRow = piece.row + dr;
            let checkCol = piece.col + dc;
            
            // 沿该方向查找
            while (checkRow >= 0 && checkRow < 13 && checkCol >= 0 && checkCol < 13) {
                const checkPiece = this.getPieceAt(pieces, checkRow, checkCol);
                
                if (checkPiece) {
                    // 找到第一个棋子
                    if (checkPiece.color === enemyColor) {
                        // 是敌方棋子，形成照面
                        return true;
                    } else {
                        // 是己方棋子，不形成照面，停止检查该方向
                        break;
                    }
                }
                
                checkRow += dr;
                checkCol += dc;
            }
        }
        
        return false;
    }
    
    /**
     * 检查特定棋子是否被尉照面
     * @param {Object} targetPiece - 目标棋子
     * @param {Object} weiPiece - 尉棋子
     * @param {Array} pieces - 棋盘上所有棋子
     * @returns {boolean} 如果目标棋子被尉照面返回true
     */
    static isPieceFacingWei(targetPiece, weiPiece, pieces) {
        if (!targetPiece || !weiPiece) return false;
        
        // 检查四个方向
        const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        
        for (const [dr, dc] of directions) {
            let checkRow = weiPiece.row + dr;
            let checkCol = weiPiece.col + dc;
            
            // 沿该方向查找，直到找到目标棋子或遇到阻挡
            while (checkRow >= 0 && checkRow < 13 && checkCol >= 0 && checkCol < 13) {
                // 如果到达目标位置，说明被照面
                if (checkRow === targetPiece.row && checkCol === targetPiece.col) {
                    return true;
                }
                
                const checkPiece = this.getPieceAt(pieces, checkRow, checkCol);
                
                if (checkPiece) {
                    // 遇到其他棋子（不是目标棋子），说明被阻挡
                    break;
                }
                
                checkRow += dr;
                checkCol += dc;
            }
        }
        
        return false;
    }
    
    /**
     * 获取被尉照面的敌方棋子
     */
    static getWeiFacingPiece(weiPiece, pieces) {
        if (!weiPiece) return null;
        
        const enemyColor = weiPiece.color === 'red' ? 'black' : 'red';
        
        // 检查四个方向
        const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        
        for (const [dr, dc] of directions) {
            let checkRow = weiPiece.row + dr;
            let checkCol = weiPiece.col + dc;
            
            while (checkRow >= 0 && checkRow < 13 && checkCol >= 0 && checkCol < 13) {
                const checkPiece = this.getPieceAt(pieces, checkRow, checkCol);
                
                if (checkPiece) {
                    if (checkPiece.color === enemyColor) {
                        return checkPiece; // 返回被照面的敌方棋子
                    } else {
                        break; // 遇到己方棋子，停止
                    }
                }
                
                checkRow += dr;
                checkCol += dc;
            }
        }
        
        return null;
    }
    
    /**
     * 射/䠶的移动规则（匈汉象棋）
     * 1. 只能斜向移动和吃子（类似斜向版的车）
     * 2. 斜向移动时不能有"夹逼"(两侧都有棋子)
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
        
        // 检查路径上是否有阻挡
        const stepRow = rowDiff > 0 ? 1 : -1;
        const stepCol = colDiff > 0 ? 1 : -1;
        
        // 首先检查起点位置的夹逼（即使只移动一格也需要检查）
        if (this.hasPinch(fromRow, fromCol, stepRow, stepCol, pieces)) {
            return false; // 起点位置存在夹逼，不能移动
        }
        
        // 然后检查路径上的阻挡和夹逼
        for (let i = 1; i < absRowDiff; i++) {
            const checkRow = fromRow + i * stepRow;
            const checkCol = fromCol + i * stepCol;
            
            if (this.getPieceAt(pieces, checkRow, checkCol)) {
                return false; // 路径上有阻挡
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
     * 巡/廵的移动规则（匈汉象棋）
     * 1. 移动：可以走任意偶数格直线（2、4、6…），无阻挡
     * 2. 吃子：必须隔1个格吃子（走2格，吃第2格的子），中间不能有棋子阻挡（类似塞象眼）
     */
    static isValidXunMove(pieces, fromRow, fromCol, toRow, toCol) {
        const rowDiff = toRow - fromRow;
        const colDiff = toCol - fromCol;
        const absRowDiff = Math.abs(rowDiff);
        const absColDiff = Math.abs(colDiff);
        
        // 必须是直线移动（横向或纵向）
        if (!(absRowDiff === 0 || absColDiff === 0)) {
            return false;
        }
        
        // 不能原地不动
        if (absRowDiff === 0 && absColDiff === 0) {
            return false;
        }
        
        // 计算移动距离
        const distance = absRowDiff + absColDiff;
        
        // 检查目标位置
        const targetPiece = this.getPieceAt(pieces, toRow, toCol);
        
        if (targetPiece) {
            // 吃子情况：必须隔1格吃子（走2格）
            if (distance !== 2) {
                return false; // 吃子时必须走2格
            }
            
            // 检查中间是否有棋子（类似塞象眼）
            const midRow = fromRow + rowDiff / 2;
            const midCol = fromCol + colDiff / 2;
            if (this.getPieceAt(pieces, midRow, midCol)) {
                return false; // 中间有棋子，不能吃子
            }
            
            // 可以吃子
            return true;
        } else {
            // 移动到空位：必须是偶数格
            if (distance % 2 !== 0) {
                return false; // 必须是偶数格
            }
            
            // 检查路径上是否有阻挡
            if (absRowDiff > 0) {
                // 纵向移动
                const step = rowDiff > 0 ? 1 : -1;
                for (let i = 1; i < absRowDiff; i++) {
                    const checkRow = fromRow + step * i;
                    if (this.getPieceAt(pieces, checkRow, fromCol)) {
                        return false; // 路径上有阻挡
                    }
                }
            } else {
                // 横向移动
                const step = colDiff > 0 ? 1 : -1;
                for (let i = 1; i < absColDiff; i++) {
                    const checkCol = fromCol + step * i;
                    if (this.getPieceAt(pieces, fromRow, checkCol)) {
                        return false; // 路径上有阻挡
                    }
                }
            }
            
            // 可以移动到空位
            return true;
        }
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
        const king = pieces.find(p => p instanceof King && p.color === color);
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
