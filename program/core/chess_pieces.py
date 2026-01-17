from program.config.config import BOARD_SIZE
from program.config.config import game_config


class ChessPiece:
    """棋子基类"""

    def __init__(self, color, name, row, col):
        """初始化棋子
        
        Args:
            color (str): 棋子颜色，"red" 或 "black"
            name (str): 棋子名称，如"車"、"马"等
            row (int): 行坐标
            col (int): 列坐标
        """
        if color not in ["red", "black"]:
            raise ValueError("棋子颜色必须是 'red' 或 'black'")
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            raise ValueError(f"棋子位置必须在棋盘范围内 (0-{BOARD_SIZE - 1}, 0-{BOARD_SIZE - 1})")

        self.color = color  # 颜色：red或black
        self.name = name  # 棋子名称
        self.row = row  # 行坐标
        self.col = col  # 列坐标

    def move_to(self, row, col):
        """移动棋子到新位置"""
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            raise ValueError(f"棋子移动位置必须在棋盘范围内 (0-{BOARD_SIZE - 1}, 0-{BOARD_SIZE - 1})")
        self.row = row
        self.col = col


def should_include_piece(piece_class_name):
    """根据设置决定是否包含特定棋子"""
    # 将棋子类名转换为配置键名
    piece_name_map = {
        'Ju': 'ju_appear',
        'Ma': 'ma_appear',
        'Xiang': 'xiang_appear',
        'Shi': 'shi_appear',
        'King': 'king_appear',  # 将/帅总是登场
        'Pao': 'pao_appear',
        'Pawn': 'pawn_appear',
        'Wei': 'wei_appear',
        'She': 'she_appear',
        'Lei': 'lei_appear',
        'Jia': 'jia_appear',
        'Ci': 'ci_appear',
        'Dun': 'dun_appear',
        'Xun': 'xun_appear'
    }
    
    setting_key = piece_name_map.get(piece_class_name, 'king_appear')  # 默认为将/帅设置
    
    # 将/帅必须登场，不接受配置更改
    if piece_class_name == 'King':
        return True
    else:
        return game_config.get_setting(setting_key, True)


# 传统棋子
class Ju(ChessPiece):
    """車/俥"""

    def __init__(self, color, row, col):
        name = "車" if color == "black" else "俥"
        super().__init__(color, name, row, col)


class Ma(ChessPiece):
    """馬/傌"""

    def __init__(self, color, row, col):
        name = "馬" if color == "black" else "傌"
        super().__init__(color, name, row, col)


class Xiang(ChessPiece):
    """相/象"""

    def __init__(self, color, row, col):
        name = "象" if color == "black" else "相"
        super().__init__(color, name, row, col)


class Shi(ChessPiece):
    """士/仕"""

    def __init__(self, color, row, col):
        name = "士" if color == "black" else "仕"
        super().__init__(color, name, row, col)


class King(ChessPiece):
    """将/帅/汉/汗"""

    def __init__(self, color, row, col):
        # 匈汉象棋中黑方为"汗"，红方为"汉"
        name = "汗" if color == "black" else "汉"
        super().__init__(color, name, row, col)


class Pao(ChessPiece):
    """炮/砲"""

    def __init__(self, color, row, col):
        name = "砲" if color == "black" else "炮"
        super().__init__(color, name, row, col)


class Pawn(ChessPiece):
    """兵/卒"""

    def __init__(self, color, row, col):
        name = "卒" if color == "black" else "兵"
        super().__init__(color, name, row, col)


# 匈汉象棋特有棋子
class Wei(ChessPiece):
    """尉/衛"""

    def __init__(self, color, row, col):
        name = "衛" if color == "black" else "尉"
        super().__init__(color, name, row, col)


class She(ChessPiece):
    """射/䠶"""

    def __init__(self, color, row, col):
        name = "䠶" if color == "black" else "射"
        super().__init__(color, name, row, col)


class Lei(ChessPiece):
    """檑/礌棋子类
    
    特性：移动规则类似国际象棋的皇后（直线和斜线，步数无限），
         但攻击规则特殊，只能攻击"落单"的敌方棋子
    """

    def __init__(self, color, row, col):
        name = "礌" if color == "black" else "檑"
        super().__init__(color, name, row, col)

    def is_isolated(self, target_piece, pieces):
        """检查敌方棋子是否"落单"
        
        Args:
            target_piece: 目标棋子
            pieces: 棋盘上所有棋子
            
        Returns:
            bool: 如果目标棋子周围上下左右没有友方棋子，返回True
        """
        # 检查四个方向：上、下、左、右
        directions = [
            (-1, 0),  # 上
            (1, 0),  # 下
            (0, -1),  # 左
            (0, 1)  # 右
        ]

        # 创建一个位置到棋子的映射，提高查找效率
        pos_to_piece = {(p.row, p.col): p for p in pieces}

        for dr, dc in directions:
            adj_row, adj_col = target_piece.row + dr, target_piece.col + dc

            # 检查是否在棋盘内
            if not (0 <= adj_row < BOARD_SIZE and 0 <= adj_col < BOARD_SIZE):
                continue

            # 检查是否有敌方的友方棋子
            piece = pos_to_piece.get((adj_row, adj_col))

            if piece is not None and piece.color == target_piece.color:
                return False  # 找到友方棋子，不是落单

        return True  # 周围没有友方棋子，是落单

    def get_all_moves(self, pieces):
        """获取所有可能的移动位置（非攻击移动）
        
        Args:
            pieces (list): 棋盘上所有棋子
            
        Returns:
            list: 可移动到的位置列表，每个位置为(row, col)元组
        """
        moves = []

        # 创建一个位置到棋子的映射，提高查找效率
        pos_to_piece = {(p.row, p.col): p for p in pieces}

        # 8个移动方向：上、下、左、右、左上、右上、左下、右下
        directions = [
            (-1, 0),  # 上
            (1, 0),  # 下
            (0, -1),  # 左
            (0, 1),  # 右
            (-1, -1),  # 左上
            (-1, 1),  # 右上
            (1, -1),  # 左下
            (1, 1)  # 右下
        ]

        for dr, dc in directions:
            current_row, current_col = self.row, self.col

            # 沿该方向移动直到被阻挡或超出边界
            while True:
                current_row += dr
                current_col += dc

                # 检查是否超出边界
                if not (0 <= current_row < BOARD_SIZE and 0 <= current_col < BOARD_SIZE):
                    break

                # 检查是否有棋子阻挡
                target_piece = pos_to_piece.get((current_row, current_col))

                if target_piece is not None:
                    # 有棋子阻挡，不能继续移动
                    break

                # 可以移动到这个位置
                moves.append((current_row, current_col))

        return moves

    def get_all_attacks(self, pieces):
        """获取所有可能的攻击位置
        
        Args:
            pieces (list): 棋盘上所有棋子
            
        Returns:
            list: 可攻击的位置列表，每个位置为(row, col, piece)元组
        """
        attacks = []

        # 创建一个位置到棋子的映射，提高查找效率
        pos_to_piece = {(p.row, p.col): p for p in pieces}

        # 检查周围的8个相邻格子
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                # 跳过当前位置
                if dr == 0 and dc == 0:
                    continue

                target_row = self.row + dr
                target_col = self.col + dc

                # 检查是否在棋盘内
                if not (0 <= target_row < BOARD_SIZE and 0 <= target_col < BOARD_SIZE):
                    continue

                # 检查是否有棋子
                target_piece = pos_to_piece.get((target_row, target_col))

                # 如果有敌方棋子且是落单的，则可以攻击
                if target_piece is not None and target_piece.color != self.color:
                    if self.is_isolated(target_piece, pieces):
                        attacks.append((target_row, target_col, target_piece))

        return attacks


class Jia(ChessPiece):
    """甲/胄"""

    def __init__(self, color, row, col):
        name = "胄" if color == "black" else "甲"
        super().__init__(color, name, row, col)


class Ci(ChessPiece):
    """刺（拖吃者）"""

    def __init__(self, color, row, col):
        name = "刺" if color == "black" else "刺"
        super().__init__(color, name, row, col)


class Dun(ChessPiece):
    """盾"""

    def __init__(self, color, row, col):
        name = "盾" if color == "black" else "盾"
        super().__init__(color, name, row, col)


class Xun(ChessPiece):
    """巡/廵 - 河界专属控场棋子"""

    def __init__(self, color, row, col):
        name = "廵" if color == "black" else "巡"
        super().__init__(color, name, row, col)


def create_initial_pieces():
    """创建匈汉象棋初始布局的所有棋子
    
    Returns:
        list: 所有棋子的列表
    """
    pieces = []

    # 检查是否启用经典模式
    classic_mode = game_config.get_setting("classic_mode", False)
    
    if classic_mode:
        # 经典模式布局 - 只包含传统象棋棋子及新增的射\檑\巡
        black_pieces_config = [
            # 第0行 - 黑方底线
            (She, 0, 0), (She, 0, 12), (Ju, 0, 10),(Ju, 0, 2),(Lei, 0, 4), (Lei, 0, 8),
            # 第1行
             (Ma, 1, 3), (Xiang, 1, 4), (Shi, 1, 5), (King, 1, 6), (Shi, 1, 7), (Xiang, 1, 8), (Ma, 1, 9),
            # 第3行
            (Pao, 3, 1), (Pao, 3, 11),  # 炮在第三行两侧
            # 第4行
            (Pawn, 4, 0), (Pawn, 4, 2), (Pawn, 4, 4), (Pawn, 4, 6),
            (Pawn, 4, 8), (Pawn, 4, 10), (Pawn, 4, 12) , # 兵在第四行间隔排列
            # 第5行
            (Xun, 5, 0), (Xun, 5, 12)# 黑方巡在最边缘
        ]

        red_pieces_config = [
            # 第12行 - 红方底线
            (She, 12, 0), (She, 12, 12),
            (Lei, 12, 4), (Lei, 12, 8),
             (Ju, 12, 10),(Ju, 12, 2),
            # 第11行
            (Ma, 11, 3), (Xiang, 11, 4), (Shi, 11, 5),
            (King, 11, 6), (Shi, 11, 7), (Xiang, 11, 8), (Ma, 11, 9),

            # 第9行
            (Pao, 9, 1), (Pao, 9, 11),  # 炮在第九行两侧
            # 第8行
            (Pawn, 8, 0), (Pawn, 8, 2), (Pawn, 8, 4), (Pawn, 8, 6),
            (Pawn, 8, 8), (Pawn, 8, 10), (Pawn, 8, 12) , # 兵在第八行间隔排列
            # 第7行
            (Xun, 7, 0), (Xun, 7, 12)# 红方廵在最边缘
        ]
    else:
        # 原始布局配置
        black_pieces_config = [
            # 第0行
            (Jia, 0, 2), (Jia, 0, 10), (She, 0, 0), (She, 0, 12),
            (Lei, 0, 4), (Lei, 0, 8), (Wei, 0, 6),
            (Ci, 0, 3), (Ci, 0, 9),  # 刺
            (Dun, 0, 1), (Dun, 0, 11),  # 盾
            # 第1行
            (Ju, 1, 2), (Ma, 1, 3), (Xiang, 1, 4), (Shi, 1, 5),
            (King, 1, 6), (Shi, 1, 7), (Xiang, 1, 8), (Ma, 1, 9), (Ju, 1, 10),
            # 第3行
            (Pao, 3, 1), (Pao, 3, 11),
            # 第4行
            (Pawn, 4, 0), (Pawn, 4, 2), (Pawn, 4, 4), (Pawn, 4, 6),
            (Pawn, 4, 8), (Pawn, 4, 10), (Pawn, 4, 12),
            # 第5行
            (Xun, 5, 0), (Xun, 5, 12)
        ]

        red_pieces_config = [
            # 第12行 (红方底线)
            (Dun, 12, 1), (She, 12, 0), (Jia, 12, 2), (Jia, 12, 10),
            (Ci, 12, 3), (Ci, 12, 9), (Wei, 12, 6),
            (Lei, 12, 4), (Lei, 12, 8), (She, 12, 12), (Dun, 12, 11),
            # 第11行
            (Ju, 11, 2), (Ma, 11, 3), (Xiang, 11, 4), (Shi, 11, 5),
            (King, 11, 6), (Shi, 11, 7), (Xiang, 11, 8), (Ma, 11, 9), (Ju, 11, 10),
            # 第9行
            (Pao, 9, 1), (Pao, 9, 11),
            # 第8行
            (Pawn, 8, 0), (Pawn, 8, 2), (Pawn, 8, 4), (Pawn, 8, 6),
            (Pawn, 8, 8), (Pawn, 8, 10), (Pawn, 8, 12),
            # 第7行
            (Xun, 7, 0), (Xun, 7, 12)
        ]

    # 添加黑方棋子，根据设置决定是否添加
    for piece_class, row, col in black_pieces_config:
        # 在经典模式下，只包含特定棋子
        if classic_mode:
            # 经典模式只包含车、马、相、士、汉、炮、兵，以及新增的射、檑、巡
            if piece_class in [Ju, Ma, Xiang, Shi, King, Pao, Pawn, She, Lei, Xun]:
                pieces.append(piece_class("black", row, col))
        else:
            # 原始模式根据设置决定是否包含棋子
            if should_include_piece(piece_class.__name__):
                pieces.append(piece_class("black", row, col))

    # 添加红方棋子，根据设置决定是否添加
    for piece_class, row, col in red_pieces_config:
        # 在经典模式下，只包含特定棋子
        if classic_mode:
            # 经典模式只包含车、马、相、士、将/帅、炮、兵/卒，以及新增的射、檑、巡
            if piece_class in [Ju, Ma, Xiang, Shi, King, Pao, Pawn, She, Lei, Xun]:
                pieces.append(piece_class("red", row, col))
        else:
            # 原始模式根据设置决定是否包含棋子
            if should_include_piece(piece_class.__name__):
                pieces.append(piece_class("red", row, col))

    return pieces
