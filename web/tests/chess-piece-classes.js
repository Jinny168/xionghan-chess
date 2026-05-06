/**
 * 棋子类定义 - 用于测试
 * 简化版，只包含必要的属性和方法
 */

// 基础棋子类
class ChessPiece {
    constructor(name, color, row, col) {
        this.name = name;
        this.color = color;
        this.row = row;
        this.col = col;
    }
    
    moveTo(row, col) {
        this.row = row;
        this.col = col;
    }
}

// 车
class Ju extends ChessPiece {
    constructor(color, row, col) {
        super('车', color, row, col);
    }
}

// 马
class Ma extends ChessPiece {
    constructor(color, row, col) {
        super('马', color, row, col);
    }
}

// 相/象
class Xiang extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '相' : '象', color, row, col);
    }
}

// 士/仕
class Shi extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '仕' : '士', color, row, col);
    }
}

// 将/帅/汉/汗
class Han extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '漢' : '汗', color, row, col);
    }
}

// 炮
class Pao extends ChessPiece {
    constructor(color, row, col) {
        super('炮', color, row, col);
    }
}

// 兵/卒
class Bing extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '兵' : '卒', color, row, col);
    }
}

// 尉/衛
class Wei extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '尉' : '衛', color, row, col);
    }
}

// 射/䠶
class She extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '射' : '䠶', color, row, col);
    }
}

// 檑/礌
class Lei extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '檑' : '礌', color, row, col);
    }
}

// 巡/廵
class Xun extends ChessPiece {
    constructor(color, row, col) {
        super(color === 'red' ? '巡' : '廵', color, row, col);
    }
}

// 导出所有棋子类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ChessPiece,
        Ju, Ma, Xiang, Shi, Han, Bing, Pao,
        Wei, She, Lei, Xun
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
    window.Xun = Xun;
}
