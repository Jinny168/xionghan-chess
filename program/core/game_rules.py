from program.core.chess_pieces import ChessPiece, Ju, Ma, Xiang, Shi, King, Pao, Pawn, Wei, She, Lei, Jia, Ci, Dun, Xun
from program.config.config import game_config

class GameRules:
    """匈汉象棋游戏规则类，负责验证移动的合法性和胜负判定"""
    
    # 特殊规则设置
    king_can_leave_palace = game_config.get_setting("king_can_leave_palace", True)  # 汉/汗是否可以出九宫
    king_lose_diagonal_outside_palace = game_config.get_setting("king_lose_diagonal_outside_palace", True)  # 汉/汗出九宫后是否失去斜走能力
    king_can_diagonal_in_palace = game_config.get_setting("king_can_diagonal_in_palace", True)  # 汉/汗在九宫内是否可以斜走
    shi_can_leave_palace = game_config.get_setting("shi_can_leave_palace", True)  # 士是否可以出九宫
    shi_gain_straight_outside_palace = game_config.get_setting("shi_gain_straight_outside_palace", True)  # 士出九宫后是否获得直走能力
    xiang_can_cross_river = game_config.get_setting("xiang_can_cross_river", True)  # 相是否可以过河
    xiang_gain_jump_two_outside_river = game_config.get_setting("xiang_gain_jump_two_outside_river", True)  # 相过河后是否获得隔两格吃子能力
    ma_can_straight_three = game_config.get_setting("ma_can_straight_three", True)  # 马是否可以获得直走三格的能力
    pawn_backward_at_base_enabled = game_config.get_setting("pawn_backward_at_base_enabled", False)  # 兵/卒底线后退能力
    pawn_full_movement_at_base_enabled = game_config.get_setting("pawn_full_movement_at_base_enabled", False)  # 兵/卒底线完整移动能力
    # 棋子登场设置
    ju_appear = game_config.get_setting("ju_appear", True)      # 車/车登场
    ma_appear = game_config.get_setting("ma_appear", True)      # 馬/马登场
    xiang_appear = game_config.get_setting("xiang_appear", True)   # 相/象登场
    shi_appear = game_config.get_setting("shi_appear", True)     # 士/仕登场
    king_appear = game_config.get_setting("king_appear", True)    # 将/帅/汉/汗登场
    pao_appear = game_config.get_setting("pao_appear", True)     # 炮/砲登场
    pawn_appear = game_config.get_setting("pawn_appear", True)    # 兵/卒登场
    wei_appear = game_config.get_setting("wei_appear", True)     # 尉/衛登场
    she_appear = game_config.get_setting("she_appear", True)     # 射/䠶登场
    lei_appear = game_config.get_setting("lei_appear", True)     # 檑/礌登场
    jia_appear = game_config.get_setting("jia_appear", True)     # 甲/胄登场
    ci_appear = game_config.get_setting("ci_appear", True)      # 刺登场
    dun_appear = game_config.get_setting("dun_appear", True)     # 盾登场

    @staticmethod
    def set_game_settings(settings):
        """设置游戏规则参数
        
        Args:
            settings (dict): 游戏规则设置字典
        """
        # 特殊规则设置
        if "king_can_leave_palace" in settings:
            GameRules.king_can_leave_palace = settings["king_can_leave_palace"]
        if "king_lose_diagonal_outside_palace" in settings:
            GameRules.king_lose_diagonal_outside_palace = settings["king_lose_diagonal_outside_palace"]
        if "king_can_diagonal_in_palace" in settings:
            GameRules.king_can_diagonal_in_palace = settings["king_can_diagonal_in_palace"]
        if "shi_can_leave_palace" in settings:
            GameRules.shi_can_leave_palace = settings["shi_can_leave_palace"]
        if "shi_gain_straight_outside_palace" in settings:
            GameRules.shi_gain_straight_outside_palace = settings["shi_gain_straight_outside_palace"]
        if "xiang_can_cross_river" in settings:
            GameRules.xiang_can_cross_river = settings["xiang_can_cross_river"]
        if "xiang_gain_jump_two_outside_river" in settings:
            GameRules.xiang_gain_jump_two_outside_river = settings["xiang_gain_jump_two_outside_river"]
        if "ma_can_straight_three" in settings:
            GameRules.ma_can_straight_three = settings["ma_can_straight_three"]
        if "pawn_backward_at_base_enabled" in settings:
            GameRules.pawn_backward_at_base_enabled = settings["pawn_backward_at_base_enabled"]
        if "pawn_full_movement_at_base_enabled" in settings:
            GameRules.pawn_full_movement_at_base_enabled = settings["pawn_full_movement_at_base_enabled"]

        # 棋子登场设置
        if "ju_appear" in settings:
            GameRules.ju_appear = settings["ju_appear"]
        if "ma_appear" in settings:
            GameRules.ma_appear = settings["ma_appear"]
        if "xiang_appear" in settings:
            GameRules.xiang_appear = settings["xiang_appear"]
        if "shi_appear" in settings:
            GameRules.shi_appear = settings["shi_appear"]
        if "king_appear" in settings:
            GameRules.king_appear = settings["king_appear"]
        if "pao_appear" in settings:
            GameRules.pao_appear = settings["pao_appear"]
        if "pawn_appear" in settings:
            GameRules.pawn_appear = settings["pawn_appear"]
        if "wei_appear" in settings:
            GameRules.wei_appear = settings["wei_appear"]
        if "she_appear" in settings:
            GameRules.she_appear = settings["she_appear"]
        if "lei_appear" in settings:
            GameRules.lei_appear = settings["lei_appear"]
        if "jia_appear" in settings:
            GameRules.jia_appear = settings["jia_appear"]
        if "ci_appear" in settings:
            GameRules.ci_appear = settings["ci_appear"]
        if "dun_appear" in settings:
            GameRules.dun_appear = settings["dun_appear"]
        if "xun_appear" in settings:
            GameRules.xun_appear = settings["xun_appear"]

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
        """检查移动是否合法
        
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
        
        # 检查目标位置是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == piece.color:
            return False
        
        # 检查盾的特殊效果：盾不可被吃
        if target_piece and isinstance(target_piece, Dun):
            # 任何棋子都不能吃盾
            return False

        # 检查盾的特殊效果：与己方盾横竖斜相连的敌方棋子禁止执行吃子操作
        # 如果移动的棋子是敌方棋子，并且与己方盾相邻，则不能吃子
        if target_piece and piece.color != GameRules.get_piece_at(pieces, from_row, from_col).color:
            # 检查移动的敌方棋子是否与某个己方盾相邻
            for p in pieces:
                if isinstance(p, Dun) and p.color == GameRules.get_piece_at(pieces, from_row, from_col).color:
                    # 检查该己方盾是否与移动的敌方棋子相邻（8邻域）
                    row_diff = abs(p.row - from_row)
                    col_diff = abs(p.col - from_col)
                    if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):  # 相邻8格
                        # 如果敌方棋子与己方盾相邻，且这次移动是吃子，则不允许
                        return False

        # 检查盾的特殊效果：与敌方盾横竖斜相连的己方棋子禁止执行吃子操作
        # 如果移动的棋子与敌方盾相邻，则不能吃子（丧失攻击能力）
        if target_piece:  # 如果是吃子移动
            for p in pieces:
                if isinstance(p, Dun) and p.color != piece.color:  # 找到敌方盾
                    # 检查移动的棋子是否与敌方盾相邻（8邻域）
                    row_diff = abs(p.row - from_row)
                    col_diff = abs(p.col - from_col)
                    if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):  # 相邻8格
                        # 如果移动的棋子与敌方盾相邻，且这次移动是吃子，则不允许
                        return False

                        pass
                elif isinstance(p, Dun) and p.color != piece.color:
                    # 检查敌方盾是否与移动的棋子相邻（8邻域）
                    row_diff = abs(p.row - from_row)
                    col_diff = abs(p.col - from_col)
                    if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):  # 相邻8格
                        # 如果移动的棋子与敌方盾相邻，且这次移动是吃子，则不允许
                        # 实际上，根据规则，应该是己方棋子与敌方盾相邻时，己方棋子不能吃子
                        if piece.color != p.color:  # 移动的是己方棋子，盾是敌方的
                            pass  # 不限制己方棋子与敌方盾相邻
                        else:  # 移动的是敌方棋子，盾是己方的
                            pass  # 不限制敌方棋子与己方盾相邻
        # 正确的逻辑是：如果敌方棋子与己方盾相邻，则该敌方棋子不能吃子
        if target_piece:  # 如果是吃子移动
            for p in pieces:
                if isinstance(p, Dun) and p.color != target_piece.color:  # 找到与目标棋子颜色不同的盾（即己方盾）
                    # 检查目标棋子（被吃的棋子）是否与己方盾相邻
                    row_diff = abs(p.row - to_row)
                    col_diff = abs(p.col - to_col)
                    if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):  # 相邻8格
                        # 如果目标棋子与己方盾相邻，则不能吃该棋子
                        return False
        
        # 检查是否有被尉/衛照面限制的棋子
        for p in pieces:
            # 检查是否是被尉/衛照面的敌方棋子
            if isinstance(p, Wei) and GameRules.is_facing_enemy(p, pieces):
                facing_target = GameRules.get_facing_piece(p, pieces)
                # 如果移动的正是被照面限制的棋子，且不是尉/衛本身，则不允许移动
                if piece == facing_target:
                    return False
        
        # 根据棋子类型检查移动是否符合规则
        if isinstance(piece, Ju):
            return GameRules.is_valid_ju_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Ma):
            return GameRules.is_valid_ma_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Xiang):
            return GameRules.is_valid_xiang_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Shi):
            return GameRules.is_valid_shi_move(piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, King):
            return GameRules.is_valid_king_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Pao):
            return GameRules.is_valid_pao_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Pawn):
            return GameRules.is_valid_pawn_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Wei):
            return GameRules.is_valid_wei_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, She):
            return GameRules.is_valid_she_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Lei):
            return GameRules.is_valid_lei_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Jia):
            return GameRules.is_valid_jia_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Ci):
            return GameRules.is_valid_ci_move(pieces, piece.color, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Dun):
            return GameRules.is_valid_dun_move(pieces, from_row, from_col, to_row, to_col)
        elif isinstance(piece, Xun):
            return GameRules.is_valid_xun_move(pieces, from_row, from_col, to_row, to_col)
        
        return False
    
    @staticmethod
    def is_valid_ju_move(pieces, from_row, from_col, to_row, to_col):
        """检查车的移动是否合法"""
        # 车只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == GameRules.get_piece_at(pieces, from_row, from_col).color:
            return False

        # 检查路径上是否有其他棋子
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if GameRules.get_piece_at(pieces, from_row, col):
                    return False
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if GameRules.get_piece_at(pieces, row, from_col):
                    return False
        
        return True
    
    @staticmethod
    def can_ju_attack(pieces, from_row, from_col, to_row, to_col):
        """检查车是否能攻击到目标位置（路径检查，不考虑目标位置棋子颜色）
        
        Args:
            pieces (list): 棋子列表
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 是否能攻击到目标位置
        """
        # 车只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查路径上是否有其他棋子
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if GameRules.get_piece_at(pieces, from_row, col):
                    return False
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if GameRules.get_piece_at(pieces, row, from_col):
                    return False
        
        return True

    @staticmethod
    def is_valid_ma_move(pieces, from_row, from_col, to_row, to_col):
        """检查马的移动是否合法"""
        # 计算行列差
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == GameRules.get_piece_at(pieces, from_row, from_col).color:
            return False

        # 检查基本移动规则：日字
        is_normal_ma_move = ((row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2))  # 日字
        
        # 检查是否允许直走三格
        is_straight_three_move = False
        if GameRules.ma_can_straight_three:
            is_straight_three_move = ((row_diff == 3 and col_diff == 0) or (row_diff == 0 and col_diff == 3))  # 直三
        
        # 马移动必须是日字或直三（如果设置允许）
        if not (is_normal_ma_move or is_straight_three_move):
            return False
        
        # 检查是否有阻挡
        if is_normal_ma_move:  # 传统日字走法
            if row_diff == 2:  # 竖着走日字，检查横向阻挡
                block_row = from_row + (1 if to_row > from_row else -1)
                if GameRules.get_piece_at(pieces, block_row, from_col):
                    return False
            elif col_diff == 2:  # 横着走日字，检查纵向阻挡
                block_col = from_col + (1 if to_col > from_col else -1)
                if GameRules.get_piece_at(pieces, from_row, block_col):
                    return False
        elif is_straight_three_move:  # 直三走法
            if row_diff == 3:  # 竖着走直线，检查路径阻挡
                step = 1 if to_row > from_row else -1
                for i in range(1, 3):
                    if GameRules.get_piece_at(pieces, from_row + i * step, from_col):
                        return False
            elif col_diff == 3:  # 横着走直线，检查路径阻挡
                step = 1 if to_col > from_col else -1
                for i in range(1, 3):
                    if GameRules.get_piece_at(pieces, from_row, from_col + i * step):
                        return False
        
        return True
    
    @staticmethod
    def can_ma_attack(pieces, from_row, from_col, to_row, to_col):
        """检查马是否能攻击到目标位置（不考虑目标位置棋子颜色）
        
        Args:
            pieces (list): 棋子列表
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 是否能攻击到目标位置
        """
        # 计算行列差
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        # 检查基本移动规则：日字
        is_normal_ma_move = ((row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2))  # 日字
        
        # 检查是否允许直走三格
        is_straight_three_move = False
        if GameRules.ma_can_straight_three:
            is_straight_three_move = ((row_diff == 3 and col_diff == 0) or (row_diff == 0 and col_diff == 3))  # 直三
        
        # 马攻击必须是日字或直三（如果设置允许）
        if not (is_normal_ma_move or is_straight_three_move):
            return False
        
        # 检查是否有阻挡
        if is_normal_ma_move:  # 传统日字走法
            if row_diff == 2:  # 竖着走日字，检查横向阻挡
                block_row = from_row + (1 if to_row > from_row else -1)
                if GameRules.get_piece_at(pieces, block_row, from_col):
                    return False
            elif col_diff == 2:  # 横着走日字，检查纵向阻挡
                block_col = from_col + (1 if to_col > from_col else -1)
                if GameRules.get_piece_at(pieces, from_row, block_col):
                    return False
        elif is_straight_three_move:  # 直三走法
            if row_diff == 3:  # 竖着走直线，检查路径阻挡
                step = 1 if to_row > from_row else -1
                for i in range(1, 3):
                    if GameRules.get_piece_at(pieces, from_row + i * step, from_col):
                        return False
            elif col_diff == 3:  # 横着走直线，检查路径阻挡
                step = 1 if to_col > from_col else -1
                for i in range(1, 3):
                    if GameRules.get_piece_at(pieces, from_row, from_col + i * step):
                        return False
        
        return True

    @staticmethod
    def is_valid_xiang_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查相/象的移动是否合法（匈汉象棋中相/象可以过河）
        
        当相在敌方区域时，获得横竖隔一格吃子的能力，但也会被塞相眼
        """
        # 获取当前相棋子
        xiang_piece = GameRules.get_piece_at(pieces, from_row, from_col)
        if not xiang_piece:
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False
        
        # 判断相是否可以过河
        can_cross_river = GameRules.xiang_can_cross_river
        
        # 检查是否是正常的田字移动（斜向移动2格，形如"田"）
        if abs(to_row - from_row) == 2 and abs(to_col - from_col) == 2:
            # 正常的田字移动，检查"塞象眼"
            center_row = (from_row + to_row) // 2
            center_col = (from_col + to_col) // 2
            if GameRules.get_piece_at(pieces, center_row, center_col):
                return False  # 被塞象眼
            
            # 检查是否违反过河规则
            if not can_cross_river:
                # 在传统象棋中，红方相的活动范围是底线到河界（下方区域），黑方相的活动范围是河界到顶线（上方区域）
                # 对于13x13的匈汉象棋棋盘，我们假设河界在中间区域，比如第5-8行（索引4-7）
                # 红方相的活动范围：第6-12行（索引5-12）
                # 黑方相的活动范围：第0-6行（索引0-6）
                # 传统象棋中，红相不能过河（不能到黑方区域），黑相不能过河（不能到红方区域）
                
                if color == "red":
                    # 红方相：起始位置应该在下方区域（索引较大的行）
                    # 如果目标位置在上方区域（索引较小的行），则是过河
                    if to_row < 6:  # 6是河界线，红方相不能到索引小于6的行
                        return False
                else:  # color == "black"
                    # 黑方相：起始位置应该在上方区域（索引较小的行）
                    # 如果目标位置在下方区域（索引较大的行），则是过河
                    if to_row > 6:  # 6是河界线，黑方相不能到索引大于6的行
                        return False
            
            return True
        
        # 如果不是田字移动，检查是否是横竖隔一格移动（特殊能力）
        if GameRules.xiang_gain_jump_two_outside_river:
            row_diff = abs(to_row - from_row)
            col_diff = abs(to_col - from_col)
            
            # 检查是否是横竖方向移动2格（隔一格）
            if (row_diff == 2 and col_diff == 0) or (row_diff == 0 and col_diff == 2):
                # 检查中间是否有棋子（塞相眼）
                mid_row = (from_row + to_row) // 2
                mid_col = (from_col + to_col) // 2
                
                # 检查中间是否有棋子
                if GameRules.get_piece_at(pieces, mid_row, mid_col):
                    return False  # 中间有棋子，被塞相眼
                
                # 判断是否在敌方区域
                is_in_enemy_territory = False
                if color == "red":
                    # 红方相在黑方区域（1-6行，即索引0-6）
                    if from_row <= 6:
                        is_in_enemy_territory = True
                else:  # black
                    # 黑方相在红方区域（6-12行，即索引6-12）
                    if from_row >= 6:
                        is_in_enemy_territory = True
                
                # 只有在敌方区域才能使用隔两格的能力
                if is_in_enemy_territory:
                    # 检查是否违反过河规则
                    if not can_cross_river:
                        # 如果不允许过河，这种特殊移动也不应该被允许
                        # 因为这种移动能力只有在过河后才能使用
                        return False
                    
                    # 还需要检查是否存在两个子与相横向相连的情况，使本来可以被吃的隔一格棋子不能被吃
                    # 检查与目标方向垂直的相邻位置是否有棋子
                    if row_diff == 2:  # 垂直移动
                        # 检查水平方向相邻位置
                        for offset in [-1, 1]:
                            adj_col = mid_col + offset
                            if 0 <= adj_col < 13:
                                adj_piece = GameRules.get_piece_at(pieces, mid_row, adj_col)
                                if adj_piece and adj_piece.color != color:  # 敌方棋子
                                    # 检查另一个方向是否有同色棋子
                                    opp_adj_col = mid_col - offset
                                    if 0 <= opp_adj_col < 13:
                                        opp_adj_piece = GameRules.get_piece_at(pieces, mid_row, opp_adj_col)
                                        if opp_adj_piece and opp_adj_piece.color == color:  # 己方棋子
                                            # 两个子与相横向相连，隔一格棋子不能被吃
                                            if not target_piece or target_piece.row == adj_piece.row and abs(target_piece.col - adj_piece.col) == 2:
                                                return False
                    elif col_diff == 2:  # 水平移动
                        # 检查垂直方向相邻位置
                        for offset in [-1, 1]:
                            adj_row = mid_row + offset
                            if 0 <= adj_row < 13:
                                adj_piece = GameRules.get_piece_at(pieces, adj_row, mid_col)
                                if adj_piece and adj_piece.color != color:  # 敌方棋子
                                    # 检查另一个方向是否有同色棋子
                                    opp_adj_row = mid_row - offset
                                    if 0 <= opp_adj_row < 13:
                                        opp_adj_piece = GameRules.get_piece_at(pieces, opp_adj_row, mid_col)
                                        if opp_adj_piece and opp_adj_piece.color == color:  # 己方棋子
                                            # 两个子与相横向相连，隔一格棋子不能被吃
                                            if not target_piece or target_piece.col == adj_piece.col and abs(target_piece.row - adj_piece.row) == 2:
                                                return False
                    
                    return True
        
        # 不符合任何允许的移动方式
        return False

    @staticmethod
    def is_valid_shi_move(color, from_row, from_col, to_row, to_col):
        """检查士/仕的移动是否合法（匈汉象棋中士/仕可以过河）
        
        士/仕移动规则：
        - 在九宫内：可斜走一格
        - 离开九宫：根据设置决定是否增加直走一格的能力
        """
        # 计算移动距离
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # 判断是否在九宫内
        if color == "red":
            in_palace = (9 <= from_row <= 11 and 5 <= from_col <= 7)  # 红方九宫
        else:  # black
            in_palace = (1 <= from_row <= 3 and 5 <= from_col <= 7)   # 黑方九宫
        
        # 检查目标位置是否在九宫内
        if color == "red":
            in_target_palace = (9 <= to_row <= 11 and 5 <= to_col <= 7)  # 红方九宫
        else:  # black
            in_target_palace = (1 <= to_row <= 3 and 5 <= to_col <= 7)   # 黑方九宫
        
        # 如果当前在九宫内，但目标位置在九宫外，且不允许出九宫，则禁止移动
        if in_palace and not in_target_palace and not GameRules.shi_can_leave_palace:
            return False
        
        # 如果当前在九宫外，且不允许出九宫，但目标位置在九宫内，这种情况下允许返回九宫
        # 如果当前在九宫外，且不允许出九宫，且目标位置也在九宫外，则禁止移动
        
        # 检查移动方式是否合法
        is_diagonal_move = (abs(row_diff) == 1 and abs(col_diff) == 1)  # 斜走
        is_horizontal_move = (row_diff == 0 and abs(col_diff) == 1)     # 横走
        is_vertical_move = (abs(row_diff) == 1 and col_diff == 0)       # 竖走
        
        if not is_diagonal_move and not is_horizontal_move and not is_vertical_move:
            # 移动距离不符合规则
            return False
        
        if in_palace:
            # 在九宫内，只允许斜走
            if is_diagonal_move:
                return True
            else:
                return False
        else:
            # 不在九宫内
            if not GameRules.shi_can_leave_palace:
                # 如果不允许出九宫，但当前已经不在九宫内，说明规则设置与当前状态冲突
                # 按照规则，不允许出九宫的士不应该在九宫外，但为了兼容性，我们限制其移动
                # 如果目标位置也在九宫外，不允许移动
                if not in_target_palace:
                    return False
                # 如果目标位置在九宫内，允许返回九宫
                elif in_target_palace:
                    return is_diagonal_move  # 只允许斜走回九宫
            else:
                # 允许出九宫，检查移动规则
                if is_diagonal_move:
                    # 斜走始终允许
                    return True
                elif GameRules.shi_gain_straight_outside_palace and (is_horizontal_move or is_vertical_move):
                    # 如果设置允许出九宫后获得直走能力，且是直走，则允许
                    return True
                else:
                    # 其他情况不允许
                    return False

    @staticmethod
    def is_valid_king_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查将/帅/汉/汗的移动是否合法"""
        # 检查是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False

        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False

        # 计算移动距离
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # 判断是否在九宫内
        if color == "red":
            in_own_palace = (9 <= from_row <= 11 and 5 <= from_col <= 7)  # 红方在自己九宫内
        else:  # black
            in_own_palace = (1 <= from_row <= 3 and 5 <= from_col <= 7)   # 黑方在自己九宫内
        
        # 根据位置应用不同的移动规则
        if in_own_palace:
            # 在九宫内，根据设置决定是否可以斜走
            if GameRules.king_can_diagonal_in_palace:
                # 在九宫内，可以横竖斜走一格
                if max(abs(row_diff), abs(col_diff)) != 1:
                    return False
            else:
                # 在九宫内，只能横竖走一格
                if not ((abs(row_diff) == 1 and col_diff == 0) or (row_diff == 0 and abs(col_diff) == 1)):
                    return False
        else:
            # 在九宫外，根据设置决定是否失去斜走能力
            if GameRules.king_lose_diagonal_outside_palace:
                # 在九宫外，失去斜走能力，只能横竖走一格
                if not ((abs(row_diff) == 1 and col_diff == 0) or (row_diff == 0 and abs(col_diff) == 1)):
                    return False
            else:
                # 在九宫外，仍可斜走一格
                if max(abs(row_diff), abs(col_diff)) != 1:
                    return False
        
        # 检查是否允许汉/汗出九宫
        if not GameRules.king_can_leave_palace:
            # 如果不允许出九宫，判断目标位置是否在九宫内
            if color == "red":
                in_target_palace = (9 <= to_row <= 11 and 5 <= to_col <= 7)  # 红方九宫
            else:  # black
                in_target_palace = (1 <= to_row <= 3 and 5 <= to_col <= 7)   # 黑方九宫
            
            if not in_target_palace:
                return False
        
        # 汉/汗进入敌方九宫直接获胜（在移动合法的基础上）
        if color == "red":  # 红方汉进入黑方九宫(1-3行, 5-7列)获胜
            if 1 <= to_row <= 3 and 5 <= to_col <= 7:
                return True
        else:  # 黑方汗进入红方九宫(9-11行, 5-7列)获胜
            if 9 <= to_row <= 11 and 5 <= to_col <= 7:
                return True
        
        # 将帅对脸规则（禁止照面）
        if target_piece and isinstance(target_piece, King) and target_piece.color != color:
            # 检查是否在同一列
            if from_col == to_col:
                # 检查中间是否有其他棋子
                start = min(from_row, to_row) + 1
                end = max(from_row, to_row)
                has_piece_between = False
                for row in range(start, end):
                    if GameRules.get_piece_at(pieces, row, from_col):
                        has_piece_between = True
                        break
                
                # 如果中间没有棋子，说明将帅照面，这是不允许的，直接返回False
                if not has_piece_between:
                    return False
        
        return True

    @staticmethod
    def is_valid_pao_move(pieces, from_row, from_col, to_row, to_col):
        """检查炮的移动是否合法"""
        # 炮只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == GameRules.get_piece_at(pieces, from_row, from_col).color:
            return False

        # 检查路径上的棋子数量
        pieces_in_path = 0
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if GameRules.get_piece_at(pieces, from_row, col):
                    pieces_in_path += 1
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if GameRules.get_piece_at(pieces, row, from_col):
                    pieces_in_path += 1
        
        # 吃子时必须有且只有一个炮架
        if target_piece:
            return pieces_in_path == 1
        
        # 移动时不能有棋子阻隔
        return pieces_in_path == 0
    
    @staticmethod
    def can_pao_attack(pieces, from_row, from_col, to_row, to_col):
        """检查炮是否能攻击到目标位置（不考虑目标位置棋子颜色）
        
        Args:
            pieces (list): 棋子列表
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 是否能攻击到目标位置
        """
        # 炮只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查路径上的棋子数量
        pieces_in_path = 0
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if GameRules.get_piece_at(pieces, from_row, col):
                    pieces_in_path += 1
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if GameRules.get_piece_at(pieces, row, from_col):
                    pieces_in_path += 1
        
        # 炮攻击必须有且只有一个炮架
        return pieces_in_path == 1
    
    @staticmethod
    def is_valid_pawn_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查兵/卒的移动是否合法（匈汉象棋规则）"""
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False
            
        # 检查是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
            
        if color == "red":
            # 红方兵移动规则
            
            # 1. 未跨越长城阶段（己方半场，未到达敌方阵地，即row > 5）
            if from_row > 5:  # 未跨越长城阴山（红方在第6行及以上，即row > 5）
                # 移动方向：仅能向敌方方向直线走
                if col_diff != 0:  # 不是直线向前
                    return False
                    
                # 检查是否跨越长城（到达row <= 5）
                if to_row <= 5:  # 跨越了长城阴山
                    # 可以进行远距离移动，但不可吃子（如果目标位置有敌子，且移动步数大于1）
                    if target_piece is not None and abs(row_diff) > 1:
                        return False  # 移动步数大于1时不可吃子
                        
                    # 移动距离限制：从当前行到第5行的最大距离
                    max_steps = from_row - 5
                    if abs(row_diff) <= max_steps and row_diff < 0:  # 向前移动，不超过最大步数
                        # 检查路径上是否有阻挡
                        for step in range(1, abs(row_diff) + 1):
                            check_row = from_row + (step * -1)  # 向前移动
                            if GameRules.get_piece_at(pieces, check_row, from_col):
                                # 如果路径有阻挡且移动步数大于1，则不能移动
                                if abs(row_diff) > 1:
                                    return False
                                # 如果路径有阻挡但移动步数为1，可以停在阻挡处（如果目标位置是阻挡）
                                if check_row == to_row:
                                    break  # 可以停在这里
                                else:
                                    return False  # 不能跳过阻挡
                        return True
                else:  # 没有跨越长城
                    # 基础步数：可走1格
                    if row_diff == -1:  # 向前走1格
                        return True
                        
                    # 其他情况不符合未跨越长城的移动规则
                    return False
                
            # 2. 已跨越长城阶段（敌方半场，已过长城，即row <= 5且未到底线）
            elif from_row <= 5 and from_row > 0:  # 已跨越长城但未到底线（第0-5行）
                # 移动方向：保留向前走1格的能力，新增左右横向走1格的能力
                if not (abs(row_diff) <= 1 and abs(col_diff) <= 1 and abs(row_diff) + abs(col_diff) == 1):
                    return False
                    
                # 不能向后移动（远离敌方阵地）
                if row_diff > 0:
                    return False
                    
                return True
                
            # 3. 进入底线阶段（对方最后一行）
            elif from_row == 0:
                # 检查是否启用完整移动能力
                if GameRules.pawn_full_movement_at_base_enabled:
                    # 启用完整移动能力，可以前后左右移动
                    if not (abs(row_diff) <= 1 and abs(col_diff) <= 1 and abs(row_diff) + abs(col_diff) == 1):
                        return False
                elif GameRules.pawn_backward_at_base_enabled:
                    # 启用后退能力，可以前后左右移动
                    if not (abs(row_diff) <= 1 and abs(col_diff) <= 1 and abs(row_diff) + abs(col_diff) == 1):
                        return False
                else:
                    # 不启用特殊能力，只能前左右移动
                    if not (abs(row_diff) <= 1 and abs(col_diff) <= 1 and abs(row_diff) + abs(col_diff) == 1):
                        return False
                    # 不能后退
                    if row_diff > 0:
                        return False
                
                return True
                
        else:  # black
            # 黑方卒移动规则
            
            # 1. 未跨越长城阶段（己方半场，未到达敌方阵地，即row < 7）
            if from_row < 7:  # 未跨越长城阴山（黑方在第6行及以下，即row < 7）
                # 移动方向：仅能向敌方方向直线走
                if col_diff != 0:  # 不是直线向前
                    return False
                    
                # 检查是否跨越长城（到达row >= 7）
                if to_row >= 7:  # 跨越了长城阴山
                    # 可以进行远距离移动，但不可吃子（如果目标位置有敌子，且移动步数大于1）
                    if target_piece is not None and abs(row_diff) > 1:
                        return False  # 移动步数大于1时不可吃子
                        
                    # 移动距离限制：从当前行到第7行的最大距离
                    max_steps = 7 - from_row
                    if abs(row_diff) <= max_steps and row_diff > 0:  # 向前移动，不超过最大步数
                        # 检查路径上是否有阻挡
                        for step in range(1, abs(row_diff) + 1):
                            check_row = from_row + (step * 1)  # 向前移动
                            if GameRules.get_piece_at(pieces, check_row, from_col):
                                # 如果路径有阻挡且移动步数大于1，则不能移动
                                if abs(row_diff) > 1:
                                    return False
                                # 如果路径有阻挡但移动步数为1，可以停在阻挡处（如果目标位置是阻挡）
                                if check_row == to_row:
                                    break  # 可以停在这里
                                else:
                                    return False  # 不能跳过阻挡
                        return True
                else:  # 没有跨越长城
                    # 基础步数：可走1格
                    if row_diff == 1:  # 向前走1格
                        return True
                        
                    # 其他情况不符合未跨越长城的移动规则
                    return False
                
            # 2. 已跨越长城阶段（敌方半场，已过长城，即row >= 7且未到底线）
            elif from_row >= 7 and from_row < 12:  # 已跨越长城但未到底线（第7-11行）
                # 移动方向：保留向前走1格的能力，新增左右横向走1格的能力
                if not (abs(row_diff) <= 1 and abs(col_diff) <= 1 and abs(row_diff) + abs(col_diff) == 1):
                    return False
                    
                # 不能向后移动
                if row_diff < 0:
                    return False
                    
                return True
                
            # 3. 进入底线阶段（对方最后一行）
            elif from_row == 12:
                # 移动方向：前/左/右/后走1格
                if not (abs(row_diff) <= 1 and abs(col_diff) <= 1 and abs(row_diff) + abs(col_diff) == 1):
                    return False
                    
                return True
        
        return True
    
    @staticmethod
    def is_valid_wei_move(pieces, from_row, from_col, to_row, to_col):
        """检查尉/衛的移动是否合法（修改后规则：跳跃过棋子后在碰撞前的区间内移动，支持直线和斜线跨越）"""
        # 获取当前尉棋子
        wei_piece = GameRules.get_piece_at(pieces, from_row, from_col)
        if not wei_piece:
            return False
        
        # 目标位置必须为空（取消吃子能力）
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece:
            return False  # 目标位置不为空，无法跳跃
        
        # 检查目标位置是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
        
        # 不能原地不动
        if from_row == to_row and from_col == to_col:
            return False

        # 检查是否为直线移动（横向或纵向）
        if from_row == to_row or from_col == to_col:
            # 水平移动
            if from_row == to_row:
                # 计算移动方向
                col_diff = to_col - from_col
                step = 1 if col_diff > 0 else -1
                
                # 从起始位置开始，寻找第一个跨越的棋子
                crossed_piece_pos = None
                current_col = from_col + step
                
                # 寻找第一个被跨越的棋子
                while 0 <= current_col < 13 and current_col != to_col:
                    if GameRules.get_piece_at(pieces, from_row, current_col):
                        crossed_piece_pos = current_col
                        break
                    current_col += step
                
                # 如果没有找到被跨越的棋子，无效
                if crossed_piece_pos is None:
                    return False
                
                # 从跨越点的下一个位置开始，检查到目标位置之间是否有棋子
                current_col = crossed_piece_pos + step
                while current_col != to_col:
                    if 0 <= current_col < 13:
                        if GameRules.get_piece_at(pieces, from_row, current_col):
                            # 在跨越棋子后的路径中遇到棋子，无效
                            return False
                    else:
                        # 超出棋盘边界
                        return False
                    current_col += step
                
                # 检查目标位置是否在跨越点之后，且跨越点与目标位置之间没有棋子
                # 确保目标位置在跨越棋子的另一侧
                if step > 0:  # 向右移动
                    if to_col <= crossed_piece_pos:
                        return False
                else:  # 向左移动
                    if to_col >= crossed_piece_pos:
                        return False
                
                return True
            
            # 垂直移动
            elif from_col == to_col:
                # 计算移动方向
                row_diff = to_row - from_row
                step = 1 if row_diff > 0 else -1
                
                # 从起始位置开始，寻找第一个跨越的棋子
                crossed_piece_pos = None
                current_row = from_row + step
                
                # 寻找第一个被跨越的棋子
                while 0 <= current_row < 13 and current_row != to_row:
                    if GameRules.get_piece_at(pieces, current_row, from_col):
                        crossed_piece_pos = current_row
                        break
                    current_row += step
                
                # 如果没有找到被跨越的棋子，无效
                if crossed_piece_pos is None:
                    return False
                
                # 从跨越点的下一个位置开始，检查到目标位置之间是否有棋子
                current_row = crossed_piece_pos + step
                while current_row != to_row:
                    if 0 <= current_row < 13:
                        if GameRules.get_piece_at(pieces, current_row, from_col):
                            # 在跨越棋子后的路径中遇到棋子，无效
                            return False
                    else:
                        # 超出棋盘边界
                        return False
                    current_row += step
                
                # 检查目标位置是否在跨越点之后，且跨越点与目标位置之间没有棋子
                # 确保目标位置在跨越棋子的另一侧
                if step > 0:  # 向下移动
                    if to_row <= crossed_piece_pos:
                        return False
                else:  # 向上移动
                    if to_row >= crossed_piece_pos:
                        return False
                
                return True
        
        # 检查是否为斜线移动
        elif abs(from_row - to_row) == abs(from_col - to_col):
            # 计算移动方向
            row_step = 1 if to_row > from_row else -1
            col_step = 1 if to_col > from_col else -1
            
            # 从起始位置开始，寻找第一个跨越的棋子
            crossed_piece_pos = None
            current_row = from_row + row_step
            current_col = from_col + col_step
            
            # 寻找第一个被跨越的棋子
            # 我们需要确保在到达目标位置之前先遇到一个棋子
            while 0 <= current_row < 13 and 0 <= current_col < 13 and (current_row != to_row or current_col != to_col):
                if GameRules.get_piece_at(pieces, current_row, current_col):
                    crossed_piece_pos = (current_row, current_col)
                    break
                current_row += row_step
                current_col += col_step
            
            # 如果没有找到被跨越的棋子，或者直接到达目标位置而没有跨越棋子，无效
            if crossed_piece_pos is None:
                return False
            
            # 从跨越点的下一个位置开始，检查到目标位置之间是否有棋子
            current_row = crossed_piece_pos[0] + row_step
            current_col = crossed_piece_pos[1] + col_step
            while current_row != to_row or current_col != to_col:
                if 0 <= current_row < 13 and 0 <= current_col < 13:
                    if GameRules.get_piece_at(pieces, current_row, current_col):
                        # 在跨越棋子后的路径中遇到棋子，无效
                        return False
                else:
                    # 超出棋盘边界
                    return False
                current_row += row_step
                current_col += col_step
            
            # 检查目标位置是否在跨越点之后，且跨越点与目标位置之间没有棋子
            # 确保目标位置在跨越棋子的另一侧
            if row_step > 0:  # 向下移动
                if to_row <= crossed_piece_pos[0]:
                    return False
            else:  # 向上移动
                if to_row >= crossed_piece_pos[0]:
                    return False
            
            if col_step > 0:  # 向右移动
                if to_col <= crossed_piece_pos[1]:
                    return False
            else:  # 向左移动
                if to_col >= crossed_piece_pos[1]:
                    return False
            
            return True
        
        return False
    
    @staticmethod
    def is_valid_she_move(pieces, from_row, from_col, to_row, to_col):
        """检查射/䠶的移动是否合法（匈汉象棋规则）"""
        # 射/䠶斜向移动至无碰撞点位
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # 必须斜向移动
        if abs(row_diff) != abs(col_diff):
            return False
            
        # 不能原地不动
        if row_diff == 0 and col_diff == 0:
            return False
            
        # 移动距离限制：至多斜向移动根号18（行变化量绝对值 = 列变化量绝对值 = 3）
        if abs(row_diff) > 3:
            return False
        
        # 检查目标位置是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
            
        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == GameRules.get_piece_at(pieces, from_row, from_col).color:
            return False
        
        # 检查路径上是否有阻挡
        steps = abs(row_diff)
        if steps > 0:  # 确保有移动
            step_row = row_diff // steps
            step_col = col_diff // steps
            
            for i in range(1, steps):
                check_row = from_row + i * step_row
                check_col = from_col + i * step_col
                if GameRules.get_piece_at(pieces, check_row, check_col):
                    return False
        
        return True
    
    @staticmethod
    def is_valid_lei_move(pieces, from_row, from_col, to_row, to_col):
        """检查檑/礌的移动是否合法（匈汉象棋规则）
        
        檑/礌移动规则：
        1. 可以沿直线或斜线无限移动
        2. 不能越过其他棋子
        3. 不能移动到己方棋子位置
        4. 只能攻击落单的敌方棋子，且必须在相邻8格内
        """
        # 获取当前棋子的颜色
        piece = GameRules.get_piece_at(pieces, from_row, from_col)
        if not piece:
            return False
            
        # 检查目标位置是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False
            
        # 不能不动
        if from_row == to_row and from_col == to_col:
            return False
            
        # 计算偏移量
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # 必须是直线或斜线方向
        if not (row_diff == 0 or col_diff == 0 or abs(row_diff) == abs(col_diff)):
            return False
        
        # 检查目标位置是否有棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        
        # 如果目标位置有棋子，判断是否是可攻击的落单敌方棋子
        if target_piece:
            # 不能攻击己方棋子
            if target_piece.color == piece.color:
                return False
                
            # 只能攻击相邻的敌方棋子
            if abs(row_diff) > 1 or abs(col_diff) > 1:
                return False
                
            # 必须是落单的棋子才能攻击
            if not GameRules.is_isolated(target_piece, pieces):
                return False
        else:
            # 如果目标位置为空，检查是否是合法的移动位置（不能是攻击）
            # 检查路径上是否有阻挡
            steps = max(abs(row_diff), abs(col_diff))
            if steps > 1:  # 只有移动超过1格时才需要检查路径
                step_row = 1 if row_diff > 0 else (-1 if row_diff < 0 else 0)
                step_col = 1 if col_diff > 0 else (-1 if col_diff < 0 else 0)
                
                for i in range(1, steps):
                    check_row = from_row + i * step_row
                    check_col = from_col + i * step_col
                    if GameRules.get_piece_at(pieces, check_row, check_col):
                        return False  # 路径上有阻挡
        
        return True
    
    @staticmethod
    def is_valid_jia_move(pieces, from_row, from_col, to_row, to_col):
        """检查甲/胄的移动是否合法（修改后规则：使用炮的移动方式，但仅用于移动，不能直接吃子）
        
        甲/胄移动规则：
        - 横向或纵向移动，类似炮的移动方式
        - 移动时可以无阻挡直线移动任意格
        - 吃子只能通过三子相连（两个己方棋子和一个敌方棋子）
        """
        # 甲/胄只能横向或纵向移动
        if from_row != to_row and from_col != to_col:
            return False
        
        # 检查目标位置是否有棋子（甲/胄不能直接吃子，只能移动到空位置）
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece:  # 目标位置有棋子，甲/胄不能直接移动到有棋子的位置
            return False
        
        # 检查路径上是否有棋子阻挡
        pieces_in_path = 0
        if from_row == to_row:  # 横向移动
            start = min(from_col, to_col) + 1
            end = max(from_col, to_col)
            for col in range(start, end):
                if GameRules.get_piece_at(pieces, from_row, col):
                    pieces_in_path += 1
        else:  # 纵向移动
            start = min(from_row, to_row) + 1
            end = max(from_row, to_row)
            for row in range(start, end):
                if GameRules.get_piece_at(pieces, row, from_col):
                    pieces_in_path += 1
        
        # 移动时不能有棋子阻隔
        return pieces_in_path == 0
    
    @staticmethod
    def is_isolated(piece, pieces):
        """检查敌方棋子是否落单（上下左右四个方向没有同色棋子）
        
        Args:
            piece: 要检查的棋子
            pieces: 棋盘上所有的棋子
            
        Returns:
            bool: 如果棋子落单返回True，否则返回False
        """
        if not piece:
            return False
            
        # 检查四个方向：上、下、左、右
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        row, col = piece.row, piece.col
        
        # 检查每个方向是否有同色棋子
        for dr, dc in directions:
            adjacent_row, adjacent_col = row + dr, col + dc
            
            # 检查相邻位置是否在棋盘范围内
            if 0 <= adjacent_row < 13 and 0 <= adjacent_col < 13:
                adjacent_piece = GameRules.get_piece_at(pieces, adjacent_row, adjacent_col)
                # 如果相邻位置有棋子且颜色相同，则目标棋子不是孤立的
                if adjacent_piece and adjacent_piece.color == piece.color:
                    return False  # 发现相邻的同色棋子，不是孤立的
        
        # 四个方向都没有同色棋子，说明是孤立的
        return True
    
    @staticmethod
    def can_lei_attack(lei_piece, target_piece, pieces):
        """检查檑/礌是否可以攻击目标棋子
        
        檑/礌棋子攻击规则：
        1. 只能攻击敌方棋子
        2. 目标棋子必须是"落单"的（周围上下左右没有同色棋子）
        3. 目标必须在檑/礌周围的8个相邻格子内（包括对角线）
        """
        if not lei_piece or not target_piece:
            return False
            
        # 必须是敌方棋子
        if lei_piece.color == target_piece.color:
            return False
            
        # 目标棋子必须是落单的（周围上下左右没有同色棋子）
        if not GameRules.is_isolated(target_piece, pieces):
            return False
            
        # 目标必须在檑/礌周围的8个相邻格子内（包括对角线），但不能是同一个位置
        row_diff = abs(lei_piece.row - target_piece.row)
        col_diff = abs(lei_piece.col - target_piece.col)
        
        # 检查是否在相邻的8个格子内
        if row_diff > 1 or col_diff > 1 or (row_diff == 0 and col_diff == 0):
            return False
            
        return True

    @staticmethod
    def is_valid_ci_move(pieces, color, from_row, from_col, to_row, to_col):
        """检查刺（拖吃者）的移动是否合法

        刺棋子的规则：
        - 只能直走
        - 移动路径上必须完全无任何棋子阻挡
        - 只能在无障碍的连续区间内移动
        - 目标位置必须为空
        - 移动本身无限制，但只有当移动前起始位置的反方向一格有敌棋时，才能兑掉那个敌棋，敌棋也阵亡，你也阵亡
        - 无法攻击/移除盾棋子
        - 刺若被盾（8邻域敌方盾）阻挡，禁止攻击，无法触发拖吃
        - 被尉照面，禁止移动
        """
        # 目标位置不能有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == color:
            return False

        # 刺只能直线移动（横或竖）
        if from_row != to_row and from_col != to_col:
            return False

        # 检查路径上是否有阻挡
        if from_row == to_row:  # 横向移动
            start_col = min(from_col, to_col)
            end_col = max(from_col, to_col)
            for col in range(start_col + 1, end_col):
                if GameRules.get_piece_at(pieces, from_row, col):
                    return False
        else:  # 纵向移动
            start_row = min(from_row, to_row)
            end_row = max(from_row, to_row)
            for row in range(start_row + 1, end_row):
                if GameRules.get_piece_at(pieces, row, from_col):
                    return False

        # 目标位置必须为空
        if target_piece is not None:
            return False

        # 检查被尉照面的限制
        piece = GameRules.get_piece_at(pieces, from_row, from_col)
        if piece and isinstance(piece, Ci):  # 检查移动的棋子是否是刺
            # 检查是否有敌方尉与当前刺照面
            for p in pieces:
                if isinstance(p, Wei) and p.color != color:  # 敌方尉
                    if GameRules.is_facing_enemy(p, pieces):  # 如果尉与其他棋子照面
                        facing_target = GameRules.get_facing_piece(p, pieces)  # 获取被照面的棋子
                        if facing_target == piece:  # 如果被照面的就是当前刺
                            return False  # 被尉照面的刺禁止移动

        # 检查移动前起始位置的反方向一格是否有敌棋（兑子条件）
        row_diff = to_row - from_row
        col_diff = to_col - from_col

        # 计算起始位置的反方向
        reverse_row = from_row - row_diff
        reverse_col = from_col - col_diff

        # 检查反方向位置是否在棋盘范围内
        if 0 <= reverse_row < 13 and 0 <= reverse_col < 13:
            reverse_piece = GameRules.get_piece_at(pieces, reverse_row, reverse_col)
            # 如果反方向有敌方棋子，那么刺可以移动（但需要后续处理兑子逻辑）
            if reverse_piece and reverse_piece.color != color:
                # 检查是否是盾棋子（不能攻击盾）
                if isinstance(reverse_piece, Dun):
                    return False
                # 检查是否被敌方盾阻挡（8邻域）
                # 检查移动的刺是否与敌方盾相邻
                for p in pieces:
                    if isinstance(p, Dun) and p.color != color:  # 只考虑敌方盾
                        # 检查该敌方盾是否与移动的刺相邻（8邻域）
                        row_diff_to_dun = abs(p.row - from_row)
                        col_diff_to_dun = abs(p.col - from_col)
                        if row_diff_to_dun <= 1 and col_diff_to_dun <= 1 and (
                                row_diff_to_dun != 0 or col_diff_to_dun != 0):
                            # 如果刺与敌方盾相邻，则不能触发拖吃
                            return False
                return True

        # 如果没有满足兑子条件，普通移动也是允许的（只是不触发兑子）
        return True

    @staticmethod
    def is_valid_dun_move(pieces, from_row, from_col, to_row, to_col):
        """检查盾的移动是否合法

        盾棋子的规则：
        - 不可被吃：任何试图移除盾的操作都会被拦截
        - 不能吃子：盾没有任何攻击/吃子逻辑
        - 只能直线跨越移动（移动规则同尉）
        """
        # 目标位置不能有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece:
            return False  # 盾不能吃子，目标位置必须为空

        # 盾的移动规则同尉（直线跨越移动）
        # 只能横向或纵向移动
        if not (from_row == to_row or from_col == to_col):
            return False

        # 不能原地不动
        if from_row == to_row and from_col == to_col:
            return False

        # 检查目标位置是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False

        # 水平移动
        if from_row == to_row:
            step = 1 if to_col > from_col else -1

            # 从起始位置开始，寻找第一个跨越的棋子
            crossed_piece_pos = None
            current_col = from_col + step

            # 寻找第一个被跨越的棋子
            while 0 <= current_col < 13 and current_col != to_col:
                if GameRules.get_piece_at(pieces, from_row, current_col):
                    crossed_piece_pos = current_col
                    break
                current_col += step

            # 如果没有找到被跨越的棋子，无效
            if crossed_piece_pos is None:
                return False

            # 从跨越点的下一个位置开始，检查到目标位置之间是否有棋子
            current_col = crossed_piece_pos + step
            while current_col != to_col:
                if 0 <= current_col < 13:
                    if GameRules.get_piece_at(pieces, from_row, current_col):
                        # 在跨越棋子后的路径中遇到棋子，无效
                        return False
                else:
                    # 超出棋盘边界
                    return False
                current_col += step

            # 检查目标位置是否在跨越点之后，且跨越点与目标位置之间没有棋子
            # 确保目标位置在跨越棋子的另一侧
            if step > 0:  # 向右移动
                if to_col <= crossed_piece_pos:
                    return False
            else:  # 向左移动
                if to_col >= crossed_piece_pos:
                    return False

            return True

        # 垂直移动
        elif from_col == to_col:
            step = 1 if to_row > from_row else -1

            # 从起始位置开始，寻找第一个跨越的棋子
            crossed_piece_pos = None
            current_row = from_row + step

            # 寻找第一个被跨越的棋子
            while 0 <= current_row < 13 and current_row != to_row:
                if GameRules.get_piece_at(pieces, current_row, from_col):
                    crossed_piece_pos = current_row
                    break
                current_row += step

            # 如果没有找到被跨越的棋子，无效
            if crossed_piece_pos is None:
                return False

            # 从跨越点的下一个位置开始，检查到目标位置之间是否有棋子
            current_row = crossed_piece_pos + step
            while current_row != to_row:
                if 0 <= current_row < 13:
                    if GameRules.get_piece_at(pieces, current_row, from_col):
                        # 在跨越棋子后的路径中遇到棋子，无效
                        return False
                else:
                    # 超出棋盘边界
                    return False
                current_row += step

            # 检查目标位置是否在跨越点之后，且跨越点与目标位置之间没有棋子
            # 确保目标位置在跨越棋子的另一侧
            if step > 0:  # 向下移动
                if to_row <= crossed_piece_pos:
                    return False
            else:  # 向上移动
                if to_row >= crossed_piece_pos:
                    return False

            return True

        return False

    @staticmethod
    def is_valid_xun_move(pieces, from_row, from_col, to_row, to_col):
        """检查巡/廵的移动是否合法

        巡/廵规则：
        1. 初始位置：分别置于河界左右两侧最边缘，即第5行和第7行的第0列和第12列
        2. 走法规则：仅能横向移动，不可纵向、斜向移动，也不可越子
        3. 移动格数为任意偶数（2格、4格、6格等），需符合河界的限制
        4. 河界为专属活动区域，不可离开第5行和第7行
        5. 吃子范围限定为自身左右紧邻的第二格，仅2个目标点（左二格、右二格）
        6. 吃子需满足两个条件：一是目标格有敌方棋子，二是移动路径无任何棋子阻挡
        """
        # 获取巡/廵棋子
        xun_piece = GameRules.get_piece_at(pieces, from_row, from_col)
        if not xun_piece or not isinstance(xun_piece, Xun):
            return False

        # 检查目标位置是否在棋盘范围内
        if not (0 <= to_row < 13 and 0 <= to_col < 13):
            return False

        # 巡/廵只能在河界（第5行和第7行）活动，检查是否在河界
        if from_row != 5 and from_row != 7:
            return False

        # 巡/廵只能在河界（第5行和第7行）活动，检查目标位置是否仍在河界
        if to_row != 5 and to_row != 7:
            return False

        # 巡/廵只能横向移动，检查是否改变了行
        if from_row != to_row:
            return False

        # 计算移动的距离
        col_diff = abs(to_col - from_col)

        # 检查是否移动了偶数格（2, 4, 6, 8, 10, 12等）
        if col_diff == 0 or col_diff % 2 != 0:
            return False

        # 检查路径上是否有阻挡
        start_col = min(from_col, to_col)
        end_col = max(from_col, to_col)

        for col in range(start_col + 1, end_col):
            if GameRules.get_piece_at(pieces, from_row, col):
                return False  # 路径上有棋子阻挡

        # 检查目标位置是否有己方棋子
        target_piece = GameRules.get_piece_at(pieces, to_row, to_col)
        if target_piece and target_piece.color == xun_piece.color:
            return False

        # 检查是否是吃子移动
        if target_piece:
            # 巡/廵只能吃左右紧邻的第二格的棋子（即移动2格到达的位置）
            if col_diff == 2:
                # 检查是否是吃子（目标位置有敌方棋子）
                if target_piece.color != xun_piece.color:
                    return True  # 符合吃子规则
                else:
                    return False  # 目标位置是己方棋子，不能移动
            else:
                # 如果不是移动2格，但目标位置有棋子，则不符合规则
                return False

        # 如果目标位置为空，只要符合移动规则即可
        return True
    @staticmethod
    def calculate_possible_moves(pieces, piece):
        """计算棋子所有可能的移动位置
        
        Args:
            pieces (list): 棋子列表
            piece (ChessPiece): 要计算的棋子
            
        Returns:
            list: 可能移动的位置列表 [(row, col), ...]
        """
        moves = []
        capturable = []
        
        # 根据棋子类型优化可能的移动范围
        if isinstance(piece, She):  # 射/䠶，斜向移动，限制在3格范围内
            # 对于射/䠶，限制检查范围
            for dr in range(-3, 4):  # 限制在3格范围内
                for dc in range(-3, 4):
                    # 只有斜向移动
                    if abs(dr) == abs(dc) and (dr != 0 and dc != 0):
                        to_row, to_col = piece.row + dr, piece.col + dc
                        if 0 <= to_row < 13 and 0 <= to_col < 13:  # 在棋盘范围内
                            if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col):
                                # 检查目标位置是否有对方棋子（可吃子）
                                target = GameRules.get_piece_at(pieces, to_row, to_col)
                                if target and target.color != piece.color:
                                    capturable.append((to_row, to_col))
                                moves.append((to_row, to_col))
        elif isinstance(piece, Lei):  # 檑/礌，直线和斜线无限移动
            # 檑/礌可以沿直线和斜线无限移动，需要按方向检查
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]  # 8个方向
            for dr, dc in directions:
                # 沿着方向一直移动直到边界或遇到障碍
                current_row, current_col = piece.row + dr, piece.col + dc
                while 0 <= current_row < 13 and 0 <= current_col < 13:
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, current_row, current_col):
                        target = GameRules.get_piece_at(pieces, current_row, current_col)
                        if target and target.color != piece.color:
                            capturable.append((current_row, current_col))
                        moves.append((current_row, current_col))
                        
                        # 如果目标位置有棋子，停止移动
                        if target is not None:
                            break  # 檑/礌遇到障碍就停止
                    current_row += dr
                    current_col += dc
        elif isinstance(piece, (Ju, Pao, Ci, Dun)):  # 车/炮/刺/盾，直线移动
            # 对于车/炮/刺/盾，只需要沿着4个方向检查
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 上下左右
            for dr, dc in directions:
                # 沿着方向一直移动直到边界或遇到障碍
                current_row, current_col = piece.row + dr, piece.col + dc
                while 0 <= current_row < 13 and 0 <= current_col < 13:
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, current_row, current_col):
                        target = GameRules.get_piece_at(pieces, current_row, current_col)
                        if target and target.color != piece.color:
                            capturable.append((current_row, current_col))
                        moves.append((current_row, current_col))
                        
                        # 如果目标位置有棋子，根据棋子类型决定是否停止
                        if target is not None:
                            if isinstance(piece, Pao):  # 炮的特殊规则
                                # 炮可以越过一个棋子后继续移动，直到遇到第二个棋子
                                current_row += dr
                                current_col += dc
                                while 0 <= current_row < 13 and 0 <= current_col < 13:
                                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, current_row, current_col):
                                        target2 = GameRules.get_piece_at(pieces, current_row, current_col)
                                        if target2:
                                            if target2.color != piece.color:
                                                capturable.append((current_row, current_col))
                                            moves.append((current_row, current_col))
                                            break  # 炮在攻击后停止
                                        else:
                                            moves.append((current_row, current_col))
                                    current_row += dr
                                    current_col += dc
                                break  # 炮在越过一个棋子后停止
                            else:
                                break  # 车、刺、盾遇到障碍就停止
                    current_row += dr
                    current_col += dc
        elif isinstance(piece, Wei):  # 尉，现在支持直线和斜线移动
            # 尉的移动范围包括直线和斜线
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]  # 8个方向
            for dr, dc in directions:
                # 沿着方向一直移动直到边界或遇到障碍
                current_row, current_col = piece.row + dr, piece.col + dc
                while 0 <= current_row < 13 and 0 <= current_col < 13:
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, current_row, current_col):
                        target = GameRules.get_piece_at(pieces, current_row, current_col)
                        if target and target.color != piece.color:
                            capturable.append((current_row, current_col))
                        moves.append((current_row, current_col))
                        
                        # 尉遇到棋子就停止
                        if target is not None:
                            break  # 尉遇到障碍就停止
                    current_row += dr
                    current_col += dc
        elif isinstance(piece, Ma):  # 马，包含传统日字和直走三格
            # 马的所有可能移动位置
            knight_moves = [
                (-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2), (1, 2), (2, -1), (2, 1)
            ]
            
            # 如果设置了马可以直走三格，则添加这些移动
            if GameRules.ma_can_straight_three:
                knight_moves.extend([
                    (-3, 0), (3, 0), (0, -3), (0, 3)  # 直走三格
                ])
            
            for dr, dc in knight_moves:
                to_row, to_col = piece.row + dr, piece.col + dc
                if 0 <= to_row < 13 and 0 <= to_col < 13:  # 在棋盘范围内
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col):
                        target = GameRules.get_piece_at(pieces, to_row, to_col)
                        if target and target.color != piece.color:
                            capturable.append((to_row, to_col))
                        moves.append((to_row, to_col))
        elif isinstance(piece, Xiang):  # 相/象，走田字等
            # 相的可能移动位置
            elephant_moves = [
                (-2, -2), (-2, 2), (2, -2), (2, 2)  # 田字
            ]
            
            # 如果设置了相可以在敌方区域获得隔两格的能力，则添加这些移动
            if GameRules.xiang_gain_jump_two_outside_river:
                # 检查相是否在敌方区域
                is_in_enemy_territory = False
                if piece.color == "red":
                    # 红方相在黑方区域（0-6行）
                    if piece.row <= 6:
                        is_in_enemy_territory = True
                else:  # black
                    # 黑方相在红方区域（6-12行）
                    if piece.row >= 6:
                        is_in_enemy_territory = True
                
                # 如果在敌方区域，添加隔一格直线移动
                if is_in_enemy_territory:
                    elephant_moves.extend([
                        (-2, 0), (2, 0), (0, -2), (0, 2)     # 隔一格直线
                    ])
            else:
                # 如果没开启特殊能力，仍保留基本的隔一格直线移动
                elephant_moves.extend([
                    (-2, 0), (2, 0), (0, -2), (0, 2)     # 隔一格直线
                ])
            
            for dr, dc in elephant_moves:
                to_row, to_col = piece.row + dr, piece.col + dc
                if 0 <= to_row < 13 and 0 <= to_col < 13:  # 在棋盘范围内
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col):
                        target = GameRules.get_piece_at(pieces, to_row, to_col)
                        if target and target.color != piece.color:
                            capturable.append((to_row, to_col))
                        moves.append((to_row, to_col))
        elif isinstance(piece, Shi):  # 士/仕，包含对角线和直线移动
            # 士的可能移动位置（对角线1格）
            advisor_moves = [
                (-1, -1), (-1, 1), (1, -1), (1, 1)
            ]
            
            # 检查士是否在九宫外
            if piece.color == "red":
                in_palace = (9 <= piece.row <= 11 and 5 <= piece.col <= 7)  # 红方九宫
            else:  # black
                in_palace = (1 <= piece.row <= 3 and 5 <= piece.col <= 7)   # 黑方九宫
            
            # 如果士可以离开九宫且设置了出九宫后获得直走能力，则添加直走移动
            if GameRules.shi_can_leave_palace and GameRules.shi_gain_straight_outside_palace and not in_palace:
                # 添加直走移动（横竖各一格）
                advisor_moves.extend([
                    (-1, 0), (1, 0), (0, -1), (0, 1)  # 横竖移动
                ])
            
            for dr, dc in advisor_moves:
                to_row, to_col = piece.row + dr, piece.col + dc
                if 0 <= to_row < 13 and 0 <= to_col < 13:  # 在棋盘范围内
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col):
                        target = GameRules.get_piece_at(pieces, to_row, to_col)
                        if target and target.color != piece.color:
                            capturable.append((to_row, to_col))
                        moves.append((to_row, to_col))
        elif isinstance(piece, King):  # 将/帅/汉/汗
            # 检查是否在九宫内
            if piece.color == "red":
                in_own_palace = (9 <= piece.row <= 11 and 5 <= piece.col <= 7)  # 红方九宫
            else:  # black
                in_own_palace = (1 <= piece.row <= 3 and 5 <= piece.col <= 7)   # 黑方九宫
            
            # 根据位置和设置确定可能的移动
            if in_own_palace:
                # 在九宫内，根据设置决定是否可以斜走
                if GameRules.king_can_diagonal_in_palace:
                    # 在九宫内，可以横竖斜走一格
                    king_moves = [
                        (-1, -1), (-1, 0), (-1, 1),  # 斜向和上
                        (0, -1),           (0, 1),   # 横向
                        (1, -1),  (1, 0),  (1, 1)    # 斜向和下
                    ]
                else:
                    # 在九宫内，只能横竖走一格
                    king_moves = [
                        (-1, 0),           # 上
                        (0, -1), (0, 1),   # 横向
                        (1, 0)             # 下
                    ]
            else:
                # 在九宫外，根据设置决定是否失去斜走能力
                if GameRules.king_lose_diagonal_outside_palace:
                    # 在九宫外，失去斜走能力，只能横竖走一格
                    king_moves = [
                        (-1, 0),           # 上
                        (0, -1), (0, 1),   # 横向
                        (1, 0)             # 下
                    ]
                else:
                    # 在九宫外，仍可斜走一格
                    king_moves = [
                        (-1, -1), (-1, 0), (-1, 1),  # 斜向和上
                        (0, -1),           (0, 1),   # 横向
                        (1, -1),  (1, 0),  (1, 1)    # 斜向和下
                    ]
            
            for dr, dc in king_moves:
                to_row, to_col = piece.row + dr, piece.col + dc
                if 0 <= to_row < 13 and 0 <= to_col < 13:  # 在棋盘范围内
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col):
                        target = GameRules.get_piece_at(pieces, to_row, to_col)
                        if target and target.color != piece.color:
                            capturable.append((to_row, to_col))
                        moves.append((to_row, to_col))
        elif isinstance(piece, Pawn):  # 兵/卒
            # 兵/卒的可能移动位置（根据位置和规则）
            pawn_moves = []
            # 基础移动：向前
            if piece.color == "red":
                # 红方兵移动规则
                if piece.row >= 6:  # 未过河
                    pawn_moves.append((-1, 0))  # 向前1格
                    # 检查是否在初始位置，可以向前2格（需要路径和目标位置都为空）
                    if piece.row == 8:  # 初始位置
                        # 检查中间位置和目标位置是否都为空
                        middle_row = piece.row - 1  # 7
                        target_row = piece.row - 2   # 6
                        if (0 <= middle_row < 13 and 0 <= target_row < 13 and
                            GameRules.get_piece_at(pieces, middle_row, piece.col) is None and
                            GameRules.get_piece_at(pieces, target_row, piece.col) is None):
                            pawn_moves.append((-2, 0))  # 向前2格
                else:  # 已过河
                    if piece.row == 0 and GameRules.pawn_full_movement_at_base_enabled:  # 到达底线且启用完整移动
                        # 底线兵获得前后左右完整移动能力
                        pawn_moves.extend([(-1, 0), (1, 0), (0, -1), (0, 1)])  # 前后左右
                    elif piece.row == 0 and GameRules.pawn_backward_at_base_enabled:  # 到达底线且启用后退能力
                        # 底线兵可后退一格
                        pawn_moves.extend([(-1, 0), (0, -1), (0, 1), (1, 0)])  # 前左右和后退
                    else:  # 过河后但未到底线
                        pawn_moves.extend([(-1, 0), (0, -1), (0, 1)])  # 前左右
            else:  # 黑方
                # 黑方卒移动规则
                if piece.row <= 6:  # 未过河
                    pawn_moves.append((1, 0))  # 向前1格
                    # 检查是否在初始位置，可以向前2格（需要路径和目标位置都为空）
                    if piece.row == 4:  # 初始位置
                        # 检查中间位置和目标位置是否都为空
                        middle_row = piece.row + 1  # 5
                        target_row = piece.row + 2   # 6
                        if (0 <= middle_row < 13 and 0 <= target_row < 13 and
                            GameRules.get_piece_at(pieces, middle_row, piece.col) is None and
                            GameRules.get_piece_at(pieces, target_row, piece.col) is None):
                            pawn_moves.append((2, 0))  # 向前2格
                else:  # 已过河
                    if piece.row == 12 and GameRules.pawn_full_movement_at_base_enabled:  # 到达底线且启用完整移动
                        # 底线卒获得前后左右完整移动能力
                        pawn_moves.extend([(1, 0), (-1, 0), (0, -1), (0, 1)])  # 前后左右
                    elif piece.row == 12 and GameRules.pawn_backward_at_base_enabled:  # 到达底线且启用后退能力
                        # 底线卒可后退一格
                        pawn_moves.extend([(1, 0), (0, -1), (0, 1), (-1, 0)])  # 前左右和后退
                    else:  # 过河后但未到底线
                        pawn_moves.extend([(1, 0), (0, -1), (0, 1)])  # 前左右
            
            for dr, dc in pawn_moves:
                to_row, to_col = piece.row + dr, piece.col + dc
                if 0 <= to_row < 13 and 0 <= to_col < 13:  # 在棋盘范围内
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col):
                        target = GameRules.get_piece_at(pieces, to_row, to_col)
                        if target and target.color != piece.color:
                            capturable.append((to_row, to_col))
                        moves.append((to_row, to_col))
        elif isinstance(piece, Xun):  # 巡/廵，河界专属控场棋子
            # 巡/廵只能在河界（第5行和第7行）横向移动，移动偶数格（2, 4, 6等）
            if piece.row == 5 or piece.row == 7:  # 确保在河界
                # 尝试左右方向移动偶数格
                for step in [2, 4, 6, 8, 10, 12]:  # 移动2, 4, 6, 8, 10, 12格
                    # 向右移动
                    to_col_right = piece.col + step
                    if to_col_right < 13:
                        if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, piece.row, to_col_right):
                            target = GameRules.get_piece_at(pieces, piece.row, to_col_right)
                            if target and target.color != piece.color:
                                capturable.append((piece.row, to_col_right))
                            moves.append((piece.row, to_col_right))
                    
                    # 向左移动
                    to_col_left = piece.col - step
                    if to_col_left >= 0:
                        if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, piece.row, to_col_left):
                            target = GameRules.get_piece_at(pieces, piece.row, to_col_left)
                            if target and target.color != piece.color:
                                capturable.append((piece.row, to_col_left))
                            moves.append((piece.row, to_col_left))
        else:  # 其他情况，遍历所有位置
            # 遍历所有可能的位置
            for row in range(13):
                for col in range(13):
                    # 检查移动是否合法
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, row, col):
                        # 检查目标位置是否有对方棋子（可吃子）
                        target = GameRules.get_piece_at(pieces, row, col)
                        if target and target.color != piece.color:
                            capturable.append((row, col))
                        moves.append((row, col))
        
        # 特殊处理甲/胄的吃子规则
        if isinstance(piece, Jia):
            # 查找可以形成的2己1敌三子横竖连线
            jia_captures = GameRules.find_jia_capture_moves(pieces, piece)
            for captured_piece in jia_captures:
                pos = (captured_piece.row, captured_piece.col)
                if pos not in capturable:
                    capturable.append(pos)
                if pos not in moves:
                    moves.append(pos)
        
        # 特殊处理檑/礌的吃子规则
        if isinstance(piece, Lei):
            # 检查周围8个格子中是否有落单的敌方棋子
            for target_piece in pieces:
                if GameRules.can_lei_attack(piece, target_piece, pieces):
                    pos = (target_piece.row, target_piece.col)
                    if pos not in capturable:
                        capturable.append(pos)
                    if pos not in moves:
                        moves.append(pos)
        
        # 特殊处理刺的兑子规则
        if isinstance(piece, Ci):
            # 刺的移动规则比较特殊，它本身不能吃子，但移动时可能触发兑子
            # 这里我们暂时不做额外处理，因为兑子在move_piece中处理
            pass

        return moves, capturable
    
    @staticmethod
    def find_jia_capture_moves(pieces, jia_piece):
        """查找甲/胄可以吃的子（形成2己1敌三子连线）"""
        captures = []
        color = jia_piece.color
        
        # 检查所有可能的三子连线（水平和垂直）
        
        # 检查水平连线（行不变，列变化）
        for row in range(13):
            for col in range(11):  # 最多检查到第11列，因为需要连续3格
                # 获取三个连续位置的棋子
                piece1 = GameRules.get_piece_at(pieces, row, col)
                piece2 = GameRules.get_piece_at(pieces, row, col + 1)
                piece3 = GameRules.get_piece_at(pieces, row, col + 2)
                
                # 过滤空位置的连线（必须三格都有棋子）
                if None in [piece1, piece2, piece3]:
                    continue
                
                # 统计连线内的棋子构成
                ally_count = 0
                enemy_count = 0
                has_ally_jia = False  # 是否包含己方甲/胄
                
                pieces_list = [piece1, piece2, piece3]
                for piece in pieces_list:
                    if piece.color == color:
                        # 盾不参与甲/胄的连线吃子
                        if isinstance(piece, Dun):
                            # 如果连线中有盾，则此连线不能触发甲/胄的吃子规则
                            ally_count = 0
                            enemy_count = 0
                            break
                        ally_count += 1
                        if isinstance(piece, Jia):  # 己方棋子包含甲/胄
                            has_ally_jia = True
                    else:
                        enemy_count += 1
                
                # 检查连线中的己方棋子是否与敌方盾8邻域相接
                if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                    shield_nearby = False
                    for piece in pieces_list:
                        if piece.color == color:  # 检查己方棋子
                            for shield in pieces:
                                if isinstance(shield, Dun) and shield.color != color:  # 敌方盾
                                    # 检查己方棋子是否与敌方盾相邻（8邻域）
                                    row_diff = abs(shield.row - piece.row)
                                    col_diff = abs(shield.col - piece.col)
                                    if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):
                                        shield_nearby = True
                                        break
                            if shield_nearby:
                                break
                    
                    if shield_nearby:
                        # 如果连线中的己方棋子与敌方盾8邻域相接，则不能触发吃子
                        ally_count = 0
                        enemy_count = 0
                
                # 校验特殊吃子条件：2己1敌 + 包含至少1个己方甲/胄
                if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                    # 找到连线中的敌方棋子，加入捕获列表（去重）
                    enemy_pieces = [p for p in pieces_list if p.color != color]
                    for enemy in enemy_pieces:
                        if enemy not in captures:
                            captures.append(enemy)
        
        # 检查垂直连线（列不变，行变化）
        for col in range(13):
            for row in range(11):  # 最多检查到第11行，因为需要连续3格
                # 获取三个连续位置的棋子
                piece1 = GameRules.get_piece_at(pieces, row, col)
                piece2 = GameRules.get_piece_at(pieces, row + 1, col)
                piece3 = GameRules.get_piece_at(pieces, row + 2, col)
                
                # 过滤空位置的连线（必须三格都有棋子）
                if None in [piece1, piece2, piece3]:
                    continue
                
                # 统计连线内的棋子构成
                ally_count = 0
                enemy_count = 0
                has_ally_jia = False  # 是否包含己方甲/胄
                
                pieces_list = [piece1, piece2, piece3]
                for piece in pieces_list:
                    if piece.color == color:
                        # 盾不参与甲/胄的连线吃子
                        if isinstance(piece, Dun):
                            # 如果连线中有盾，则此连线不能触发甲/胄的吃子规则
                            ally_count = 0
                            enemy_count = 0
                            break
                        ally_count += 1
                        if isinstance(piece, Jia):  # 己方棋子包含甲/胄
                            has_ally_jia = True
                    else:
                        enemy_count += 1
                
                # 检查连线中的己方棋子是否与敌方盾8邻域相接
                if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                    shield_nearby = False
                    for piece in pieces_list:
                        if piece.color == color:  # 检查己方棋子
                            for shield in pieces:
                                if isinstance(shield, Dun) and shield.color != color:  # 敌方盾
                                    # 检查己方棋子是否与敌方盾相邻（8邻域）
                                    row_diff = abs(shield.row - piece.row)
                                    col_diff = abs(shield.col - piece.col)
                                    if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):
                                        shield_nearby = True
                                        break
                            if shield_nearby:
                                break
                    
                    if shield_nearby:
                        # 如果连线中的己方棋子与敌方盾8邻域相接，则不能触发吃子
                        ally_count = 0
                        enemy_count = 0
                
                # 校验特殊吃子条件：2己1敌 + 包含至少1个己方甲/胄
                if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                    # 找到连线中的敌方棋子，加入捕获列表（去重）
                    enemy_pieces = [p for p in pieces_list if p.color != color]
                    for enemy in enemy_pieces:
                        if enemy not in captures:
                            captures.append(enemy)
        
        # 检查对角线方向的连线（斜向连线）
        for row in range(11):  # 最多检查到第11行，因为需要连续3格
            for col in range(11):  # 最多检查到第11列，因为需要连续3格
                # 检查左上到右下的对角线
                piece1 = GameRules.get_piece_at(pieces, row, col)
                piece2 = GameRules.get_piece_at(pieces, row + 1, col + 1)
                piece3 = GameRules.get_piece_at(pieces, row + 2, col + 2)
                
                # 过滤空位置的连线（必须三格都有棋子）
                if None not in [piece1, piece2, piece3]:
                    # 统计连线内的棋子构成
                    ally_count = 0
                    enemy_count = 0
                    has_ally_jia = False  # 是否包含己方甲/胄
                    
                    pieces_list = [piece1, piece2, piece3]
                    for piece in pieces_list:
                        if piece.color == color:
                            # 盾不参与甲/胄的连线吃子
                            if isinstance(piece, Dun):
                                # 如果连线中有盾，则此连线不能触发甲/胄的吃子规则
                                ally_count = 0
                                enemy_count = 0
                                break
                            ally_count += 1
                            if isinstance(piece, Jia):  # 己方棋子包含甲/胄
                                has_ally_jia = True
                        else:
                            enemy_count += 1
                    
                    # 检查连线中的己方棋子是否与敌方盾8邻域相接
                    if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                        shield_nearby = False
                        for piece in pieces_list:
                            if piece.color == color:  # 检查己方棋子
                                for shield in pieces:
                                    if isinstance(shield, Dun) and shield.color != color:  # 敌方盾
                                        # 检查己方棋子是否与敌方盾相邻（8邻域）
                                        row_diff = abs(shield.row - piece.row)
                                        col_diff = abs(shield.col - piece.col)
                                        if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):
                                            shield_nearby = True
                                            break
                                if shield_nearby:
                                    break
                        
                        if shield_nearby:
                            # 如果连线中的己方棋子与敌方盾8邻域相接，则不能触发吃子
                            ally_count = 0
                            enemy_count = 0
                    
                    # 校验特殊吃子条件：2己1敌 + 包含至少1个己方甲/胄
                    if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                        # 找到连线中的敌方棋子，加入捕获列表（去重）
                        enemy_pieces = [p for p in pieces_list if p.color != color]
                        for enemy in enemy_pieces:
                            if enemy not in captures:
                                captures.append(enemy)
        
        # 检查右上到左下的对角线
        for row in range(11):  # 最多检查到第11行，因为需要连续3格
            for col in range(2, 13):  # 从第2列开始，因为需要向左下连续3格
                piece1 = GameRules.get_piece_at(pieces, row, col)
                piece2 = GameRules.get_piece_at(pieces, row + 1, col - 1)
                piece3 = GameRules.get_piece_at(pieces, row + 2, col - 2)
                
                # 过滤空位置的连线（必须三格都有棋子）
                if None not in [piece1, piece2, piece3]:
                    # 统计连线内的棋子构成
                    ally_count = 0
                    enemy_count = 0
                    has_ally_jia = False  # 是否包含己方甲/胄
                    
                    pieces_list = [piece1, piece2, piece3]
                    for piece in pieces_list:
                        if piece.color == color:
                            # 盾不参与甲/胄的连线吃子
                            if isinstance(piece, Dun):
                                # 如果连线中有盾，则此连线不能触发甲/胄的吃子规则
                                ally_count = 0
                                enemy_count = 0
                                break
                            ally_count += 1
                            if isinstance(piece, Jia):  # 己方棋子包含甲/胄
                                has_ally_jia = True
                        else:
                            enemy_count += 1
                    
                    # 检查连线中的己方棋子是否与敌方盾8邻域相接
                    if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                        shield_nearby = False
                        for piece in pieces_list:
                            if piece.color == color:  # 检查己方棋子
                                for shield in pieces:
                                    if isinstance(shield, Dun) and shield.color != color:  # 敌方盾
                                        # 检查己方棋子是否与敌方盾相邻（8邻域）
                                        row_diff = abs(shield.row - piece.row)
                                        col_diff = abs(shield.col - piece.col)
                                        if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):
                                            shield_nearby = True
                                            break
                                if shield_nearby:
                                    break
                        
                        if shield_nearby:
                            # 如果连线中的己方棋子与敌方盾8邻域相接，则不能触发吃子
                            ally_count = 0
                            enemy_count = 0
                    
                    # 校验特殊吃子条件：2己1敌 + 包含至少1个己方甲/胄
                    if ally_count == 2 and enemy_count == 1 and has_ally_jia:
                        # 找到连线中的敌方棋子，加入捕获列表（去重）
                        enemy_pieces = [p for p in pieces_list if p.color != color]
                        for enemy in enemy_pieces:
                            if enemy not in captures:
                                captures.append(enemy)
        
        return captures
    
    @staticmethod
    def is_check(pieces, color):
        """检查是否将军
        
        Args:
            pieces (list): 棋子列表
            color (str): 要检查的方的颜色
            
        Returns:
            bool: 是否将军
        """
        # 找出该方的将/帅
        king = None
        for piece in pieces:
            if isinstance(piece, King) and piece.color == color:
                king = piece
                break
        
        if not king:
            return True  # 没有找到将/帅，视为被将死
        
        # 检查对方每个棋子是否能攻击到将/帅
        for piece in pieces:
            if piece.color != color:  # 对方棋子
                # 根据棋子类型使用相应的攻击检测方法
                if isinstance(piece, Ju):  # 车
                    if GameRules.can_ju_attack(pieces, piece.row, piece.col, king.row, king.col):
                        return True
                elif isinstance(piece, Pao):  # 炮
                    if GameRules.can_pao_attack(pieces, piece.row, piece.col, king.row, king.col):
                        return True
                elif isinstance(piece, Ma):  # 马
                    if GameRules.can_ma_attack(pieces, piece.row, piece.col, king.row, king.col):
                        return True
                elif isinstance(piece, King):  # 将/帅
                    # 将帅对脸规则
                    if piece.col == king.col:
                        # 检查中间是否有其他棋子
                        start_row = min(piece.row, king.row) + 1
                        end_row = max(piece.row, king.row)
                        has_piece_between = False
                        for r in range(start_row, end_row):
                            if GameRules.get_piece_at(pieces, r, piece.col):
                                has_piece_between = True
                                break
                        if not has_piece_between:
                            return True
                else:  # 其他棋子（兵/卒、相/象、士/仕等）
                    if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, king.row, king.col):
                        return True
        
        return False
    
    @staticmethod
    def would_be_in_check_after_move(pieces, piece, to_row, to_col):
        """检查移动后是否会导致被将军
        
        Args:
            pieces (list): 棋子列表
            piece (ChessPiece): 要移动的棋子
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 移动后是否会被将军
        """
        # 使用虚拟移动工具函数
        from program.utils.utils import virtual_move
        return virtual_move(pieces, piece, to_row, to_col, GameRules.is_check, piece.color)
    
    @staticmethod
    def is_checkmate(pieces, color):
        """检查是否将死（无法逃脱的将军）
        
        Args:
            pieces (list): 棋子列表
            color (str): 要检查的方的颜色
            
        Returns:
            bool: 是否将死
        """
        # 首先检查是否将军
        if not GameRules.is_check(pieces, color):
            return False
        
        # 检查该方是否有任何合法移动可以解除将军
        for piece in pieces:
            if piece.color == color:  # 该方的棋子
                # 尝试所有可能的移动
                for row in range(13):
                    for col in range(13):
                        if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, row, col):
                            # 检查这个移动是否会解除将军（送将检测）
                            if not GameRules.would_be_in_check_after_move(pieces, piece, row, col):
                                return False  # 找到一个可以解除将军的移动，不是将死
        
        # 没有合法移动可以解除将军，是将死
        return True
    
    @staticmethod
    def can_move_to(pieces, piece, to_row, to_col):
        """检查棋子是否可以移动到指定位置"""
        return GameRules.is_valid_move(pieces, piece, piece.row, piece.col, to_row, to_col)
    
    @staticmethod
    def is_game_over(pieces, player_color):
        """检查游戏是否结束
        
        Args:
            pieces (list): 棋子列表
            player_color (str): 当前玩家颜色
            
        Returns:
            bool: 游戏是否结束
            str or None: 获胜方，如果游戏未结束则为None
        """
        # 检查是否有汉/汗进入敌方九宫
        for piece in pieces:
            if isinstance(piece, King):
                # 检查红方汉是否进入黑方九宫
                if piece.color == "red" and 1 <= piece.row <= 3 and 5 <= piece.col <= 7:
                    return True, "red"
                
                # 检查黑方汗是否进入红方九宫
                if piece.color == "black" and 9 <= piece.row <= 11 and 5 <= piece.col <= 7:
                    return True, "black"
        
        # 检查是否存在将帅照面的情况（违规方失败）
        red_king = None
        black_king = None
        
        # 找到双方的将/帅
        for piece in pieces:
            if isinstance(piece, King):
                if piece.color == "red":
                    red_king = piece
                else:
                    black_king = piece
        
        # 如果双方将/帅都在场上
        if red_king and black_king:
            # 检查是否在同一列
            if red_king.col == black_king.col:
                # 检查中间是否有其他棋子
                start_row = min(red_king.row, black_king.row) + 1
                end_row = max(red_king.row, black_king.row)
                has_piece_between = False
                
                for row in range(start_row, end_row):
                    if GameRules.get_piece_at(pieces, row, red_king.col):
                        has_piece_between = True
                        break
                
                # 如果中间没有棋子，说明将帅照面，当前移动的一方失败
                if not has_piece_between:
                    # 违规方是当前玩家，所以对手获胜
                    winner = "black" if player_color == "red" else "red"
                    return True, winner
        
        # 检查对方是否被将死
        opponent_color = "black" if player_color == "red" else "red"
        
        # 找出对方的将/帅
        opponent_king = None
        for piece in pieces:
            if isinstance(piece, King) and piece.color == opponent_color:
                opponent_king = piece
                break
        
        # 没有找到对方的将/帅，当前玩家获胜
        if not opponent_king:
            return True, player_color
        
        # 检查对方是否被将军
        if GameRules.is_check(pieces, opponent_color):
            # 检查对方是否有合法移动可以解除将军
            has_valid_move = False
            for piece in pieces:
                if piece.color == opponent_color:
                    for row in range(13):
                        for col in range(13):
                            # 尝试移动
                            if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, row, col):
                                # 检查这个移动是否会解除将军（送将检测）
                                if not GameRules.would_be_in_check_after_move(pieces, piece, row, col):
                                    has_valid_move = True
                                    break
                        if has_valid_move:
                            break
                if has_valid_move:
                    break
            
            # 如果对方没有合法移动可以解除将军，则当前玩家获胜（将死）
            if not has_valid_move:
                return True, player_color
        
        return False, None
    
    @staticmethod
    def is_facing_enemy(piece, pieces):
        """检查尉/衛是否与敌方面对面（照面）"""
        if not isinstance(piece, Wei):
            return False
            
        # 检查4个方向是否有敌方棋子直接照面（无遮挡）
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            # 沿着这个方向逐步检查
            r, c = piece.row + dr, piece.col + dc
            while 0 <= r < 13 and 0 <= c < 13:
                target = GameRules.get_piece_at(pieces, r, c)
                if target:
                    # 如果是敌方棋子，则形成照面
                    if target.color != piece.color:
                        return True
                    # 如果是己方棋子，则停止搜索这个方向
                    else:
                        break
                r += dr
                c += dc
        
        return False
    
    @staticmethod
    def get_facing_piece(wei_piece, pieces):
        """获取与尉/衛照面的敌方棋子"""
        if not isinstance(wei_piece, Wei):
            return None
            
        # 检查8个方向是否有敌方棋子直接照面（无遮挡）
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            # 沿着这个方向逐步检查
            r, c = wei_piece.row + dr, wei_piece.col + dc
            while 0 <= r < 13 and 0 <= c < 13:
                target = GameRules.get_piece_at(pieces, r, c)
                if target:
                    # 如果是敌方棋子，则返回该棋子
                    if target.color != wei_piece.color:
                        return target
                    # 如果是己方棋子，则停止搜索这个方向
                    else:
                        break
                r += dr
                c += dc
        
        return None
    

    @staticmethod
    def has_insufficient_material(pieces):
        """检查是否为不可能取胜的简单局势（简单残局）
        
        Args:
            pieces (list): 棋子列表
            
        Returns:
            bool: 是否为不可能取胜的简单局势
        """
        # 统计双方棋子数量
        red_pieces = [p for p in pieces if p.color == "red"]
        black_pieces = [p for p in pieces if p.color == "black"]
        
        # 统计各方棋子类型
        red_types = {}
        black_types = {}
        
        for piece in red_pieces:
            piece_type = type(piece).__name__
            red_types[piece_type] = red_types.get(piece_type, 0) + 1
        
        for piece in black_pieces:
            piece_type = type(piece).__name__
            black_types[piece_type] = black_types.get(piece_type, 0) + 1
        
        # 如果某一方只剩下将/帅，而对方只有将/帅+1个棋子，或者将/帅+2个棋子但都是不能杀王的棋子（如相/象、士/仕等）
        # 简单判断：如果一方只剩下将/帅，而对方棋子数量不足以形成杀局，则为和棋
        if len(red_pieces) == 1 and isinstance(red_pieces[0], King):  # 红方只剩将/帅
            if len(black_pieces) <= 2:
                # 黑方只有1-2个棋子，检查是否无法形成杀局
                if len(black_pieces) == 1 and isinstance(black_pieces[0], King):
                    return True  # 双王残局
                elif len(black_pieces) == 2:
                    # 检查黑方第二个棋子是否无法杀王（如相、士等）
                    other_piece = black_pieces[1] if not isinstance(black_pieces[0], King) else black_pieces[0]
                    if isinstance(other_piece, (Shi, Xiang)):
                        return True
        
        if len(black_pieces) == 1 and isinstance(black_pieces[0], King):  # 黑方只剩将/帅
            if len(red_pieces) <= 2:
                # 红方只有1-2个棋子，检查是否无法形成杀局
                if len(red_pieces) == 1 and isinstance(red_pieces[0], King):
                    return True  # 双王残局
                elif len(red_pieces) == 2:
                    # 检查红方第二个棋子是否无法杀王（如相、士等）
                    other_piece = red_pieces[1] if not isinstance(red_pieces[0], King) else red_pieces[0]
                    if isinstance(other_piece, (Shi, Xiang)):
                        return True
        
        return False
    
    @staticmethod
    def is_stalemate(pieces, player_color):
        """检查是否为困毙（无子可走）
        
        Args:
            pieces (list): 棋子列表
            player_color (str): 当前玩家颜色
            
        Returns:
            bool: 是否为困毙
        """
        # 检查当前玩家是否有任何合法移动
        for piece in pieces:
            if piece.color == player_color:
                # 尝试所有可能的移动
                for row in range(13):
                    for col in range(13):
                        if GameRules.is_valid_move(pieces, piece, piece.row, piece.col, row, col):
                            # 检查这个移动是否会送将
                            if not GameRules.would_be_in_check_after_move(pieces, piece, row, col):
                                return False  # 找到了一个合法移动，不是困毙
        
        # 没有任何合法移动，是困毙
        return True
    
    @staticmethod
    def is_repeated_move(board_position_history, repetition_count=3):
        """检查是否出现循环反复的局面（重复局面）
        
        Args:
            board_position_history (list): 局面历史记录
            repetition_count (int): 重复次数阈值
            
        Returns:
            bool: 是否出现循环反复的局面
        """
        if len(board_position_history) < repetition_count:
            return False
        
        # 获取最新的局面
        latest_board_hash = board_position_history[-1]
        
        # 计算该局面在历史上出现的次数
        count = 0
        for board_hash in board_position_history:
            if board_hash == latest_board_hash:
                count += 1
                if count >= repetition_count:
                    return True
        
        return False
    
    @staticmethod
    def get_board_hash(pieces):
        """获取棋盘局面的哈希值
        
        Args:
            pieces (list): 棋子列表
            
        Returns:
            str: 棋盘局面的哈希表示
        """
        # 按照位置和棋子类型排序，生成局面字符串
        sorted_pieces = sorted(pieces, key=lambda p: (p.row, p.col, p.name))
        board_str = ""
        for piece in sorted_pieces:
            board_str += f"{piece.row},{piece.col},{piece.name},{piece.color};"
        
        import hashlib
        return hashlib.md5(board_str.encode()).hexdigest()



