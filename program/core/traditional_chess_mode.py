"""传统象棋模式实现模块"""

import json
import os
from program.core.traditional_chess_rules import TraditionalChessRules
from program.core.chess_pieces import King, Ju, Ma, Xiang, Shi, Pao, Pawn


class TraditionalChessMode:
    """传统象棋模式类，管理传统象棋模式的状态和逻辑"""
    
    def __init__(self):
        """初始化传统象棋模式"""
        self.name = "traditional"
        self.display_name = "传统象棋模式"
        self.description = "完全遵循中国传统象棋规则，仅包含标准传统棋子，无匈汉特色棋子"
        self.pieces = ["將", "帥", "仕", "士", "相", "象", "傌", "马", "俥", "车", "炮", "砲", "兵", "卒"]
        self.highlight_color = (0, 150, 0)  # 选中高亮色：绿色
        self.layout_file = "traditional_layout.json"
        self.rules = TraditionalChessRules()
        
    def load_layout(self):
        """从JSON文件加载传统象棋初始布局"""
        layout_path = os.path.join(os.path.dirname(__file__), self.layout_file)
        try:
            with open(layout_path, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            return layout_data
        except FileNotFoundError:
            print(f"布局文件不存在: {layout_path}")
            # 返回默认布局
            return self.create_default_traditional_layout()
        except json.JSONDecodeError:
            print(f"布局文件格式错误: {layout_path}")
            return self.create_default_traditional_layout()
    
    def create_default_traditional_layout(self):
        """创建默认的传统象棋布局"""
        layout = {
            "name": "traditional_layout",
            "description": "传统中国象棋初始布局",
            "board_size": 13,
            "pieces": [
                # 黑方（下方）
                {"type": "black_shi", "name": "士", "row": 0, "col": 3},
                {"type": "black_shi", "name": "士", "row": 0, "col": 5},
                {"type": "black_xiang", "name": "象", "row": 0, "col": 2},
                {"type": "black_xiang", "name": "象", "row": 0, "col": 6},
                {"type": "black_ma", "name": "馬", "row": 0, "col": 1},
                {"type": "black_ma", "name": "馬", "row": 0, "col": 7},
                {"type": "black_ju", "name": "車", "row": 0, "col": 0},
                {"type": "black_ju", "name": "車", "row": 0, "col": 8},
                {"type": "black_king", "name": "將", "row": 0, "col": 4},
                {"type": "black_pao", "name": "砲", "row": 2, "col": 1},
                {"type": "black_pao", "name": "砲", "row": 2, "col": 7},
                {"type": "black_pawn", "name": "卒", "row": 3, "col": 0},
                {"type": "black_pawn", "name": "卒", "row": 3, "col": 2},
                {"type": "black_pawn", "name": "卒", "row": 3, "col": 4},
                {"type": "black_pawn", "name": "卒", "row": 3, "col": 6},
                {"type": "black_pawn", "name": "卒", "row": 3, "col": 8},
                
                # 红方（上方）
                {"type": "red_shi", "name": "仕", "row": 9, "col": 3},
                {"type": "red_shi", "name": "仕", "row": 9, "col": 5},
                {"type": "red_xiang", "name": "相", "row": 9, "col": 2},
                {"type": "red_xiang", "name": "相", "row": 9, "col": 6},
                {"type": "red_ma", "name": "傌", "row": 9, "col": 1},
                {"type": "red_ma", "name": "傌", "row": 9, "col": 7},
                {"type": "red_ju", "name": "俥", "row": 9, "col": 0},
                {"type": "red_ju", "name": "俥", "row": 9, "col": 8},
                {"type": "red_king", "name": "帥", "row": 9, "col": 4},
                {"type": "red_pao", "name": "炮", "row": 7, "col": 1},
                {"type": "red_pao", "name": "炮", "row": 7, "col": 7},
                {"type": "red_pawn", "name": "兵", "row": 6, "col": 0},
                {"type": "red_pawn", "name": "兵", "row": 6, "col": 2},
                {"type": "red_pawn", "name": "兵", "row": 6, "col": 4},
                {"type": "red_pawn", "name": "兵", "row": 6, "col": 6},
                {"type": "red_pawn", "name": "兵", "row": 6, "col": 8}
            ]
        }
        return layout

    def create_traditional_pieces(self):
        """创建传统象棋的棋子列表"""
        layout_data = self.load_layout()
        pieces = []
        
        for piece_data in layout_data["pieces"]:
            piece_type = piece_data["type"]
            row = piece_data["row"]
            col = piece_data["col"]
            name = piece_data["name"]
            
            # 根据棋子类型创建相应棋子
            if "king" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = King(color, row, col)
                # 修改将/帅的名称以符合传统象棋
                if color == "black":
                    piece.name = "將"  # 黑方为将
                else:
                    piece.name = "帥"  # 红方为帅
            elif "ju" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = Ju(color, row, col)
                # 修改車/车的名称
                if color == "black":
                    piece.name = "車"  # 黑方为車
                else:
                    piece.name = "俥"  # 红方为俥
            elif "ma" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = Ma(color, row, col)
                # 修改馬/马的名称
                if color == "black":
                    piece.name = "馬"  # 黑方为馬
                else:
                    piece.name = "傌"  # 红方为傌
            elif "xiang" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = Xiang(color, row, col)
                # 修改相/象的名称
                if color == "black":
                    piece.name = "象"  # 黑方为象
                else:
                    piece.name = "相"  # 红方为相
            elif "shi" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = Shi(color, row, col)
                # 修改士/仕的名称
                if color == "black":
                    piece.name = "士"  # 黑方为士
                else:
                    piece.name = "仕"  # 红方为仕
            elif "pao" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = Pao(color, row, col)
                # 修改炮/砲的名称
                if color == "black":
                    piece.name = "砲"  # 黑方为砲
                else:
                    piece.name = "炮"  # 红方为炮
            elif "pawn" in piece_type:
                color = "black" if "black" in piece_type else "red"
                piece = Pawn(color, row, col)
                # 修改兵/卒的名称
                if color == "black":
                    piece.name = "卒"  # 黑方为卒
                else:
                    piece.name = "兵"  # 红方为兵
            else:
                continue  # 跳过未知类型
            
            pieces.append(piece)
        
        return pieces

    def is_valid_traditional_move(self, pieces, piece, from_row, from_col, to_row, to_col):
        """验证传统象棋棋子移动的合法性"""
        return self.rules.is_valid_move(pieces, piece, from_row, from_col, to_row, to_col)

    def get_traditional_possible_moves(self, pieces, piece):
        """获取传统象棋棋子的所有可能移动"""
        return self.rules.calculate_possible_moves(pieces, piece)

    def is_traditional_check(self, pieces, color):
        """检查传统象棋模式下是否被将军"""
        return self.rules.is_in_check(pieces, color)

    def is_traditional_checkmate(self, pieces, color):
        """检查传统象棋模式下是否被将死"""
        return self.rules.is_checkmate(pieces, color)

    def is_traditional_stalemate(self, pieces, color):
        """检查传统象棋模式下是否困毙"""
        return self.rules.is_stalemate(pieces, color)

    def is_traditional_game_over(self, pieces, current_player, move_history=None, move_count_without_capture_or_pawn=0):
        """检查传统象棋模式下游戏是否结束"""
        # 检查将死和困毙
        is_over, winner = self.rules.is_game_over(pieces, current_player)
        if is_over:
            return is_over, winner
        
        # 检查重复局面
        if move_history and self.rules.is_repeated_move(pieces, move_history, current_player):
            return True, None  # 重复局面判和
        
        # 检查自然限着
        if self.rules.is_fifty_move_rule(move_count_without_capture_or_pawn):
            return True, None  # 自然限着判和
        
        return False, None


# 传统象棋模式配置
TRADITIONAL_GAME_MODES = {
    "traditional": {  # 传统象棋模式（核心新增）
        "name": "传统象棋模式",
        "desc": "完全遵循中国传统象棋规则，仅包含标准传统棋子，无匈汉特色棋子",
        "pieces": [  # 仅保留传统象棋标准棋子（繁简适配）
            "將", "帥", "仕", "士", "相", "象", "傌", "马", 
            "俥", "车", "炮", "砲", "兵", "卒"
        ],
        "rules_module": "traditional_chess_rules",  # 传统规则模块
        "highlight_color": (0, 150, 0),  # 选中高亮色：绿色
        "initial_layout": "traditional_layout.json"  # 传统棋子初始布局
    },
    "classic_hh": {  # 保留原有经典匈汉模式
        "name": "经典匈汉模式",
        "desc": "传统象棋基础+少量匈汉特色棋子",
        "pieces": ["將", "帥", "仕", "相", "傌", "俥", "炮", "兵", "巡", "射"],
        "rules_module": "classic_hh_chess_rules",
        "highlight_color": (255, 140, 0),
        "initial_layout": "classic_hh_layout.json"
    },
    "crazy_hh": {  # 保留原有疯狂匈汉模式
        "name": "疯狂匈汉模式",
        "desc": "传统象棋基础+全部匈汉特色棋子",
        "pieces": ["將", "帥", "仕", "相", "傌", "俥", "炮", "兵", "巡", "射", "檑", "甲", "楯", "刺", "尉"],
        "rules_module": "crazy_hh_chess_rules",
        "highlight_color": (220, 0, 0),
        "initial_layout": "crazy_hh_layout.json"
    }
}


def init_traditional_mode():
    """
    初始化传统象棋模式
    - 清空棋盘缓存
    - 加载传统布局
    - 绑定传统规则
    - 重置走棋方（红方先行）
    """
    # 这个函数将在游戏控制器中实现
    pass


def check_traditional_move(piece_type: str, from_pos: tuple, to_pos: tuple) -> bool:
    """
    校验传统象棋棋子走棋合法性
    :param piece_type: 棋子类型（如"帥""車"）
    :param from_pos: 起始坐标 (x, y)
    :param to_pos: 目标坐标 (x, y)
    :return: 合法返回True，非法返回False
    """
    # 这个函数将在游戏控制器中根据具体棋子状态实现
    pass


def switch_game_mode(mode_key: str) -> None:
    """
    统一的模式切换函数
    :param mode_key: 模式标识（traditional/classic_hh/crazy_hh）
    """
    # 这个函数将在游戏控制器中实现
    pass