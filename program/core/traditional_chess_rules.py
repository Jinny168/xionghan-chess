"""传统中国象棋规则模块"""

from program.core.chess_pieces import ChessPiece, Ju, Ma, Xiang, Shi, King, Pao, Pawn


class TraditionalChessRules:
    """传统中国象棋规则类，负责验证移动的合法性和胜负判定"""
    
    @staticmethod
    def get_piece_at(pieces, row, col):
        """获取指定位置的棋子
        
        Args:
            pieces (list): 棋子列表
            row (int): 行坐标
            col (int): 列坐标
            
        Returns:
            ChessPiece or None: 位置上的棋子，如果没有则返回None
        """
        for piece in pieces:
            if piece.row == row and piece.col == col:
                return piece
        return None

    @staticmethod
    def is_valid_move(pieces, piece, from_row, from_col, to_row, to_col):
        """检查移动是否合法（传统象棋规则）
        
        Args:
            pieces (list): 棋子列表
            piece (ChessPiece): 要移动的棋子
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 移动是否合法
        """
        # 检查起始位置是否正确
        if piece.row != from_row or piece.col != from_col:
            return False
        
        # 检查目标位置是否在棋盘范围内（传统象棋棋盘为9x10）
        # 在我们的13x13棋盘中，传统象棋区域为特定范围
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == piece.color:
            return False
        
        # 根据棋子类型检查移动是否符合规则
        if isinstance(piece, Ju):  # 車/车
            return TraditionalChessRules.is_valid_ju_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Ma):  # 馬/马
            return TraditionalChessRules.is_valid_ma_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Xiang):  # 相/象
            return TraditionalChessRules.is_valid_xiang_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Shi):  # 士/仕
            return TraditionalChessRules.is_valid_shi_move(piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, King):  # 将/帅
            return TraditionalChessRules.is_valid_king_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Pao):  # 炮/砲
            return TraditionalChessRules.is_valid_pao_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Pawn):  # 兵/卒
            return TraditionalChessRules.is_valid_pawn_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        
        return False

    @staticmethod
    def is_valid_ju_move(pieces, from_row, from_col, to_row, to_col):
        """检查車/车的移动是否合法（传统象棋规则）"""
        # 車只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == TraditionalChessRules.get_piece_at(pieces, from_row, from_col).color:
            return False

        # 检查路径上是否有其他棋子
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if TraditionalChessRules.get_piece_at(pieces, from_row, col):
                    return False
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if TraditionalChessRules.get_piece_at(pieces, row, from_col):
                    return False
        
        return True

    @staticmethod
    def is_valid_ma_move(pieces, from_row, from_col, to_row, to_col):
        """检查馬/马的移动是否合法（传统象棋规则）"""
        # 计算行列差
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == TraditionalChessRules.get_piece_at(pieces, from_row, from_col).color:
            return False

        # 检查基本移动规则：日字
        if not ((row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)):  # 日字
            return False
        
        # 检查是否有阻挡（蹩马腿）
        if row_diff == 2:  # 竖着走日字，检查横向阻挡
            block_row = from_row + (1 if to_row > from_row else -1)
            if TraditionalChessRules.get_piece_at(pieces, block_row, from_col):
                return False
        elif col_diff == 2:  # 横着走日字，检查纵向阻挡
            block_col = from_col + (1 if to_col > from_col else -1)
            if TraditionalChessRules.get_piece_at(pieces, from_row, block_col):
                return False
        
        return True

    @staticmethod
    def is_valid_xiang_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查相/象的移动是否合法（传统象棋规则）"""
        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False
        
        # 检查是否是正常的田字移动（斜向移动2格，形如"田"）
        if abs(to_row - from_row) != 2 or abs(to_col - from_col) != 2:
            return False
        
        # 检查"塞象眼"
        center_row = (from_row + to_row) // 2
        center_col = (from_col + to_col) // 2
        if TraditionalChessRules.get_piece_at(pieces, center_row, center_col):
            return False  # 被塞象眼
        
        # 检查是否过河（相/象不能过河）
        # 在传统象棋中，红方相的活动范围是底线到河界（下方区域），黑方相的活动范围是河界到顶线（上方区域）
        if color == "red":
            # 红方相：只能在下方区域活动（索引较大的行：5-9）
            if to_row < 5:  # 红方相不能过河（河界在第5行）
                return False
        else:  # color == "black"
            # 黑方相：只能在上方区域活动（索引较小的行：0-4）
            if to_row > 4:  # 黑方相不能过河（河界在第5行）
                return False
        
        return True

    @staticmethod
    def is_valid_shi_move(color, from_row, from_col, to_row, to_col):
        """检查士/仕的移动是否合法（传统象棋规则）"""
        # 检查移动距离是否为一格斜向移动
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        if row_diff != 1 or col_diff != 1:
            return False  # 士/仕只能斜走一格
        
        # 检查目标位置是否在九宫内
        if color == "red":
            # 红方九宫：row 7-9, col 3-5 (0-based: row 7-9, col 3-5)
            in_palace = (7 <= to_row <= 9 and 3 <= to_col <= 5)
        else:  # black
            # 黑方九宫：row 0-2, col 3-5 (0-based: row 0-2, col 3-5)
            in_palace = (0 <= to_row <= 2 and 3 <= to_col <= 5)
        
        if not in_palace:
            return False  # 士/仕不能出九宫
        
        return True

    @staticmethod
    def is_valid_king_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查将/帅的移动是否合法（传统象棋规则）"""
        # 检查是否在棋盘范围内（限制在传统象棋9x10范围内）
        if not (0 <= to_row <= 9 and 0 <= to_col <= 8):
            return False

        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False

        # 检查移动距离是否为一格（横或竖）
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        if not ((row_diff == 1 and col_diff == 0) or (row_diff == 0 and col_diff == 1)):
            return False  # 将/帅只能横竖走一格

        # 检查目标位置是否在九宫内
        if color == "red":
            # 红方九宫：row 7-9, col 3-5 (0-based: row 7-9, col 3-5)
            in_palace = (7 <= to_row <= 9 and 3 <= to_col <= 5)
        else:  # black
            # 黑方九宫：row 0-2, col 3-5 (0-based: row 0-2, col 3-5)
            in_palace = (0 <= to_row <= 2 and 3 <= to_col <= 5)
        
        if not in_palace:
            return False  # 将/帅不能出九宫
        
        # 将帅对脸规则（禁止照面）
        if target_piece and isinstance(target_piece, King) and target_piece.color != color:
            # 检查是否在同一列
            if from_col == to_col:
                # 检查中间是否有其他棋子
                start = min(from_row, to_row) + 1
                end = max(from_row, to_row)
                has_piece_between = False
                for row in range(start, end):
                    if TraditionalChessRules.get_piece_at(pieces, row, from_col):
                        has_piece_between = True
                        break
                
                # 如果中间没有棋子，说明将帅照面，这是不允许的
                if not has_piece_between:
                    return False
        
        return True

    @staticmethod
    def is_valid_pao_move(pieces, from_row, from_col, to_row, to_col):
        """检查炮/砲的移动是否合法（传统象棋规则）"""
        # 炮只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == TraditionalChessRules.get_piece_at(pieces, from_row, from_col).color:
            return False

        # 检查路径上的棋子数量
        pieces_in_path = 0
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if TraditionalChessRules.get_piece_at(pieces, from_row, col):
                    pieces_in_path += 1
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if TraditionalChessRules.get_piece_at(pieces, row, from_col):
                    pieces_in_path += 1
        
        # 吃子时必须有且只有一个炮架
        if target_piece:
            return pieces_in_path == 1
        
        # 移动时不能有棋子阻隔
        return pieces_in_path == 0

    @staticmethod
    def is_valid_pawn_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查兵/卒的移动是否合法（传统象棋规则）"""
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # 检查目标位置是否有己方棋子
        target_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False
            
        # 检查是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
            
        if color == "red":
            # 红方兵移动规则
            # 未过河：只能向前走一格
            # 过河后：可向前、左、右走一格，不能后退
            
            # 检查移动距离是否为一格
            if abs(row_diff) + abs(col_diff) != 1:
                return False  # 兵只能移动一格
            
            # 未过河（row >= 6）时，只能向前走
            if from_row >= 6:
                if col_diff != 0:  # 不能横向移动
                    return False
                if row_diff >= 0:  # 不能后退
                    return False
            else:  # 已过河（row < 6）
                if row_diff > 0:  # 不能后退
                    return False
        
        else:  # black
            # 黑方卒移动规则
            # 未过河：只能向前走一格
            # 过河后：可向前、左、右走一格，不能后退
            
            # 检查移动距离是否为一格
            if abs(row_diff) + abs(col_diff) != 1:
                return False  # 卒只能移动一格
            
            # 未过河（row <= 4）时，只能向前走
            if from_row <= 4:
                if col_diff != 0:  # 不能横向移动
                    return False
                if row_diff <= 0:  # 不能后退
                    return False
            else:  # 已过河（row > 4）
                if row_diff < 0:  # 不能后退
                    return False
        
        return True

    @staticmethod
    def calculate_possible_moves(pieces, piece):
        """计算指定棋子的所有可能移动
        
        Args:
            pieces (list): 棋盘上的所有棋子
            piece (ChessPiece): 要计算移动的棋子
            
        Returns:
            tuple: (可移动位置列表, 可吃子位置列表)
        """
        moves = []
        capturable = []
        
        # 遍历棋盘上的所有位置，但限制在传统象棋的范围内
        for row in range(10):  # 传统象棋棋盘是9x10，所以行范围是0-9
            for col in range(9):  # 列范围是0-8
                if TraditionalChessRules.is_valid_move(pieces, piece, piece.row, piece.col, row, col):
                    target_piece = TraditionalChessRules.get_piece_at(pieces, row, col)
                    if target_piece and target_piece.color != piece.color:
                        capturable.append((row, col))  # 可吃子位置
                    else:
                        moves.append((row, col))  # 可移动位置
        
        # 从可移动位置中移除当前位置
        moves = [(r, c) for (r, c) in moves if (r, c) != (piece.row, piece.col)]
        
        return moves, capturable

    @staticmethod
    def would_be_in_check_after_move(pieces, piece, to_row, to_col):
        """检查移动后是否会处于将军状态（模拟移动后检查）
        
        Args:
            pieces (list): 棋盘上的所有棋子
            piece (ChessPiece): 要移动的棋子
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 移动后是否会被将军
        """
        # 模拟移动
        original_row, original_col = piece.row, piece.col
        captured_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
        
        # 移动棋子
        piece.row, piece.col = to_row, to_col
        
        # 如果有棋子被吃掉，暂时移除它
        if captured_piece:
            pieces.remove(captured_piece)
        
        # 检查移动后是否会被将军
        is_in_check = TraditionalChessRules.is_in_check(pieces, piece.color)
        
        # 恢复棋子位置
        piece.row, piece.col = original_row, original_col
        
        # 如果之前吃了棋子，恢复它
        if captured_piece:
            pieces.append(captured_piece)
        
        return is_in_check

    @staticmethod
    def is_in_check(pieces, color):
        """检查指定颜色是否被将军
        
        Args:
            pieces (list): 棋盘上的所有棋子
            color (str): 检查的颜色 ("red" 或 "black")
            
        Returns:
            bool: 是否被将军
        """
        # 找到将/帅的位置
        king_pos = None
        for piece in pieces:
            if isinstance(piece, King) and piece.color == color:
                king_pos = (piece.row, piece.col)
                break
        
        if not king_pos:
            return False  # 没有将/帅，不算将军
        
        # 检查敌方棋子是否能吃到将/帅
        enemy_color = "black" if color == "red" else "red"
        for piece in pieces:
            if piece.color == enemy_color:
                if TraditionalChessRules.is_valid_move(pieces, piece, piece.row, piece.col, king_pos[0], king_pos[1]):
                    return True  # 敌方棋子可以吃到将/帅，说明被将军
        
        return False

    @staticmethod
    def is_checkmate(pieces, color):
        """检查指定颜色是否被将死
        
        Args:
            pieces (list): 棋盘上的所有棋子
            color (str): 检查的颜色 ("red" 或 "black")
            
        Returns:
            bool: 是否被将死
        """
        # 首先检查是否被将军
        if not TraditionalChessRules.is_in_check(pieces, color):
            return False
        
        # 尝试所有可能的移动，看是否能解除将军
        for piece in pieces:
            if piece.color == color:
                moves, capturable = TraditionalChessRules.calculate_possible_moves(pieces, piece)
                all_moves = moves + capturable
                
                for to_row, to_col in all_moves:
                    # 模拟移动
                    original_row, original_col = piece.row, piece.col
                    captured_piece = TraditionalChessRules.get_piece_at(pieces, to_row, to_col)
                    
                    # 移动棋子
                    piece.row, piece.col = to_row, to_col
                    
                    # 如果有棋子被吃掉，暂时移除它
                    if captured_piece:
                        pieces.remove(captured_piece)
                    
                    # 检查移动后是否还被将军
                    still_in_check = TraditionalChessRules.is_in_check(pieces, color)
                    
                    # 恢复棋子位置
                    piece.row, piece.col = original_row, original_col
                    
                    # 如果之前吃了棋子，恢复它
                    if captured_piece:
                        pieces.append(captured_piece)
                    
                    if not still_in_check:
                        return False  # 找到了解将的方法，不是将死
        
        return True  # 所有可能的移动都无法解将，被将死

    @staticmethod
    def is_stalemate(pieces, color):
        """检查是否为困毙（无子可动但未被将军）
        
        Args:
            pieces (list): 棋盘上的所有棋子
            color (str): 检查的颜色 ("red" 或 "black")
            
        Returns:
            bool: 是否为困毙
        """
        # 如果被将军，不是困毙
        if TraditionalChessRules.is_in_check(pieces, color):
            return False
        
        # 检查是否有任何合法移动
        for piece in pieces:
            if piece.color == color:
                moves, capturable = TraditionalChessRules.calculate_possible_moves(pieces, piece)
                all_moves = moves + capturable
                
                if all_moves:  # 找到了至少一个合法移动
                    return False
        
        return True  # 没有任何合法移动，且未被将军，是困毙

    @staticmethod
    def has_insufficient_material(pieces):
        """检查是否为不可能取胜的简单局势（传统象棋规则）
        
        Args:
            pieces (list): 棋盘上的所有棋子
            
        Returns:
            bool: 是否为不可能取胜的简单局势
        """
        # 统计双方剩余棋子
        red_pieces = [p for p in pieces if p.color == "red"]
        black_pieces = [p for p in pieces if p.color == "black"]
        
        # 如果任一方还有车、炮、兵等强力棋子，通常不是简单局势
        for piece_list in [red_pieces, black_pieces]:
            for piece in piece_list:
                if isinstance(piece, (Ju, Pao)):  # 車或炮
                    return False
                if isinstance(piece, Pawn):  # 兵/卒
                    return False
        
        # 检查剩余棋子是否都是王、士、象等
        red_types = set(type(p).__name__ for p in red_pieces)
        black_types = set(type(p).__name__ for p in black_pieces)
        
        # 如果双方都只剩将/帅、士/仕、相/象，可能是简单局势
        valid_types = {King.__name__, Shi.__name__, Xiang.__name__}
        
        red_simple = red_types.issubset(valid_types)
        black_simple = black_types.issubset(valid_types)
        
        if red_simple and black_simple:
            # 如果双方都只有将/帅、士/仕、相/象，且都没有足够的子力取胜
            # 比如单将对单将，将+士对将等
            red_non_kings = [p for p in red_pieces if not isinstance(p, King)]
            black_non_kings = [p for p in black_pieces if not isinstance(p, King)]
            
            # 如果双方都没有其他棋子，或者只有一些不足以取胜的棋子组合
            if len(red_non_kings) <= 2 and len(black_non_kings) <= 2:
                # 例如：将帅对将帅，或将帅士对将帅等
                return True
        
        return False

    @staticmethod
    def is_repeated_move(pieces, move_history, current_player, max_repeats=3):
        """检查是否出现重复局面（传统象棋规则中的"长将作和"等）
        
        Args:
            pieces (list): 棋盘上的所有棋子
            move_history (list): 移动历史记录
            current_player (str): 当前玩家颜色
            max_repeats (int): 最大重复次数，超过此数则判和
            
        Returns:
            bool: 是否出现重复局面
        """
        if len(move_history) < 8:  # 至少需要4个回合才能形成重复局面
            return False
        
        # 获取最近的移动记录
        recent_history = move_history[-8:]  # 检查最近4个回合
        
        # 检查是否是长将（连续将军）
        consecutive_checks = 0
        for i in range(len(recent_history)-1, -1, -1):
            move = recent_history[i]
            # 检查移动后是否形成将军
            # 为简化，这里只做基本的重复移动检测
        
        # 检查局面重复：棋子位置是否重复出现
        # 创建局面表示
        def get_position_hash(pieces_list):
            # 创建棋盘状态的字符串表示
            board_state = [['' for _ in range(9)] for _ in range(10)]  # 9x10棋盘
            for piece in pieces_list:
                if 0 <= piece.row < 10 and 0 <= piece.col < 9:  # 限制在传统象棋范围内
                    board_state[piece.row][piece.col] = f"{piece.color}_{piece.name}"
            return str(board_state)
        
        # 获取当前局面
        current_pos_hash = get_position_hash(pieces)
        
        # 检查历史中是否出现过相同局面
        repeated_count = 0
        # 从较远的历史开始检查，以避免最近的移动干扰
        check_start_idx = max(0, len(move_history) - 10)  # 检查最近10步之外的局面
        for i in range(check_start_idx, len(move_history) - 2, 2):  # 隔一步检查（同一方的回合）
            # 这里我们需要模拟移动来重建历史局面
            # 为简化，我们只检查最后几次移动是否形成循环
            pass
        
        # 更实用的重复检测：检查连续的移动是否形成循环
        if len(recent_history) >= 6:
            # 检查是否出现AB-BA模式（来回移动）
            for i in range(len(recent_history) - 3):
                move1 = recent_history[i]
                move2 = recent_history[i + 2]  # 隔一个回合
                if (move1['piece'].name == move2['piece'].name and
                    move1['piece'].color == move2['piece'].color and
                    move1['from'] == move2['to'] and
                    move1['to'] == move2['from']):
                    return True  # 发现重复移动模式
        
        return False

    @staticmethod
    def is_fifty_move_rule(move_history_without_capture_or_pawn, max_moves=60):
        """检查是否满足六十步自然限着（传统象棋规则中的自然限着）
        
        Args:
            move_history_without_capture_or_pawn (int): 无吃子和兵移动的步数
            max_moves (int): 最大步数限制
            
        Returns:
            bool: 是否达到自然限着
        """
        return move_history_without_capture_or_pawn >= max_moves

    @staticmethod
    def is_game_over(pieces, current_player, move_history=None, move_count_without_capture_or_pawn=0):
        """检查游戏是否结束
        
        Args:
            pieces (list): 棋盘上的所有棋子
            current_player (str): 当前玩家颜色
            move_history (list): 移动历史记录
            move_count_without_capture_or_pawn (int): 无吃子和兵移动的步数
            
        Returns:
            tuple: (游戏是否结束, 获胜方或None)
        """
        # 检查将死
        if TraditionalChessRules.is_checkmate(pieces, current_player):
            # 当前玩家被将死，对方获胜
            winner = "black" if current_player == "red" else "red"
            return True, winner
        
        # 检查困毙
        if TraditionalChessRules.is_stalemate(pieces, current_player):
            # 困毙为和棋
            return True, None
        
        # 检查简单局势
        if TraditionalChessRules.has_insufficient_material(pieces):
            # 简单局势为和棋
            return True, None
        
        # 检查重复局面
        if move_history and TraditionalChessRules.is_repeated_move(move_history, current_player):
            # 重复局面为和棋
            return True, None
        
        # 检查自然限着
        if TraditionalChessRules.is_fifty_move_rule(move_count_without_capture_or_pawn):
            # 自然限着为和棋
            return True, None
        
        return False, None
