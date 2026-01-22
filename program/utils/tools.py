"""工具函数模块，包含导入导出棋局和复盘等功能"""
from tkinter import filedialog

from program.core.chess_pieces import (
    King, Ju, Ma, Xiang, Shi, Pao, Pawn, Wei, She, Lei, Jia, Ci, Dun, Xun
)


def generate_move_notation(piece, from_row, from_col, to_row, to_col):
    """生成走法的中文表示，如"炮二平五"、"马8进7"等"""

    piece_name = piece.name  # 直接使用棋子名称

    # 转换列数为中文数字或数字 - 从右至左标识
    # 红方用一至十三标识，黑方用1-13标识
    col_names_red = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
    col_names_black = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]

    # 根据棋子颜色选择合适的列名表示
    col_names = col_names_red if piece.color == "red" else col_names_black

    # 计算棋盘坐标到列标识的映射（从右到左）
    col_index = 12 - from_col  # 从右到左映射 (0-12 -> 12-0)
    from_col_name = col_names[col_index]

    # 判断移动方向
    if to_row < from_row:  # 向上移动
        direction = "进" if piece.color == "red" else "退"
    elif to_row > from_row:  # 向下移动
        direction = "退" if piece.color == "red" else "进"
    else:  # 水平移动
        direction = "平"

    # 获取目标位置
    if direction == "平":
        # 平移表示目标列
        to_col_index = 12 - to_col  # 从右到左映射
        to_col_name = col_names[to_col_index]
        notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
    else:
        # 进退表示移动的距离或目标列
        # 检查是否是马、象、士或新增的对角线移动棋子
        is_diagonal_piece = (isinstance(piece, Ma) or isinstance(piece, Xiang) or
                             isinstance(piece, Shi) or isinstance(piece, She) or
                             isinstance(piece, Wei))

        if is_diagonal_piece:
            # 马、象、士、射、尉用目标列表示
            to_col_index = 12 - to_col  # 从右到左映射
            to_col_name = col_names[to_col_index]
            notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
        else:
            # 其他棋子用移动距离表示
            distance = abs(from_row - to_row)
            # 确保距离在有效范围内
            if distance < 1:
                distance = 1
            elif distance > 12:  # 最大可能距离是12格（从第0行到第12行）
                distance = 12

            if piece.color == "black" and direction == "进":
                # 黑方前进和红方后退是增加行号
                # 确保索引在有效范围内
                index = min(distance - 1, len(col_names_black) - 1)
                distance_str = col_names_black[index]
            elif piece.color == "black" and direction == "退":
                # 黑方后退和红方前进是减少行号
                # 确保索引在有效范围内
                index = min(distance - 1, len(col_names_black) - 1)
                distance_str = col_names_black[index]
            else:
                # 红方使用汉字数字表示距离
                # 确保索引在有效范围内
                # 扩展红方距离表示以适应13x13棋盘
                red_distance_names = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
                index = min(distance - 1, len(red_distance_names) - 1)
                distance_str = red_distance_names[index]
            notation = f"{piece_name}{from_col_name}{direction}{distance_str}"

    return notation

def get_valid_moves(game_state, color):
    """获取指定颜色棋子的所有有效走法"""
    valid_moves = []

    for piece in game_state.pieces:
        if piece.color == color:
            # 获取该棋子所有可能的移动位置
            possible_moves, _ = game_state.calculate_possible_moves(piece.row, piece.col)

            # 添加到有效走法列表
            for to_row, to_col in possible_moves:
                valid_moves.append(((piece.row, piece.col), (to_row, to_col)))

    return valid_moves

def is_pawn_at_opponent_base(piece, to_row):
    """检查兵/卒是否移动到对方底线

    Args:
        piece: 棋子对象
        to_row: 目标行

    Returns:
        bool: 是否到达对方底线
    """
    if not isinstance(piece, Pawn):
        return False

    # 红方兵到达第0行（黑方底线），黑方卒到达第12行（红方底线）
    if piece.color == "red" and to_row == 0:
        return True
    elif piece.color == "black" and to_row == 12:
        return True

    return False

def get_piece_class_by_name(name):
    """根据棋子名称获取对应的棋子类

    Args:
        name (str): 棋子名称

    Returns:
        class: 棋子类
    """


    name_to_class = {
        '汉': King, '汗': King, '漢': King,'帅': King, '将': King,  # 将/帅
        '車': Ju, '俥': Ju,'车': Ju,  # 车
        '馬': Ma, '傌': Ma, '马': Ma, # 马
        '象': Xiang, '相': Xiang,  # 相/象
        '士': Shi, '仕': Shi,  # 士/仕
        '砲': Pao, '炮': Pao,  # 炮
        '卒': Pawn, '兵': Pawn,  # 兵/卒
        '衛': Wei, '尉': Wei, '卫': Wei, # 卫/尉
        '䠶': She, '射': She,  # 射
        '礌': Lei, '檑': Lei,  # 檑
        '胄': Jia, '甲': Jia,  # 甲/胄
        '刺': Ci,  # 刺
        '盾': Dun,  # 盾
        '廵': Xun, '巡': Xun,  # 巡/廵
    }

    return name_to_class.get(name)

def save_game_to_file(game_state, filename=None):
    """保存当前游戏到文件
    
    Args:
        game_state: 游戏状态对象
        filename (str, optional): 保存的文件名
        
    Returns:
        bool: 是否成功保存
    """
    try:
        if filename is None:
            filename = filedialog.asksaveasfilename(
                title="导出棋局",
                defaultextension=".fen",
                filetypes=[("FEN文件", "*.fen"), ("所有文件", "*.*")]
            )
            if not filename:
                return False
        
        # 生成FEN表示
        fen_string = game_state.export_position()
        
        # 保存到文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(fen_string)
        
        print(f"游戏已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存游戏失败: {str(e)}")
        return False


def load_game_from_file(game_state, filename=None):
    """从文件加载游戏
    
    Args:
        game_state: 游戏状态对象
        filename (str, optional): 要加载的文件名
        
    Returns:
        bool: 是否成功加载
    """
    try:
        if filename is None:
            filename = filedialog.askopenfilename(
                title="导入棋局",
                filetypes=[("FEN文件", "*.fen"), ("所有文件", "*.*")]
            )
            if not filename:
                return False
        
        # 从文件读取FEN字符串
        with open(filename, 'r', encoding='utf-8') as f:
            fen_string = f.read().strip()
        
        # 导入位置
        success = game_state.import_position(fen_string)
        if success:
            print(f"游戏已从 {filename} 加载")
        else:
            print("导入游戏失败")
        
        return success
    except Exception as e:
        print(f"加载游戏失败: {str(e)}")
        return False
def check_sound_play(game_instance):
    """检查并播放将军/绝杀音效"""
    # 检查游戏状态是否为将军或绝杀
    if game_instance.game_state.is_checkmate():
        # 绝杀时播放绝杀音效
        try:
            game_instance.sound_manager.play_sound('defeat')  # 播放失败音效
        except:
            pass
    elif game_instance.game_state.is_check:
        # 将军时播放将军音效
        try:
            game_instance.sound_manager.play_sound('warn')  # 播放将军音效
        except:
            pass

def enter_replay_mode(game_state):
    """进入复盘模式
    
    Args:
        game_state: 游戏状态对象
        
    Returns:
        ReplayController: 复盘控制器实例
    """
    from program.controllers.replay_controller import ReplayController
    controller = ReplayController(game_state)
    controller.start_replay()
    return controller