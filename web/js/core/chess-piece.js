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
    
    moveTo(row, col) {
        if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) {
            throw new Error('棋子移动位置必须在棋盘范围内');
        }
        this.row = row;
        this.col = col;
    }
    
    clone() {
        return new ChessPiece(this.color, this.name, this.row, this.col);
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
 * 将/帅/汉/汗
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
 * 尉/衛
 */
class Wei extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '衛' : '尉';
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

// 已移除: 甲/胄(Jia)、刺/伺(Ci)、盾/碷(Dun)

/**
 * 巡/廵
 */
class Xun extends ChessPiece {
    constructor(color, row, col) {
        const name = color === 'black' ? '廵' : '巡';
        super(color, name, row, col);
    }
}

/**
 * 棋子工厂
 */
class PieceFactory {
    static NAME_TO_CLASS_MAP = {
        // 黑方棋子
        '汗': Han, '車': Ju, '馬': Ma, '象': Xiang, '士': Shi, '砲': Pao, '卒': Bing,
        '衛': Wei, '䠶': She, '礌': Lei, '廵': Xun,
        // 红方棋子
        '漢': Han, '俥': Ju, '傌': Ma, '相': Xiang, '仕': Shi, '炮': Pao, '兵': Bing,
        '尉': Wei, '射': She, '檑': Lei, '巡': Xun
    };
    
    static createPieceByName(name, color, row, col) {
        const PieceClass = this.NAME_TO_CLASS_MAP[name];
        if (!PieceClass) {
            console.error(`未找到棋子类型: ${name}`);
            return null;
        }
        return new PieceClass(color, row, col);
    }
    
    static getPieceClassByName(name) {
        return this.NAME_TO_CLASS_MAP[name];
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ChessPiece, Ju, Ma, Xiang, Shi, Han, Bing, Pao, 
        Wei, She, Lei, Xun, PieceFactory,
        BOARD_SIZE, TRADITIONAL_BOARD_ROWS, TRADITIONAL_BOARD_COLS
    };
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
    window.Wei = Wei;
    window.She = She;
    window.Lei = Lei;
    // 已移除: window.Jia, window.Ci, window.Dun
    window.Xun = Xun;
    window.PieceFactory = PieceFactory;
    window.BOARD_SIZE = BOARD_SIZE;
    window.TRADITIONAL_BOARD_ROWS = TRADITIONAL_BOARD_ROWS;
    window.TRADITIONAL_BOARD_COLS = TRADITIONAL_BOARD_COLS;
}
