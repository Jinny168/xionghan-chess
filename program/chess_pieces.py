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
        self.color = color  # 颜色：red或black
        self.name = name  # 棋子名称
        self.row = row  # 行坐标
        self.col = col  # 列坐标

    def move_to(self, row, col):
        """移动棋子到新位置"""
        self.row = row
        self.col = col


# 传统棋子
class Ju(ChessPiece):
    """車/车"""

    def __init__(self, color, row, col):
        name = "车" if color == "black" else "車"
        super().__init__(color, name, row, col)


class Ma(ChessPiece):
    """馬/马"""

    def __init__(self, color, row, col):
        name = "马" if color == "black" else "馬"
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

        for dr, dc in directions:
            adj_row, adj_col = target_piece.row + dr, target_piece.col + dc

            # 检查是否在棋盘内
            if not (0 <= adj_row < 13 and 0 <= adj_col < 13):
                continue

            # 检查是否有敌方的友方棋子
            piece = None
            for p in pieces:
                if p.row == adj_row and p.col == adj_col:
                    piece = p
                    break

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
                if not (0 <= current_row < 13 and 0 <= current_col < 13):
                    break

                # 检查是否有棋子阻挡
                target_piece = None
                for piece in pieces:
                    if piece.row == current_row and piece.col == current_col:
                        target_piece = piece
                        break

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

        # 检查周围的8个相邻格子
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                # 跳过当前位置
                if dr == 0 and dc == 0:
                    continue

                target_row = self.row + dr
                target_col = self.col + dc

                # 检查是否在棋盘内
                if not (0 <= target_row < 13 and 0 <= target_col < 13):
                    continue

                # 检查是否有棋子
                target_piece = None
                for piece in pieces:
                    if piece.row == target_row and piece.col == target_col:
                        target_piece = piece
                        break

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


def create_initial_pieces():
    """创建匈汉象棋初始布局的所有棋子
    
    Returns:
        list: 所有棋子的列表
    """
    pieces = []

    # 黑方(上方)
    # 第0行
    pieces.append(Jia("black", 0, 2))
    pieces.append(Jia("black", 0, 10))
    pieces.append(She("black", 0, 0))
    pieces.append(She("black", 0, 12))
    pieces.append(Lei("black", 0, 4))
    pieces.append(Lei("black", 0, 8))
    pieces.append(Wei("black", 0, 6))
    pieces.append(Ci("black", 0, 3))  # 刺
    pieces.append(Ci("black", 0, 9))  # 刺
    pieces.append(Dun("black", 0, 1))  # 盾
    pieces.append(Dun("black", 0, 11))  # 盾

    # 第1行
    pieces.append(Ju("black", 1, 2))
    pieces.append(Ma("black", 1, 3))
    pieces.append(Xiang("black", 1, 4))
    pieces.append(Shi("black", 1, 5))
    pieces.append(King("black", 1, 6))  # 汗
    pieces.append(Shi("black", 1, 7))
    pieces.append(Xiang("black", 1, 8))
    pieces.append(Ma("black", 1, 9))
    pieces.append(Ju("black", 1, 10))
    # 第3行
    pieces.append(Pao("black", 3, 1))
    pieces.append(Pao("black", 3, 11))
    # 第4行
    pieces.append(Pawn("black", 4, 0))
    pieces.append(Pawn("black", 4, 2))
    pieces.append(Pawn("black", 4, 4))
    pieces.append(Pawn("black", 4, 6))
    pieces.append(Pawn("black", 4, 8))
    pieces.append(Pawn("black", 4, 10))
    pieces.append(Pawn("black", 4, 12))

    # 红方(下方)
    # 第12行 (红方底线)
    pieces.append(Dun("red", 12, 1))  # 盾
    pieces.append(She("red", 12, 0))  # 射
    pieces.append(Jia("red", 12, 2))  # 甲
    pieces.append(Jia("red", 12, 10))  # 甲
    pieces.append(Ci("red", 12, 3))  # 刺
    pieces.append(Ci("red", 12, 9))  # 刺
    pieces.append(Wei("red", 12, 6))  # 尉
    pieces.append(Lei("red", 12, 4))  # 檑
    pieces.append(Lei("red", 12, 8))  # 檑
    pieces.append(She("red", 12, 12))  # 射
    pieces.append(Dun("red", 12, 11))  # 盾
    # 第11行
    pieces.append(Ju("red", 11, 2))  # 車
    pieces.append(Ma("red", 11, 3))  # 馬
    pieces.append(Xiang("red", 11, 4))  # 象
    pieces.append(Shi("red", 11, 5))  # 仕
    pieces.append(King("red", 11, 6))  # 汉
    pieces.append(Shi("red", 11, 7))  # 仕
    pieces.append(Xiang("red", 11, 8))  # 象
    pieces.append(Ma("red", 11, 9))  # 馬
    pieces.append(Ju("red", 11, 10))  # 車

    # 第9行
    pieces.append(Pao("red", 9, 1))  # 炮
    pieces.append(Pao("red", 9, 11))  # 炮
    # 第8行
    pieces.append(Pawn("red", 8, 0))  # 兵
    pieces.append(Pawn("red", 8, 2))  # 兵
    pieces.append(Pawn("red", 8, 4))  # 兵
    pieces.append(Pawn("red", 8, 6))  # 兵
    pieces.append(Pawn("red", 8, 8))  # 兵
    pieces.append(Pawn("red", 8, 10))  # 兵
    pieces.append(Pawn("red", 8, 12))  # 兵

    return pieces
