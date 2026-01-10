# coding=utf-8
"""匈汉象棋棋盘游戏控制 - 用于MCTS和神经网络训练"""

import copy
import random
import time
from collections import deque  # 这个队列用来判断长将或长捉

import numpy as np

from mcts_config import CONFIG

# 匈汉象棋使用13x13棋盘
# 初始棋盘状态 - 使用匈汉象棋的初始布局
# 列表来表示棋盘，红方在上，黑方在下。使用时需要使用深拷贝
state_list_init = [
    # 0行
    ['黑射', '一一', '黑甲', '一一', '黑礌', '一一', '黑衛', '一一', '黑礌', '一一', '黑甲', '一一', '黑射'],
    # 1行
    ['一一', '一一', '黑車', '黑馬', '黑象', '黑士', '黑汗', '黑士', '黑象', '黑馬', '黑車', '一一', '一一'],
    # 2行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 3行
    ['一一','黑砲' , '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '黑砲', '一一'],
    # 4行
    ['黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒'],
    # 5行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 6行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 7行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 8行
    ['红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵'],
    # 9行
    ['一一', '红炮', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '红炮', '一一'],
    # 10行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 11行
    ['一一', '一一', '红車', '红馬', '红象', '红仕', '红汉', '红仕', '红象', '红馬', '红車', '一一', '一一'],
    # 12行
    ['红射', '一一', '红甲', '一一', '红檑', '一一', '红尉', '一一', '红檑', '一一', '红甲', '一一', '红射']
]

# deque来存储棋盘状态，长度为4
state_deque_init = deque(maxlen=4)
for _ in range(4):
    state_deque_init.append(copy.deepcopy(state_list_init))

# 构建一个字典：字符串到数组的映射，函数：数组到字符串的映射
string2array = dict(红車=np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
                    红馬=np.array([0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
                    红象=np.array([0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]),
                    红仕=np.array([0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]),
                    红汉=np.array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),
                    红炮=np.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]),
                    红兵=np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]),
                    红甲=np.array([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]),
                    红檑=np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]),
                    红尉=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]),
                    红射=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]),
                    黑車=np.array([-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
                    黑馬=np.array([0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
                    黑象=np.array([0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0]),
                    黑士=np.array([0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0]),
                    黑汗=np.array([0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0]),
                    黑砲=np.array([0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0]),
                    黑卒=np.array([0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0]),
                    黑甲=np.array([0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0]),
                    黑礌=np.array([0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0]),
                    黑衛=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0]),
                    黑射=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1]),
                    一一=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]))


def array2string(array):
    return list(filter(lambda string: (string2array[string] == array).all(), string2array))[0]


# 改变棋盘状态
def change_state(state_list, move):
    """move : 字符串'00000101'，格式为"from_y(2位)from_x(2位)to_y(2位)to_x(2位)" """
    copy_list = copy.deepcopy(state_list)
    y = int(move[0:2])  # 两位数的行坐标
    x = int(move[2:4])  # 两位数的列坐标
    toy = int(move[4:6])  # 目标行坐标
    tox = int(move[6:8])  # 目标列坐标
    copy_list[toy][tox] = copy_list[y][x]
    copy_list[y][x] = '一一'
    return copy_list


# 打印盘面，可视化用到
def print_board(_state_array):
    # _state_array: [11, 13, 13], CHW
    board_line = []
    for i in range(13):
        for j in range(13):
            board_line.append(array2string(_state_array[:, i, j]))  # 从CHW格式中提取棋子
        print(board_line)
        board_line.clear()


# 列表棋盘状态到数组棋盘状态
def state_list2state_array(state_list):
    _state_array = np.zeros([13, 13, 11])  # [高度, 宽度, 特征平面数]
    for i in range(13):
        for j in range(13):
            _state_array[i][j] = string2array[state_list[i][j]]
    return _state_array


#  建立一个理论上的走子动作空间
# 第一个字典：move_id到move_action
# 第二个字典：move_action到move_id
# 例如：move_id:0 --> move_action:'00000101'
def get_all_legal_moves():
    _move_id2move_action = {}
    _move_action2move_id = {}

    idx = 0
    # 预计算马走日的偏移量
    knight_moves = [(-2, -1), (-1, -2), (-2, 1), (1, -2), (2, -1), (-1, 2), (2, 1), (1, 2)]
    
    for l1 in range(13):
        for n1 in range(13):
            # 车的移动：同一行或同一列
            destinations = []
            # 直线移动（涵盖车/俥、甲/胄、兵/卒、尉/衛、炮/砲）
            for t in range(13):
                if t != n1:  # 排除原位置
                    destinations.append((l1, t))
            for t in range(13):
                if t != l1:  # 排除原位置
                    destinations.append((t, n1))
            
            # 斜向移动（涵盖相/象、射/射、士/仕）
            for (a, b) in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                # 沿着斜线方向移动
                distance = 1
                while True:
                    l2, n2 = l1 + distance * a, n1 + distance * b
                    if check_bounds(l2, n2):
                        destinations.append((l2, n2))
                        distance += 1
                    else:
                        break
            
            # 马走日移动（L形）
            for (a, b) in knight_moves:
                l2, n2 = l1 + a, n1 + b
                # 检查边界
                if check_bounds(l2, n2):
                    destinations.append((l2, n2))
            
            # 处理所有目标位置
            for (l2, n2) in destinations:
                if (l1, n1) != (l2, n2) and check_bounds( ):
                    action = f"{l1:02d}{n1:02d}{l2:02d}{n2:02d}"
                    _move_id2move_action[idx] = action
                    _move_action2move_id[action] = idx
                    idx += 1
                    
    return _move_id2move_action, _move_action2move_id


move_id2move_action, move_action2move_id = get_all_legal_moves()


# 走子翻转的函数，用来扩充我们的数据
def flip_map(string):
    new_str = ''
    for index in range(4):
        if index == 0 or index == 2:
            new_str += (str(string[index]))
        else:
            new_str += (str(8 - int(string[index])))
    return new_str


# 边界检查
def check_bounds(toY, toX):
    if toY in range(13) and toX in range(13):
        return True
    return False


# 不能走到自己的棋子位置
def check_obstruct(piece, current_player_color):
    # 当走到的位置存在棋子的时候，进行一次判断
    if piece != '一一':
        if current_player_color == '红':
            if '黑' in piece:
                return True
            else:
                return False
        elif current_player_color == '黑':
            if '红' in piece:
                return True
            else:
                return False
    else:
        return True


# 得到当前盘面合法走子集合
# 输入状态队列，current_player_color:当前玩家控制的棋子颜色
# 用来存放合法走子的列表，例如[0, 1, 2, 1089, 2085]
def get_legal_moves(state_deque, current_player_color):
    """
    获取匈汉象棋当前盘面的合法走子集合
    """
    state_list = state_deque[-1]
    old_state_list = state_deque[-4]

    moves = []  # 用来存放所有合法的走子方法

    # state_list是以列表形式表示的, len(state_list) == 13, len(state_list[0]) == 13
    # 遍历移动初始位置
    for y in range(13):
        for x in range(13):
            # 只有是棋子才可以移动
            if state_list[y][x] == '一一':
                continue

            piece = state_list[y][x]
            piece_color = '红' if '红' in piece else '黑'

            # 如果不是当前玩家的棋子，跳过
            if piece_color != current_player_color:
                continue

            # 根据棋子类型获取合法走法
            piece_type = piece[1:]  # 去掉颜色，获取棋子类型，如"車", "馬"等

            if piece_type in ['車', '车']:  # 车的走法
                # 横向移动
                for tox in range(13):
                    if tox == x:
                        continue
                    m = f"{y:02d}{x:02d}{y:02d}{tox:02d}"
                    if is_valid_rook_move(state_list, y, x, y, tox):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

                # 纵向移动
                for toy in range(13):
                    if toy == y:
                        continue
                    m = f"{y:02d}{x:02d}{toy:02d}{x:02d}"
                    if is_valid_rook_move(state_list, y, x, toy, x):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

            elif piece_type in ['馬', '马']:  # 马的走法
                # 马走日字
                horse_moves = [
                    (y - 2, x - 1), (y - 2, x + 1),  # 上
                    (y - 1, x - 2), (y - 1, x + 2),  # 左上右上
                    (y + 1, x - 2), (y + 1, x + 2),  # 左下右下
                    (y + 2, x - 1), (y + 2, x + 1)  # 下
                ]

                for toy, tox in horse_moves:
                    if 0 <= toy < 13 and 0 <= tox < 13:
                        m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                        if is_valid_horse_move(state_list, y, x, toy, tox):
                            if change_state(state_list, m) != old_state_list:
                                moves.append(m)

            elif piece_type in ['象', '相']:  # 象的走法
                # 象走田字
                elephant_moves = [
                    (y - 2, x - 2), (y - 2, x + 2),
                    (y + 2, x - 2), (y + 2, x + 2)
                ]

                for toy, tox in elephant_moves:
                    if 0 <= toy < 13 and 0 <= tox < 13:
                        m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                        if is_valid_elephant_move(state_list, y, x, toy, tox):
                            if change_state(state_list, m) != old_state_list:
                                moves.append(m)

            elif piece_type in ['士', '仕']:  # 士的走法
                # 士在九宫内斜走
                advisor_moves = [
                    (y - 1, x - 1), (y - 1, x + 1),
                    (y + 1, x - 1), (y + 1, x + 1)
                ]

                for toy, tox in advisor_moves:
                    if 0 <= toy < 13 and 0 <= tox < 13:
                        m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                        if is_valid_advisor_move(state_list, y, x, toy, tox):
                            if change_state(state_list, m) != old_state_list:
                                moves.append(m)

            elif piece_type in ['汉', '汗']:  # 将/帅的走法
                # 将/帅移动
                king_moves = [
                    (y - 1, x), (y + 1, x),  # 上下
                    (y, x - 1), (y, x + 1)  # 左右
                ]

                # 添加斜向移动（匈汉象棋规则）
                king_moves.extend([
                    (y - 1, x - 1), (y - 1, x + 1),  # 斜上
                    (y + 1, x - 1), (y + 1, x + 1)  # 斜下
                ])

                for toy, tox in king_moves:
                    if 0 <= toy < 13 and 0 <= tox < 13:
                        m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                        if is_valid_king_move(state_list, y, x, toy, tox):
                            if change_state(state_list, m) != old_state_list:
                                moves.append(m)

            elif piece_type in ['炮', '砲']:  # 炮的走法
                # 横向移动
                for tox in range(13):
                    if tox == x:
                        continue
                    m = f"{y:02d}{x:02d}{y:02d}{tox:02d}"
                    if is_valid_cannon_move(state_list, y, x, y, tox):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

                # 纵向移动
                for toy in range(13):
                    if toy == y:
                        continue
                    m = f"{y:02d}{x:02d}{toy:02d}{x:02d}"
                    if is_valid_cannon_move(state_list, y, x, toy, x):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

            elif piece_type in ['兵', '卒']:  # 兵/卒的走法
                pawn_moves = []
                if current_player_color == '红':
                    # 红兵走法
                    if y > 0:  # 未到底线
                        pawn_moves.append((y - 1, x))  # 向前
                        if y <= 6:  # 过河后可横移
                            if x > 0: pawn_moves.append((y, x - 1))  # 左移
                            if x < 12: pawn_moves.append((y, x + 1))  # 右移
                else:  # 黑方
                    # 黑卒走法
                    if y < 12:  # 未到底线
                        pawn_moves.append((y + 1, x))  # 向前
                        if y >= 6:  # 过河后可横移
                            if x > 0: pawn_moves.append((y, x - 1))  # 左移
                            if x < 12: pawn_moves.append((y, x + 1))  # 右移

                for toy, tox in pawn_moves:
                    if 0 <= toy < 13 and 0 <= tox < 13:
                        m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

            # 匈汉象棋特有棋子
            elif piece_type in ['甲', '胄']:  # 甲/胄的走法
                # 甲/胄移动类似炮，但不能吃子，只能移动到空位
                # 横向移动
                for tox in range(13):
                    if tox == x:
                        continue
                    m = f"{y:02d}{x:02d}{y:02d}{tox:02d}"
                    if is_valid_jia_move(state_list, y, x, y, tox):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

                # 纵向移动
                for toy in range(13):
                    if toy == y:
                        continue
                    m = f"{y:02d}{x:02d}{toy:02d}{x:02d}"
                    if is_valid_jia_move(state_list, y, x, toy, x):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

            elif piece_type in ['檑', '礌']:  # 檑/礌的走法
                # 檑/礌可以沿直线和斜线移动
                # 横向、纵向、斜向移动
                directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
                for dy, dx in directions:
                    for dist in range(1, 13):
                        toy, tox = y + dy * dist, x + dx * dist
                        if 0 <= toy < 13 and 0 <= tox < 13:
                            m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                            if is_valid_lei_move(state_list, y, x, toy, tox):
                                if change_state(state_list, m) != old_state_list:
                                    moves.append(m)
                            # 如果遇到棋子，根据规则决定是否继续
                            if state_list[toy][tox] != '一一':
                                break
                        else:
                            break

            elif piece_type in ['尉', '衛']:  # 尉/衛的走法
                # 尉/衛跳跃移动规则
                # 横向跳跃
                for tox in range(13):
                    if tox == x:
                        continue
                    m = f"{y:02d}{x:02d}{y:02d}{tox:02d}"
                    if is_valid_wei_move(state_list, y, x, y, tox):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

                # 纵向跳跃
                for toy in range(13):
                    if toy == y:
                        continue
                    m = f"{y:02d}{x:02d}{toy:02d}{x:02d}"
                    if is_valid_wei_move(state_list, y, x, toy, x):
                        if change_state(state_list, m) != old_state_list:
                            moves.append(m)

            elif piece_type in ['射', '䠶']:  # 射/䠶的走法
                # 射/䠶斜向移动
                directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # 四个斜向方向
                for dy, dx in directions:
                    for dist in range(1, 13):  # 最多移动12格
                        toy, tox = y + dy * dist, x + dx * dist
                        if 0 <= toy < 13 and 0 <= tox < 13:
                            m = f"{y:02d}{x:02d}{toy:02d}{tox:02d}"
                            if is_valid_she_move(state_list, y, x, toy, tox):
                                if change_state(state_list, m) != old_state_list:
                                    moves.append(m)
                            # 如果遇到棋子，根据规则决定是否继续
                            if state_list[toy][tox] != '一一':
                                break
                        else:
                            break

    moves_id = []
    for move in moves:
        if move in move_action2move_id:
            moves_id.append(move_action2move_id[move])
    return moves_id


# 辅助函数：检查车的移动是否合法
def is_valid_rook_move(state_list, from_y, from_x, to_y, to_x):
    if from_y != to_y and from_x != to_x:
        return False  # 车只能横或竖移动

    # 检查目标位置是否有己方棋子
    target_piece = state_list[to_y][to_x]
    from_piece = state_list[from_y][from_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    # 检查路径上是否有棋子
    if from_y == to_y:  # 横向移动
        start, end = min(from_x, to_x), max(from_x, to_x)
        for x in range(start + 1, end):
            if state_list[from_y][x] != '一一':
                return False
    else:  # 纵向移动
        start, end = min(from_y, to_y), max(from_y, to_y)
        for y in range(start + 1, end):
            if state_list[y][from_x] != '一一':
                return False

    return True


# 辅助函数：检查马的移动是否合法
def is_valid_horse_move(state_list, from_y, from_x, to_y, to_x):
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)

    # 检查是否为日字走法
    if not ((row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)):
        return False

    # 检查马腿是否被蹩
    if row_diff == 2:  # 竖着走日字
        block_y = from_y + (1 if to_y > from_y else -1)
        if state_list[block_y][from_x] != '一一':
            return False
    elif col_diff == 2:  # 横着走日字
        block_x = from_x + (1 if to_x > from_x else -1)
        if state_list[from_y][block_x] != '一一':
            return False

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    return True


# 辅助函数：检查象的移动是否合法
def is_valid_elephant_move(state_list, from_y, from_x, to_y, to_x):
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)

    # 检查是否为田字走法
    if row_diff != 2 or col_diff != 2:
        return False

    # 检查象眼是否被塞
    center_y = (from_y + to_y) // 2
    center_x = (from_x + to_x) // 2
    if state_list[center_y][center_x] != '一一':
        return False

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    return True


# 辅助函数：检查士的移动是否合法
def is_valid_advisor_move(state_list, from_y, from_x, to_y, to_x):
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)

    # 士只能斜走一格
    if row_diff != 1 or col_diff != 1:
        return False

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    return True


# 辅助函数：检查将/帅的移动是否合法
def is_valid_king_move(state_list, from_y, from_x, to_y, to_x):
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)

    # 将/帅只能移动一格（包括斜向）
    if row_diff > 1 or col_diff > 1 or (row_diff == 0 and col_diff == 0):
        return False

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    return True


# 辅助函数：检查炮的移动是否合法
def is_valid_cannon_move(state_list, from_y, from_x, to_y, to_x):
    if from_y != to_y and from_x != to_x:
        return False  # 炮只能横或竖移动

    # 检查路径上的棋子数量
    pieces_in_path = 0
    if from_y == to_y:  # 横向移动
        start, end = min(from_x, to_x), max(from_x, to_x)
        for x in range(start + 1, end):
            if state_list[from_y][x] != '一一':
                pieces_in_path += 1
    else:  # 纵向移动
        start, end = min(from_y, to_y), max(from_y, to_y)
        for y in range(start + 1, end):
            if state_list[y][from_x] != '一一':
                pieces_in_path += 1

    # 检查目标位置
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]

    # 如果目标位置有棋子，必须正好有一个炮架才能吃子
    if target_piece != '一一':
        return pieces_in_path == 1 and not same_color(from_piece, target_piece)
    else:
        # 移动时不能有棋子阻挡
        return pieces_in_path == 0


# 辅助函数：检查甲/胄的移动是否合法
def is_valid_jia_move(state_list, from_y, from_x, to_y, to_x):
    if from_y != to_y and from_x != to_x:
        return False  # 甲/胄只能横或竖移动

    # 目标位置必须为空
    if state_list[to_y][to_x] != '一一':
        return False

    # 检查路径上是否有棋子阻挡
    pieces_in_path = 0
    if from_y == to_y:  # 横向移动
        start, end = min(from_x, to_x), max(from_x, to_x)
        for x in range(start + 1, end):
            if state_list[from_y][x] != '一一':
                pieces_in_path += 1
    else:  # 纵向移动
        start, end = min(from_y, to_y), max(from_y, to_y)
        for y in range(start + 1, end):
            if state_list[y][from_x] != '一一':
                pieces_in_path += 1

    # 移动时不能有棋子阻隔
    return pieces_in_path == 0


# 辅助函数：检查檑/礌的移动是否合法
def is_valid_lei_move(state_list, from_y, from_x, to_y, to_x):
    row_diff = to_y - from_y
    col_diff = to_x - from_x

    # 必须是直线或斜线移动
    if not (row_diff == 0 or col_diff == 0 or abs(row_diff) == abs(col_diff)):
        return False

    # 检查路径上是否有棋子
    if row_diff == 0:  # 横向移动
        step = 1 if col_diff > 0 else -1
        for x in range(from_x + step, to_x, step):
            if state_list[from_y][x] != '一一':
                return False
    elif col_diff == 0:  # 纵向移动
        step = 1 if row_diff > 0 else -1
        for y in range(from_y + step, to_y, step):
            if state_list[y][from_x] != '一一':
                return False
    else:  # 斜向移动
        y_step = 1 if row_diff > 0 else -1
        x_step = 1 if col_diff > 0 else -1
        y, x = from_y + y_step, from_x + x_step
        while y != to_y and x != to_x:
            if state_list[y][x] != '一一':
                return False
            y += y_step
            x += x_step

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    return True


# 辅助函数：检查尉/衛的移动是否合法
def is_valid_wei_move(state_list, from_y, from_x, to_y, to_x):
    if from_y != to_y and from_x != to_x:
        return False  # 尉/衛暂时按直线移动

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    # 检查路径上是否有棋子（根据具体规则实现）
    if from_y == to_y:  # 横向移动
        start, end = min(from_x, to_x), max(from_x, to_x)
        for x in range(start + 1, end):
            if state_list[from_y][x] != '一一':
                return False
    else:  # 纵向移动
        start, end = min(from_y, to_y), max(from_y, to_y)
        for y in range(start + 1, end):
            if state_list[y][from_x] != '一一':
                return False

    return True


# 辅助函数：检查射/䠶的移动是否合法
def is_valid_she_move(state_list, from_y, from_x, to_y, to_x):
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)

    # 射/䠶只能斜向移动
    if row_diff != col_diff or row_diff == 0:
        return False

    # 检查目标位置是否有己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一' and same_color(from_piece, target_piece):
        return False

    # 检查路径上是否有棋子
    y_step = 1 if to_y > from_y else -1
    x_step = 1 if to_x > from_x else -1

    current_y, current_x = from_y + y_step, from_x + x_step
    while current_y != to_y and current_x != to_x:
        if state_list[current_y][current_x] != '一一':
            return False
        current_y += y_step
        current_x += x_step

    return True


# 辅助函数：判断两个棋子是否同色
def same_color(piece1, piece2):
    return ('红' in piece1 and '红' in piece2) or ('黑' in piece1 and '黑' in piece2)


# 棋盘逻辑控制
class Board(object):

    def __init__(self):
        self.state_list = copy.deepcopy(state_list_init)
        self.game_start = False
        self.winner = None
        self.state_deque = copy.deepcopy(state_deque_init)

    # 初始化棋盘的方法
    def init_board(self, start_player=1):  # 传入先手玩家的id
        # 增加一个颜色到id的映射字典，id到颜色的映射字典
        # 永远是红方先移动
        self.start_player = start_player

        if start_player == 1:
            self.id2color = {1: '红', 2: '黑'}
            self.color2id = {'红': 1, '黑': 2}
            self.backhand_player = 2
        elif start_player == 2:
            self.id2color = {2: '红', 1: '黑'}
            self.color2id = {'红': 2, '黑': 1}
            self.backhand_player = 1
        # 当前手玩家，也就是先手玩家
        self.current_player_color = self.id2color[start_player]  # 红
        self.current_player_id = self.color2id['红']
        # 初始化棋盘状态
        self.state_list = copy.deepcopy(state_list_init)
        self.state_deque = copy.deepcopy(state_deque_init)
        # 初始化最后落子位置
        self.last_move = -1
        # 记录游戏中吃子的回合数
        self.kill_action = 0
        self.game_start = False
        self.action_count = 0  # 游戏动作计数器
        self.winner = None

    @property
    # 获的当前盘面的所有合法走子集合
    def availables(self):
        return get_legal_moves(self.state_deque, self.current_player_color)

    # 从当前玩家的视角返回棋盘状态，current_state_array: [15, 13, 13]  CHW
    def current_state(self):
        _current_state = np.zeros([15, 13, 13])
        # 使用15个平面来表示棋盘状态
        # 0-10个平面表示棋子位置，1代表红方棋子，-1代表黑方棋子, 队列最后一个盘面
        # 第11个平面表示对手player最近一步的落子位置，走子之前的位置为-1，走子之后的位置为1，其余全部是0
        # 第12个平面表示的是当前player是不是先手player，如果是先手player则整个平面全部为1，否则全部为0
        # 第13-14个平面（共3个）作为额外特征
        _state_array = state_list2state_array(self.state_deque[-1])
        _current_state[:11] = _state_array.transpose([2, 0, 1])  # [11, 13, 13]

        if self.game_start:
            # 解构self.last_move
            if self.last_move >= 0 and self.last_move < len(move_id2move_action):
                move = move_id2move_action[self.last_move]
                start_y = int(move[0:2])
                start_x = int(move[2:4])
                end_y = int(move[4:6])
                end_x = int(move[6:8])
                _current_state[11][start_y][start_x] = -1
                _current_state[11][end_y][end_x] = 1
        # 指出当前是哪个玩家走子
        if self.action_count % 2 == 0:
            _current_state[12][:, :] = 1.0
        else:
            _current_state[12][:, :] = -1.0

        return _current_state

    # 根据move对棋盘状态做出改变
    def do_move(self, move):
        self.game_start = True  # 游戏开始
        self.action_count += 1  # 移动次数加1
        move_action = move_id2move_action[move]
        start_y = int(move_action[0:2])
        start_x = int(move_action[2:4])
        end_y = int(move_action[4:6])
        end_x = int(move_action[6:8])
        state_list = copy.deepcopy(self.state_deque[-1])
        # 判断是否吃子
        if state_list[end_y][end_x] != '一一':
            # 如果吃掉对方的帅，则返回当前的current_player胜利
            self.kill_action = 0
            if self.current_player_color == '黑' and '红汉' in state_list[end_y][end_x]:
                self.winner = self.color2id['黑']
            elif self.current_player_color == '红' and '黑汗' in state_list[end_y][end_x]:
                self.winner = self.color2id['红']
        else:
            self.kill_action += 1
        # 更改棋盘状态
        state_list[end_y][end_x] = state_list[start_y][start_x]
        state_list[start_y][start_x] = '一一'
        self.current_player_color = '黑' if self.current_player_color == '红' else '红'  # 改变当前玩家
        self.current_player_id = 1 if self.current_player_id == 2 else 2
        # 记录最后一次移动的位置
        self.last_move = move
        self.state_deque.append(state_list)

    # 是否产生赢家
    def has_a_winner(self):
        """一共有三种状态，红方胜，黑方胜，平局"""
        if self.winner is not None:
            return True, self.winner
        elif self.kill_action >= CONFIG['kill_action']:  # 平局先手判负
            # return False, -1
            return True, self.backhand_player
        return False, -1

    # 检查当前棋局是否结束
    def game_end(self):
        win, winner = self.has_a_winner()
        if win:
            return True, winner
        elif self.kill_action >= CONFIG['kill_action']:  # 平局，没有赢家
            return True, -1
        return False, -1

    def get_current_player_color(self):
        return self.current_player_color

    def get_current_player_id(self):
        return self.current_player_id


# 在Board类基础上定义Game类，该类用于启动并控制一整局对局的完整流程，并收集对局过程中的数据，以及进行棋盘的展示
class Game(object):

    def __init__(self, board):
        self.board = board

    # 可视化
    def graphic(self, board, player1_color, player2_color):
        print('player1 take: ', player1_color)
        print('player2 take: ', player2_color)
        print_board(state_list2state_array(board.state_deque[-1]))

    # 用于人机对战，人人对战等
    def start_play(self, player1, player2, start_player=1, is_shown=1):
        if start_player not in (1, 2):
            raise Exception('start_player should be either 1 (player1 first) '
                            'or 2 (player2 first)')
        self.board.init_board(start_player)  # 初始化棋盘
        p1, p2 = 1, 2
        player1.set_player_ind(1)
        player2.set_player_ind(2)
        players = {p1: player1, p2: player2}
        if is_shown:
            self.graphic(self.board, player1.player, player2.player)

        while True:
            current_player = self.board.get_current_player_id()  # 红子对应的玩家id
            player_in_turn = players[current_player]  # 决定当前玩家的代理
            move = player_in_turn.get_action(self.board)  # 当前玩家代理拿到动作
            self.board.do_move(move)  # 棋盘做出改变
            if is_shown:
                self.graphic(self.board, player1.player, player2.player)
            end, winner = self.board.game_end()
            if end:
                if winner != -1:
                    print("Game end. Winner is", players[winner])
                else:
                    print("Game end. Tie")
                return winner

    # 使用蒙特卡洛树搜索开始自我对弈，存储游戏状态（状态，蒙特卡洛落子概率，胜负手）三元组用于神经网络训练
    def start_self_play(self, player, is_shown=False, temp=1e-3):
        self.board.init_board()  # 初始化棋盘, start_player=1
        p1, p2 = 1, 2
        states, mcts_probs, current_players = [], [], []
        # 开始自我对弈
        _count = 0
        while True:
            _count += 1
            if _count % 20 == 0:
                start_time = time.time()
                move, move_probs = player.get_action(self.board,
                                                     temp=temp,
                                                     return_prob=1)
                print('走一步要花: ', time.time() - start_time)
            else:
                move, move_probs = player.get_action(self.board,
                                                     temp=temp,
                                                     return_prob=1)
            # 保存自我对弈的数据
            states.append(self.board.current_state())
            mcts_probs.append(move_probs)
            current_players.append(self.board.current_player_id)
            # 执行一步落子
            self.board.do_move(move)
            end, winner = self.board.game_end()
            if end:
                # 从每一个状态state对应的玩家的视角保存胜负信息
                winner_z = np.zeros(len(current_players))
                if winner != -1:
                    winner_z[np.array(current_players) == winner] = 1.0
                    winner_z[np.array(current_players) != winner] = -1.0
                # 重置蒙特卡洛根节点
                player.reset_player()
                if is_shown:
                    if winner != -1:
                        print("Game end. Winner is:", winner)
                    else:
                        print('Game end. Tie')

                return winner, zip(states, mcts_probs, winner_z)


if __name__ == '__main__':
    # 测试array2string
    # _array = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    # print(array2string(_array))

    """# 测试change_state
    new_state = change_state(state_list_init, move='00000101')
    for row in range(13):
        print(new_state[row])"""

    """# 测试print_board
    _state_list = copy.deepcopy(state_list_init)
    print_board(state_list2state_array(_state_list))"""

    """# 测试get_legal_moves
    moves = get_legal_moves(state_deque_init, current_player_color='黑')
    move_actions = []
    for item in moves:
        if item in move_id2move_action:
            move_actions.append(move_id2move_action[item])
    print(move_actions)"""


    # 测试Board中的start_play
    class Human1:
        def get_action(self, board):
            # print('当前是player1在操作')
            # print(board.current_player_color)
            # move = move_action2move_id[input('请输入')]
            move = random.choice(board.availables)
            return move

        def set_player_ind(self, p):
            self.player = p


    class Human2:
        def get_action(self, board):
            # print('当前是player2在操作')
            # print(board.current_player_color)
            # move = move_action2move_id[input('请输入')]
            move = random.choice(board.availables)
            return move

        def set_player_ind(self, p):
            self.player = p


    human1 = Human1()
    human2 = Human2()
    game = Game(board=Board())
    for i in range(20):
        game.start_play(human1, human2, start_player=2, is_shown=0)
    # board = Board()
    # board.init_board()
