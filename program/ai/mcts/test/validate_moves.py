# coding=utf-8
"""
验证匈汉象棋走子动作合法性的工具
"""

import copy
from mcts_game import get_legal_moves, state_deque_init, change_state, state_list2state_array, print_board


def validate_move_format(move_str):
    """
    验证移动字符串格式是否正确
    格式为"from_y(2位)from_x(2位)to_y(2位)to_x(2位)"
    """
    if len(move_str) != 8:
        return False
    try:
        y1 = int(move_str[0:2])
        x1 = int(move_str[2:4])
        y2 = int(move_str[4:6])
        x2 = int(move_str[6:8])
        
        # 检查坐标是否在有效范围内
        if not all(0 <= coord < 13 for coord in [y1, x1, y2, x2]):
            return False
            
        # 检查起点和终点是否相同
        if (y1, x1) == (y2, x2):
            return False
            
        return True
    except ValueError:
        return False


def validate_specific_move_logic(state_list, move_str, current_player_color):
    """
    验证特定移动是否符合棋子移动规则
    """
    if not validate_move_format(move_str):
        return False, "移动格式不正确"
    
    y1 = int(move_str[0:2])
    x1 = int(move_str[2:4])
    y2 = int(move_str[4:6])
    x2 = int(move_str[6:8])
    
    # 检查起点是否有棋子
    if state_list[y1][x1] == '一一':
        return False, "起点没有棋子"
    
    # 检查棋子颜色是否匹配
    piece = state_list[y1][x1]
    piece_color = '红' if '红' in piece else '黑'
    if piece_color != current_player_color:
        return False, f"棋子颜色不匹配，期望{current_player_color}，实际{piece_color}"
    
    # 获取棋子类型
    piece_type = piece[1:]
    
    # 根据棋子类型验证移动
    if piece_type in ['車', '车']:
        return validate_rook_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['馬', '马']:
        return validate_horse_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['象', '相']:
        return validate_elephant_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['士', '仕']:
        return validate_advisor_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['汉', '汗']:
        return validate_king_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['炮', '砲']:
        return validate_cannon_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['兵', '卒']:
        return validate_pawn_move(state_list, y1, x1, y2, x2, current_player_color)
    elif piece_type in ['檑', '礌']:
        return validate_lei_move(state_list, y1, x1, y2, x2)
    elif piece_type in ['射', '䠶']:
        return validate_she_move(state_list, y1, x1, y2, x2)
    else:
        return False, f"未知棋子类型: {piece_type}"


def validate_rook_move(state_list, from_y, from_x, to_y, to_x):
    """验证车的移动"""
    # 车只能横或竖移动
    if from_y != to_y and from_x != to_x:
        return False, "车只能横或竖移动"
    
    # 检查路径上是否有棋子
    if from_y == to_y:  # 横向移动
        start, end = min(from_x, to_x), max(from_x, to_x)
        for x in range(start + 1, end):
            if state_list[from_y][x] != '一一':
                return False, "车移动路径上有棋子阻挡"
    else:  # 纵向移动
        start, end = min(from_y, to_y), max(from_y, to_y)
        for y in range(start + 1, end):
            if state_list[y][from_x] != '一一':
                return False, "车移动路径上有棋子阻挡"
    
    # 检查目标位置是否为己方棋子
    target_piece = state_list[to_y][to_x]
    from_piece = state_list[from_y][from_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    return True, "车移动合法"


def validate_horse_move(state_list, from_y, from_x, to_y, to_x):
    """验证马的移动"""
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)
    
    # 检查是否为日字走法
    if not ((row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)):
        return False, "马移动不符合日字规则"
    
    # 检查马腿是否被蹩
    if row_diff == 2:  # 竖着走日字
        block_y = from_y + (1 if to_y > from_y else -1)
        if state_list[block_y][from_x] != '一一':
            return False, "马腿被蹩"
    elif col_diff == 2:  # 横着走日字
        block_x = from_x + (1 if to_x > from_x else -1)
        if state_list[from_y][block_x] != '一一':
            return False, "马腿被蹩"
    
    # 检查目标位置是否为己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    return True, "马移动合法"


def validate_elephant_move(state_list, from_y, from_x, to_y, to_x):
    """验证象的移动"""
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)
    
    # 检查是否为田字走法
    if row_diff != 2 or col_diff != 2:
        return False, "象移动不符合田字规则"
    
    # 检查象眼是否被塞
    center_y = (from_y + to_y) // 2
    center_x = (from_x + to_x) // 2
    if state_list[center_y][center_x] != '一一':
        return False, "象眼被塞"
    
    # 检查目标位置是否为己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    # 检查象是否在己方区域内
    piece_color = '红' if '红' in from_piece else '黑'
    if piece_color == '红':
        # 红方相只能在7-12行活动
        if from_y < 7 or to_y < 7:
            return False, "红象不能离开己方区域"
    else:  # 黑方
        # 黑方相只能在0-5行活动
        if from_y > 5 or to_y > 5:
            return False, "黑象不能离开己方区域"
    
    return True, "象移动合法"


def validate_advisor_move(state_list, from_y, from_x, to_y, to_x):
    """验证士的移动"""
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)
    
    # 士只能斜走一格
    if row_diff != 1 or col_diff != 1:
        return False, "士只能斜走一格"
    
    # 检查目标位置是否为己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    # 确定棋子颜色以判断九宫位置
    piece_color = '红' if '红' in from_piece else '黑'
    
    # 定义九宫格的范围
    if piece_color == '红':
        # 红方九宫：行9-11，列5-7
        palace_rows = [9, 10, 11]
        palace_cols = [5, 6, 7]
    else:  # 黑方
        # 黑方九宫：行1-3，列5-7
        palace_rows = [1, 2, 3]
        palace_cols = [5, 6, 7]
    
    # 检查起始位置是否在九宫内
    if from_y not in palace_rows or from_x not in palace_cols:
        return False, "士必须在九宫内"
    
    # 检查目标位置是否在九宫内
    if to_y not in palace_rows or to_x not in palace_cols:
        return False, "士移动后必须仍在九宫内"
    
    return True, "士移动合法"


def validate_king_move(state_list, from_y, from_x, to_y, to_x):
    """验证将/帅的移动"""
    # 检查目标位置是否为己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    # 确定棋子颜色以判断九宫位置
    piece_color = '红' if '红' in from_piece else '黑'
    
    # 定义九宫格的范围
    if piece_color == '红':
        # 红方九宫：行9-11，列5-7
        palace_rows = [9, 10, 11]
        palace_cols = [5, 6, 7]
    else:  # 黑方
        # 黑方九宫：行1-3，列5-7
        palace_rows = [1, 2, 3]
        palace_cols = [5, 6, 7]
    
    # 检查起始位置是否在九宫内
    if from_y not in palace_rows or from_x not in palace_cols:
        return False, "将/帅必须在九宫内"
    
    # 检查目标位置是否在九宫内
    if to_y not in palace_rows or to_x not in palace_cols:
        return False, "将/帅移动后必须仍在九宫内"
    
    # 将/帅只能移动一格
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)
    
    if (row_diff == 1 and col_diff == 0) or (row_diff == 0 and col_diff == 1):
        return True, "将/帅移动合法"
    else:
        return False, "将/帅只能移动一格（横或竖）"


def validate_cannon_move(state_list, from_y, from_x, to_y, to_x):
    """验证炮的移动"""
    if from_y != to_y and from_x != to_x:
        return False, "炮只能横或竖移动"
    
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
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if pieces_in_path == 1 and from_color != target_color:
            return True, "炮吃子移动合法"
        else:
            return False, f"炮吃子需要恰好一个炮架，实际{pieces_in_path}个"
    else:
        # 移动时不能有棋子阻挡
        if pieces_in_path == 0:
            return True, "炮移动合法"
        else:
            return False, f"炮移动路径上不能有棋子，实际{pieces_in_path}个"


def validate_pawn_move(state_list, from_y, from_x, to_y, to_x, current_player_color):
    """验证兵/卒的移动"""
    # 兵/卒只能移动一格
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)
    
    if row_diff + col_diff != 1:
        return False, "兵/卒只能移动一格"
    
    # 验证移动方向
    if current_player_color == '红':
        # 红兵走法：向前(y减小)或过河后横移
        if to_y >= from_y:
            return False, "红兵只能向前移动"
        if from_y > 6 and from_y <= 6:  # 过河后可横移
            if to_y == from_y and abs(to_x - from_x) == 1:
                pass  # 横移合法
            elif to_y == from_y - 1 and to_x == from_x:
                pass  # 前进合法
            else:
                return False, "红兵过河后移动方向错误"
        elif from_y <= 6:  # 过河后可横移
            if not ((to_y == from_y - 1 and to_x == from_x) or (to_y == from_y and abs(to_x - from_x) == 1)):
                return False, "红兵过河后移动方向错误"
        else:  # 未过河只可前进
            if not (to_y == from_y - 1 and to_x == from_x):
                return False, "红兵未过河不可横移"
    else:  # 黑方
        # 黑卒走法：向前(y增大)或过河后横移
        if to_y <= from_y:
            return False, "黑卒只能向前移动"
        if from_y < 6 and to_y >= 6:  # 过河后可横移
            if not ((to_y == from_y + 1 and to_x == from_x) or (to_y == from_y and abs(to_x - from_x) == 1)):
                return False, "黑卒过河后移动方向错误"
        elif from_y >= 6:  # 过河后可横移
            if not ((to_y == from_y + 1 and to_x == from_x) or (to_y == from_y and abs(to_x - from_x) == 1)):
                return False, "黑卒过河后移动方向错误"
        else:  # 未过河只可前进
            if not (to_y == from_y + 1 and to_x == from_x):
                return False, "黑卒未过河不可横移"
    
    # 检查目标位置是否为己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    return True, "兵/卒移动合法"


def validate_lei_move(state_list, from_y, from_x, to_y, to_x):
    """验证檑的移动"""
    row_diff = to_y - from_y
    col_diff = to_x - from_x
    
    # 必须是直线或斜线移动
    if not (row_diff == 0 or col_diff == 0 or abs(row_diff) == abs(col_diff)):
        return False, "檑只能直线或斜线移动"
    
    # 检查目标位置是否有棋子（吃子）
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    
    # 如果目标位置有棋子，需要判断是否为孤立棋子
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
        
        # 檑只能攻击8邻域内的孤立棋子（距离为1格）
        dist_y = abs(to_y - from_y)
        dist_x = abs(to_x - from_x)
        
        # 如果距离超过1格，则不能吃子
        if dist_y > 1 or dist_x > 1:
            return False, "檑只能吃掉相邻的孤立棋子"
        
        # 检查目标棋子是否孤立（周围没有同色棋子）
        # （此检查在实际实现中会更复杂，这里简化处理）
    
    # 检查路径上是否有棋子（对于非邻接移动）
    if row_diff == 0:  # 横向移动
        step = 1 if col_diff > 0 else -1
        for x in range(from_x + step, to_x, step):
            if state_list[from_y][x] != '一一':
                return False, "檑移动路径上有棋子阻挡"
    elif col_diff == 0:  # 纵向移动
        step = 1 if row_diff > 0 else -1
        for y in range(from_y + step, to_y, step):
            if state_list[y][from_x] != '一一':
                return False, "檑移动路径上有棋子阻挡"
    else:  # 斜向移动
        y_step = 1 if row_diff > 0 else -1
        x_step = 1 if col_diff > 0 else -1
        y, x = from_y + y_step, from_x + x_step
        while y != to_y and x != to_x:
            if state_list[y][x] != '一一':
                return False, "檑移动路径上有棋子阻挡"
            y += y_step
            x += x_step
    
    return True, "檑移动合法"


def validate_she_move(state_list, from_y, from_x, to_y, to_x):
    """验证射的移动"""
    row_diff = abs(to_y - from_y)
    col_diff = abs(to_x - from_x)
    
    # 射只能斜向移动
    if row_diff != col_diff or row_diff == 0:
        return False, "射只能斜向移动"
    
    # 移动距离限制：至多斜向移动3格
    if row_diff > 3:
        return False, "射最多只能斜向移动3格"
    
    # 检查目标位置是否为己方棋子
    from_piece = state_list[from_y][from_x]
    target_piece = state_list[to_y][to_x]
    if target_piece != '一一':
        from_color = '红' if '红' in from_piece else '黑'
        target_color = '红' if '红' in target_piece else '黑'
        if from_color == target_color:
            return False, "不能吃掉己方棋子"
    
    # 检查路径上是否有棋子
    y_step = 1 if to_y > from_y else -1
    x_step = 1 if to_x > from_x else -1
    
    current_y, current_x = from_y + y_step, from_x + x_step
    while current_y != to_y and current_x != to_x:
        if state_list[current_y][current_x] != '一一':
            return False, "射移动路径上有棋子阻挡"
        current_y += y_step
        current_x += x_step
    
    return True, "射移动合法"


def validate_all_moves(moves, state_deque, current_player_color):
    """
    验证一组移动的合法性
    """
    results = []
    
    for move in moves:
        state_list = state_deque[-1]
        is_valid, reason = validate_specific_move_logic(state_list, move, current_player_color)
        results.append({
            'move': move,
            'valid': is_valid,
            'reason': reason
        })
    
    return results


def print_validation_report(validation_results):
    """
    打印验证报告
    """
    print("\n=== 移动验证报告 ===")
    valid_count = sum(1 for r in validation_results if r['valid'])
    total_count = len(validation_results)
    
    print(f"总移动数: {total_count}")
    print(f"合法移动数: {valid_count}")
    print(f"非法移动数: {total_count - valid_count}")
    
    if total_count > 0:
        print(f"合法率: {valid_count / total_count * 100:.2f}%")
    
    print("\n详细结果:")
    for i, result in enumerate(validation_results):
        status = "✓" if result['valid'] else "✗"
        print(f"{status} {result['move']} - {result['reason']}")
        
        if not result['valid']:
            print(f"    详细: 移动 {result['move']} 不合法 - {result['reason']}")


def run_validation_test():
    """
    运行验证测试
    """
    print("开始验证匈汉象棋走子动作的合法性...")
    
    # 获取黑方的合法移动
    black_moves = get_legal_moves(state_deque_init, current_player_color='黑')
    
    # 转换为移动字符串
    move_actions = []
    for item in black_moves:
        if item in globals().get('move_id2move_action', {}):  # 注意：这里需要导入move_id2move_action
            move_actions.append(globals().get('move_id2move_action')[item])
        else:
            # 如果全局变量不可用，我们从mcts_game模块导入
            from program.ai.mcts.mcts_game import move_id2move_action
            if item in move_id2move_action:
                move_actions.append(move_id2move_action[item])
    
    print(f"获取到 {len(move_actions)} 个黑方的移动动作")
    
    # 验证这些移动
    validation_results = validate_all_moves(move_actions, state_deque_init, '黑')
    
    # 打印验证报告
    print_validation_report(validation_results)
    
    # 验证一些具体的移动示例
    print("\n=== 具体示例验证 ===")
    sample_moves = ['00000101', '00000202', '00000303', '00020001', '00020003', '00020102', '00020202', '00020302', '00040003', '00040005', '00040006', '00040007', '00080007', '00080006', '00080005', '00080009', '00100009', '00100011', '00100110', '00100210', '00100310', '00120111', '00120210', '00120309', '01030001', '01030201', '01030302', '01030304', '01040302', '01040306', '01050206', '01070206', '01080306', '01080310', '01090011', '01090211', '01090308', '01090310', '03010300', '03010302', '03010303', '03010304', '03010305', '03010306', '03010307', '03010308', '03010309', '03010310', '03010001', '03010101', '03010201', '03010401', '03010501', '03010601', '03010701', '03010801', '03110302', '03110303', '03110304', '03110305', '03110306', '03110307', '03110308', '03110309', '03110310', '03110312', '03110011', '03110111', '03110211', '03110411', '03110511', '03110611', '03110711', '03110811', '04000500', '04020502', '04040504', '04060506', '04080508', '04100510', '04120512']

    
    for move in sample_moves:
        state_list = state_deque_init[-1]
        is_valid, reason = validate_specific_move_logic(state_list, move, '黑')
        print(f"移动 {move}: {'合法' if is_valid else '非法'} - {reason}")
    
    return validation_results


if __name__ == "__main__":
    run_validation_test()