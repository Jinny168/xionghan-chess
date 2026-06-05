/**
 * 棋子基类和各类棋子定义
 */

// 棋盘配置
const BOARD_SIZE = 13;
const TRADITIONAL_BOARD_ROWS = 10;
const TRADITIONAL_BOARD_COLS = 9;

/**
 * 棋子基类
 */
class ChessPiece {
    constructor(color, name, row, col) {
        if (color !== 'red' && color !== 'black') {
            throw new Error('棋子颜色必须是 red 或 black');
        }
        
        this.color = color;
        this.name = name;
        this.row = row;
        this.col = col;
    }
    
    /**
     * 移动棋子到指定位置
     * @param {number} row - 目标行
     * @param {number} col - 目标列
     */
    moveTo(row, col) {
        if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) {
            throw new Error('棋子移动位置必须在棋盘范围内');
        }
        this.row = row;
        this.col = col;
    }
}

/**
 * 车/俥
 */
class Ju extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '車' : '俥';
        super(color, name, row, col);
    }
}

/**
 * 马/傌
 */
class Ma extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '馬' : '傌';
        super(color, name, row, col);
    }
}

/**
 * 相/象
 */
class Xiang extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '象' : '相';
        super(color, name, row, col);
    }
}

/**
 * 士/仕
 */
class Shi extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '士' : '仕';
        super(color, name, row, col);
    }
}

/**
 * 漢/汗
 */
class Han extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '汗' : '漢';
        super(color, name, row, col);
    }
}

/**
 * 炮/砲
 */
class Pao extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '砲' : '炮';
        super(color, name, row, col);
    }
}

/**
 * 兵/卒
 */
class Bing extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '卒' : '兵';
        super(color, name, row, col);
    }
}



/**
 * 射/䠶
 */
class She extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '䠶' : '射';
        super(color, name, row, col);
    }
}

/**
 * 檑/礌
 */
class Lei extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '礌' : '檑';
        super(color, name, row, col);
    }
}



/**
 * 棋子工厂
 */
class PieceFactory {
    /**
     * 棋子名称到类的映射表
     * @type {Object<string, typeof ChessPiece>}
     */
    static NAME_TO_CLASS_MAP = {
        // 黑方棋子
        '汗': Han, '車': Ju, '馬': Ma, '象': Xiang, '士': Shi, '砲': Pao, '卒': Bing,
        '䠶': She, '礌': Lei,
        // 红方棋子
        '漢': Han, '俥': Ju, '傌': Ma, '相': Xiang, '仕': Shi, '炮': Pao, '兵': Bing,
        '射': She, '檑': Lei
    };
    
    /**
     * 根据名称创建棋子
     * @param {string} name - 棋子名称
     * @param {string} color - 棋子颜色 ('red' 或 'black')
     * @param {number} row - 行坐标
     * @param {number} col - 列坐标
     * @returns {Object|null} 棋子对象
     */
    static createPieceByName(name, color, row, col) {
        const PieceClass = this.NAME_TO_CLASS_MAP[name];
        if (!PieceClass) {
            console.error(`未找到棋子类型: ${name}`);
            return null;
        }
        return new PieceClass(color, row, col);
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.ChessPiece = ChessPiece;
    window.Ju = Ju;
    window.Ma = Ma;
    window.Xiang = Xiang;
    window.Shi = Shi;
    window.Han = Han;
    window.Bing = Bing;
    window.Pao = Pao;
    window.She = She;
    window.Lei = Lei;
    // 已移除: window.Jia, window.Ci, window.Dun, window.Wei, window.Xun
    window.PieceFactory = PieceFactory;
    window.BOARD_SIZE = BOARD_SIZE;
    window.TRADITIONAL_BOARD_ROWS = TRADITIONAL_BOARD_ROWS;
    window.TRADITIONAL_BOARD_COLS = TRADITIONAL_BOARD_COLS;
}
