import time
import threading
import pygame
from program.core.chess_pieces import Ju, Ma, Xiang, Shi, King, Pao, Pawn, Wei, She, Lei, Jia, Ci, Dun


class ChessAI:
    """匈汉象棋AI类，支持Minimax、Negamax和Alpha-Beta搜索算法，支持多线程计算"""
    
    def __init__(self, algorithm="negamax", difficulty="hard", ai_color="black"):
        """初始化AI
        
        Args:
            algorithm (str): 算法类型 'minimax', 'negamax', 'alpha-beta'
            difficulty (str): 难度级别 'easy', 'medium', 'hard' - 现在始终使用最高难度
            ai_color (str): AI执子颜色 'red' 或 'black'
        """
        self.algorithm = algorithm.lower()
        self.difficulty = "hard"  # 始终使用最高难度
        self.ai_color = ai_color
        self.transposition_table = {}  # 置换表
        self.history_table = {}  # 历史启发表
        
        # 根据难度设置搜索参数
        if difficulty == "easy":
            self.search_depth = 3
            self.max_think_time = 2000
        elif difficulty == "medium":
            self.search_depth = 5
            self.max_think_time = 4000
        else:  # hard
            self.search_depth = 9  # 调整搜索深度到9层
            self.max_think_time = 8000  # 优化思考时间
        
        # 增加搜索深度和思考时间，提高AI难度
        self.search_depth = 9 # 调整搜索深度到9层
        self.randomness = 0.0
        
        # 启用迭代加深搜索以更快响应
        self.use_iterative_deepening = True
        # 启用积极剪枝以提高搜索效率
        self.aggressive_pruning = True
        
        # 棋子基础价值（根据匈汉象棋新规则调整）
        self.piece_values = {
            "汉": 10000, "汗": 10000,  # 王的价值最高
            "車": 900, "车": 900,      # 车
            "馬": 400, "马": 400,      # 马
            "相": 250, "象": 250,      # 相/象（增强后价值提升）
            "仕": 200, "士": 200,      # 仕/士
            "炮": 450, "砲": 450,      # 炮
            "兵": 100, "卒": 100,      # 兵/卒
            "尉": 300, "衛": 300,      # 尉/衛（价值调整）
            "射": 300, "䠶": 300,      # 射/䠶
            "檑": 350, "礌": 350,      # 檑/礌（攻击能力强）
            "甲": 200, "胄": 200,      # 甲/胄
            "刺": 250, "刺": 250,      # 刺（拖吃者）
            "盾": 300, "盾": 300       # 盾（保护价值）
        }
        
        # 位置价值表
        self._init_position_tables()
        
        # 多线程相关
        self.ai_thread = None
        self.computed_move = None
        self.computation_finished = False
        self.best_move_so_far = None  # 用于保存当前最佳走法
        self.best_value_so_far = float('-inf')  # 用于保存当前最佳估值
        
        # 线程锁，确保线程安全
        self.lock = threading.Lock()
        
        # 高级搜索技术参数
        self.search_depth = 11  # 增加搜索深度
        self.max_think_time = 8000  # 优化思考时间
        self.use_killer_move = True  # 启用杀手着法
        self.killer_moves = [[None for _ in range(2)] for _ in range(20)]  # 杀手着法表
        self.use_history_heuristic = True  # 启用历史启发
        self.transposition_table_size = 1000000  # 增大置换表容量
        
        # 线程锁，确保线程安全
        self.lock = threading.Lock()
    
    def _init_position_tables(self):
        """初始化棋子位置价值表（适用于匈汉象棋13x13棋盘）"""
        # 基础位置价值矩阵，适用于13x13棋盘
        base_pos_value = [[10 for _ in range(13)] for _ in range(13)]
        
        # 中心区域价值更高 (5-7行, 5-7列)
        for i in range(5, 8):
            for j in range(5, 8):
                base_pos_value[i][j] = 20
                
        # 九宫格价值调整
        # 红方九宫格 (9-11行, 5-7列)
        for i in range(9, 12):
            for j in range(5, 8):
                base_pos_value[i][j] = 25
                
        # 黑方九宫格 (1-3行, 5-7列)
        for i in range(1, 4):
            for j in range(5, 8):
                base_pos_value[i][j] = 25
        
        # 楚河汉界区域价值降低 (6行)
        for j in range(13):
            base_pos_value[6][j] = 5
            
        self.base_pos_value = base_pos_value
        
        # 兵/卒位置价值表
        self.pawn_pos_red = [row[:] for row in base_pos_value]
        self.pawn_pos_black = [row[:] for row in base_pos_value]
        
        # 调整兵/卒位置价值
        # 红方兵价值随着接近对方九宫而增加
        for i in range(9):  # 红方兵在0-8行
            for j in range(13):
                self.pawn_pos_red[i][j] += (9 - i) * 5  # 越接近对方价值越高
                
        # 黑方兵价值随着接近对方九宫而增加
        for i in range(4, 13):  # 黑方兵在4-12行
            for j in range(13):
                self.pawn_pos_black[i][j] += (i - 3) * 5  # 越接近对方价值越高
        
        # 车位置价值表（倾向于控制开放线路）
        self.rook_pos_red = [row[:] for row in base_pos_value]
        self.rook_pos_black = [row[:] for row in base_pos_value]
        
        # 马位置价值表（倾向于中心位置）
        self.knight_pos_red = [row[:] for row in base_pos_value]
        self.knight_pos_black = [row[:] for row in base_pos_value]
        
        # 炮位置价值表
        self.cannon_pos_red = [row[:] for row in base_pos_value]
        self.cannon_pos_black = [row[:] for row in base_pos_value]
        
        # 相/象位置价值表（不能过河，但敌方区域有特殊能力）
        self.bishop_pos_red = [row[:] for row in base_pos_value]
        self.bishop_pos_black = [row[:] for row in base_pos_value]
        
        # 限制相/象活动范围，但在敌方区域增强
        for i in range(13):
            for j in range(13):
                # 红方相在敌方区域（1-6行）价值更高
                if i <= 6:
                    self.bishop_pos_red[i][j] = 30  # 在敌方区域价值更高
                # 黑方象在敌方区域（6-12行）价值更高
                elif i >= 6:
                    self.bishop_pos_black[i][j] = 30  # 在敌方区域价值更高
                # 传统相/象限制
                else:
                    self.bishop_pos_red[i][j] = 5
                    self.bishop_pos_black[i][j] = 5
        
        # 士/仕位置价值表（只能在九宫格内）
        self.advisor_pos_red = [row[:] for row in base_pos_value]
        self.advisor_pos_black = [row[:] for row in base_pos_value]
        
        # 限制士/仕活动范围（虽然规则允许过河，但仍偏好九宫）
        for i in range(13):
            for j in range(13):
                # 红方仕偏好九宫格
                if not (9 <= i <= 11 and 5 <= j <= 7):
                    self.advisor_pos_red[i][j] -= 5
                # 黑方士偏好九宫格
                if not (1 <= i <= 3 and 5 <= j <= 7):
                    self.advisor_pos_black[i][j] -= 5
        
        # 尉/衛位置价值表（跳跃能力，战略价值高）
        self.guard_pos_red = [row[:] for row in base_pos_value]
        self.guard_pos_black = [row[:] for row in base_pos_value]
        
        # 尉在棋盘中央区域价值更高，因为可以跳跃过棋子
        for i in range(13):
            for j in range(13):
                if 4 <= i <= 8 and 4 <= j <= 8:
                    self.guard_pos_red[i][j] = 35
                    self.guard_pos_black[i][j] = 35
                # 在边界区域价值较低
                elif i < 2 or i > 10 or j < 2 or j > 10:
                    self.guard_pos_red[i][j] = 15
                    self.guard_pos_black[i][j] = 15
        
        # 射/䠶位置价值表（偏好斜线和特定位置）
        self.archer_pos_red = [row[:] for row in base_pos_value]
        self.archer_pos_black = [row[:] for row in base_pos_value]
        
        # 檑/礌位置价值表（长距离攻击，中心控制力强）
        self.rock_pos_red = [row[:] for row in base_pos_value]
        self.rock_pos_black = [row[:] for row in base_pos_value]
        
        # 檑/礌在中心区域价值更高，因为控制范围广
        for i in range(13):
            for j in range(13):
                if 4 <= i <= 8 and 4 <= j <= 8:
                    self.rock_pos_red[i][j] = 40
                    self.rock_pos_black[i][j] = 40
        
        # 甲/胄位置价值表（近战）
        self.armor_pos_red = [row[:] for row in base_pos_value]
        self.armor_pos_black = [row[:] for row in base_pos_value]
        
    def get_move_async(self, game_state):
        """异步获取AI的最佳走法，启动多线程计算
        
        Args:
            game_state: GameState对象，表示当前棋盘状态
        """
        # 重置状态
        self.computed_move = None
        self.computation_finished = False
        self.best_move_so_far = None
        self.best_value_so_far = float('-inf')
        
        # 启动一个线程来执行AI计算
        self.ai_thread = threading.Thread(target=self._compute_move, args=(game_state,))
        self.ai_thread.daemon = True  # 设置为守护线程
        self.ai_thread.start()
    
    def is_computation_finished(self):
        """检查计算是否完成"""
        return self.computation_finished
    
    def get_computed_move(self):
        """获取计算完成的走法，如果计算未完成则返回当前最佳走法"""
        with self.lock:  # 线程安全
            if self.computation_finished:
                return self.computed_move
            else:
                # 如果计算未完成，返回当前已知的最佳走法
                return self.best_move_so_far if self.best_move_so_far is not None else self.computed_move
    
    def _compute_move(self, game_state):
        """在单独线程中计算最佳走法"""
        try:
            # 执行实际的AI计算
            self.computed_move = self._get_best_move(game_state)
        finally:
            # 标记计算完成
            with self.lock:  # 线程安全
                self.computation_finished = True
            # 通过pygame事件通知主线程
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + 2))  # 使用不同的事件ID
    
    def _get_best_move(self, game_state):
        """获取AI的最佳走法（实际计算逻辑）
        
        Args:
            game_state: GameState对象，表示当前棋盘状态
            
        Returns:
            tuple: ((from_row, from_col), (to_row, to_col)) 表示移动的起点和终点
        """
        # 清空置换表和历史表
        self.transposition_table = {}
        self.history_table = {}
        
        # 重置当前最佳走法
        self.best_move_so_far = None
        self.best_value_so_far = float('-inf')
        
        # 获取所有可能的走法
        valid_moves = self._get_valid_moves(game_state, self.ai_color)
        
        if not valid_moves:
            return None  # 无有效走法
        
        # 对走法进行排序（启发式）以提高剪枝效率
        valid_moves = self._sort_moves(game_state, valid_moves)
        
        # 如果只有一个有效移动，直接返回
        if len(valid_moves) == 1:
            return valid_moves[0]
        
        # 记录开始时间
        start_time = time.time()
        
        best_move = valid_moves[0]  # 默认使用第一个有效走法
        best_value = float('-inf')
        
        # 根据局面复杂性动态调整搜索深度
        # 如果局面比较复杂（有很多可走的棋子），稍微减少搜索深度以保证时间
        # 如果局面较简单，增加搜索深度
        complexity_factor = len(valid_moves) / 10.0  # 基于可走步数的复杂度
        if complexity_factor > 1.5:  # 复杂局面
            effective_depth = max(3, self.search_depth - 1)  # 减少搜索深度
        elif complexity_factor < 0.5:  # 简单局面
            effective_depth = min(12, self.search_depth + 1)  # 增加搜索深度
        else:
            effective_depth = self.search_depth  # 正常搜索深度
        
        # 使用迭代加深搜索
        if self.use_iterative_deepening:
            # 从较浅的深度开始搜索，逐步加深
            for current_depth in range(1, effective_depth + 1):
                # 检查是否超时（更严格的超时控制）
                if (time.time() - start_time) * 1000 > self.max_think_time * 0.9:  # 提高时间利用率为90%
                    break
                
                alpha = float('-inf')
                beta = float('inf')
                
                current_best_move = None
                current_best_value = float('-inf')
                
                # 搜索当前深度的最佳走法
                for from_pos, to_pos in valid_moves:
                    # 检查思考时间是否超出限制
                    elapsed_time = (time.time() - start_time) * 1000
                    if elapsed_time > self.max_think_time:
                        break
                    
                    # 模拟移动
                    cloned_state = self._clone_game_state(game_state)
                    self._make_move(cloned_state, from_pos, to_pos)
                    
                    # 根据算法类型选择搜索方法
                    if self.algorithm == "minimax":
                        value = self._minimax(cloned_state, current_depth - 1, False, start_time)
                        value = -value  # 反转值，因为是对手的回合
                    elif self.algorithm == "alpha-beta":
                        value = self._alpha_beta_search(cloned_state, current_depth - 1, alpha, beta, False, start_time)
                        value = -value  # 反转值，因为是对手的回合
                    else:  # 默认使用negamax
                        value = self._negamax(cloned_state, current_depth - 1, -beta, -alpha, False, start_time)
                        value = -value  # 反转值，因为是对手的回合
                    
                    # 更新最佳走法
                    if value > current_best_value:
                        current_best_value = value
                        current_best_move = (from_pos, to_pos)
                        alpha = max(alpha, current_best_value)
                        
                        # 更新历史表
                        self._update_history_move(from_pos, to_pos, current_depth)
                        
                        # 更新当前已知最佳走法 - 线程安全
                        with self.lock:
                            self.best_move_so_far = (from_pos, to_pos)
                            self.best_value_so_far = value
                        
                        # 如果使用积极剪枝且发现明显优势的走法，提前终止
                        if self.aggressive_pruning and alpha > 5000:  # 接近胜利的局面
                            break
                
                # 更新全局最佳走法
                if current_best_move and current_best_value > best_value:
                    best_value = current_best_value
                    best_move = current_best_move
        else:
            # 原始的固定深度搜索
            alpha = float('-inf')
            beta = float('inf')
            
            for from_pos, to_pos in valid_moves:
                # 检查思考时间是否超出限制
                if (time.time() - start_time) * 1000 > self.max_think_time:
                    break
                
                # 模拟移动
                cloned_state = self._clone_game_state(game_state)
                self._make_move(cloned_state, from_pos, to_pos)
                
                # 根据算法类型选择搜索方法
                if self.algorithm == "minimax":
                    value = self._minimax(cloned_state, effective_depth - 1, False, start_time)
                    value = -value  # 反转值，因为是对手的回合
                elif self.algorithm == "alpha-beta":
                    value = self._alpha_beta_search(cloned_state, effective_depth - 1, alpha, beta, False, start_time)
                    value = -value  # 反转值，因为是对手的回合
                else:  # 默认使用negamax
                    value = self._negamax(cloned_state, effective_depth - 1, -beta, -alpha, False, start_time)
                    value = -value  # 反转值，因为是对手的回合
                
                # 更新最佳走法
                if value > best_value:
                    best_value = value
                    best_move = (from_pos, to_pos)
                    alpha = max(alpha, best_value)
                    
                    # 更新当前已知最佳走法 - 线程安全
                    with self.lock:
                        self.best_move_so_far = (from_pos, to_pos)
                        self.best_value_so_far = value
        
        # 如果没有找到最佳走法，返回当前已知的最佳走法
        if best_move is None:
            with self.lock:  # 线程安全
                best_move = self.best_move_so_far
        
        # 如果仍然没有找到走法，返回随机走法
        if best_move is None and valid_moves:
            import random
            best_move = random.choice(valid_moves)
        
        return best_move
    
    def _get_valid_moves(self, game_state, color):
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
    
    def _sort_moves(self, game_state, moves):
        """改进的走法排序，提高剪枝效率
        
        排序优先级：杀手着法 > 历史启发 > MVV-LVA > 将军 > 普通走法
        """
        scored_moves = []
        
        for from_pos, to_pos in moves:
            score = 0
            from_row, from_col = from_pos
            to_row, to_col = to_pos
            
            # 获取移动的棋子和目标棋子
            moving_piece = None
            target_piece = None
            for piece in game_state.pieces:
                if piece.row == from_row and piece.col == from_col:
                    moving_piece = piece
                elif piece.row == to_row and piece.col == to_col:
                    target_piece = piece
            
            # 检查是否为杀手着法（导致beta剪枝的走法）
            if (hasattr(self, 'killer_moves') and 
                (from_pos, to_pos) in [km for sublist in self.killer_moves for km in sublist]):
                score += 10000  # 杀手着法优先级最高
            
            # 历史启发：使用历史表中的评分
            history_score = self.history_table.get((from_pos, to_pos), 0)
            score += history_score * 10  # 历史启发权重较高
            
            # MVV-LVA (Most Valuable Victim - Least Valuable Attacker) 启发
            if target_piece:
                # 吃子得分：目标棋子价值 - 当前棋子价值
                mvv_lva_score = self._get_piece_value(target_piece) - self._get_piece_value(moving_piece) // 10
                score += mvv_lva_score * 2  # 增加吃子权重
            
            # 模拟移动，检查是否将军
            cloned_state = self._clone_game_state(game_state)
            self._make_move(cloned_state, from_pos, to_pos)
            
            opponent_color = "red" if self.ai_color == "black" else "black"
            if self._is_check(cloned_state, opponent_color):
                score += 300  # 将军得高分，增加将军权重
            
            # 位置价值启发：移动到更好位置的加权
            if moving_piece:
                old_pos_value = self._get_position_value_at_pos(moving_piece, from_row, from_col)
                new_pos_value = self._get_position_value_at_pos(moving_piece, to_row, to_col)
                pos_improvement = new_pos_value - old_pos_value
                score += pos_improvement * 0.5  # 位置改进权重
            
            scored_moves.append(((from_pos, to_pos), score))
        
        # 按分数降序排列
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        
        # 返回排序后的走法
        return [move for move, _ in scored_moves]

    def _minimax(self, game_state, depth, is_maximizing, start_time):
        """Minimax搜索算法
        
        Args:
            game_state: 游戏状态
            depth: 当前搜索深度
            is_maximizing: 是否是最大化层(AI回合)
            start_time: 搜索开始时间
            
        Returns:
            int: 局面评分
        """
        # 检查思考时间是否超出限制
        if (time.time() - start_time) * 1000 > self.max_think_time:
            # 时间耗尽，使用评估函数快速返回
            return self._evaluate_board(game_state)
        
        # 达到叶节点或游戏结束
        if depth == 0 or game_state.game_over:
            return self._evaluate_board(game_state)
        
        # 获取当前玩家颜色
        if is_maximizing:
            player_color = self.ai_color
        else:
            player_color = "red" if self.ai_color == "black" else "black"
        
        # 获取并排序走法
        moves = self._get_valid_moves(game_state, player_color)
        
        # 如果没有可走的棋子，返回极大负值（表示被将死）
        if not moves:
            # 检查是否被将死
            if self._is_in_check_for_current_player(game_state):
                return float('-inf') if is_maximizing else float('inf')  # 被将死
            else:
                return 0  # 和棋（无子可动但未被将军）
        
        if is_maximizing:
            max_eval = float('-inf')
            for from_pos, to_pos in moves:
                # 检查思考时间是否超出限制
                if (time.time() - start_time) * 1000 > self.max_think_time:
                    break
                
                cloned_state = self._clone_game_state(game_state)
                self._make_move(cloned_state, from_pos, to_pos)
                
                # 递归搜索
                eval = self._minimax(cloned_state, depth - 1, False, start_time)
                
                max_eval = max(max_eval, eval)
                
            return max_eval
        else:
            min_eval = float('inf')
            for from_pos, to_pos in moves:
                # 检查思考时间是否超出限制
                if (time.time() - start_time) * 1000 > self.max_think_time:
                    break
                
                cloned_state = self._clone_game_state(game_state)
                self._make_move(cloned_state, from_pos, to_pos)
                
                # 递归搜索
                eval = self._minimax(cloned_state, depth - 1, True, start_time)
                
                min_eval = min(min_eval, eval)
                
            return min_eval

    def _alpha_beta_search(self, game_state, depth, alpha, beta, is_maximizing, start_time):
        """Alpha-Beta搜索算法
        
        Args:
            game_state: 游戏状态
            depth: 当前搜索深度
            alpha: Alpha值
            beta: Beta值
            is_maximizing: 是否是最大化层(AI回合)
            start_time: 搜索开始时间
            
        Returns:
            int: 局面评分
        """
        # 检查思考时间是否超出限制
        if (time.time() - start_time) * 1000 > self.max_think_time:
            # 时间耗尽，使用评估函数快速返回
            return self._evaluate_board(game_state)
        
        # 生成棋盘状态的唯一键
        state_key = self._get_state_key(game_state)
        
        # 检查置换表
        if state_key in self.transposition_table and self.transposition_table[state_key]['depth'] >= depth:
            entry = self.transposition_table[state_key]
            if entry['type'] == 'exact':
                return entry['value']
            elif entry['type'] == 'lower':
                alpha = max(alpha, entry['value'])
            elif entry['type'] == 'upper':
                beta = min(beta, entry['value'])
            if alpha >= beta:
                return entry['value']
        
        # 达到叶节点或游戏结束
        if depth == 0 or game_state.game_over:
            value = self._evaluate_board(game_state)
            # 保存到置换表
            self.transposition_table[state_key] = {
                'value': value, 
                'depth': depth,
                'type': 'exact'
            }
            return value
        
        # 获取当前玩家颜色
        if is_maximizing:
            player_color = self.ai_color
        else:
            player_color = "red" if self.ai_color == "black" else "black"
        
        # 获取并排序走法
        moves = self._get_valid_moves(game_state, player_color)
        
        # 如果没有可走的棋子，返回极大负值（表示被将死）
        if not moves:
            # 检查是否被将死
            if self._is_in_check_for_current_player(game_state):
                return float('-inf') if is_maximizing else float('inf')  # 被将死
            else:
                return 0  # 和棋（无子可动但未被将军）
        
        if is_maximizing:
            max_eval = float('-inf')
            for from_pos, to_pos in moves:
                # 检查思考时间是否超出限制
                if (time.time() - start_time) * 1000 > self.max_think_time:
                    break
                
                cloned_state = self._clone_game_state(game_state)
                self._make_move(cloned_state, from_pos, to_pos)
                
                # 递归搜索
                eval = self._alpha_beta_search(cloned_state, depth - 1, alpha, beta, False, start_time)
                
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                
                # Alpha-Beta剪枝
                if alpha >= beta:
                    # 更新历史表，记录导致剪枝的走法
                    self._update_history_move(from_pos, to_pos, depth)
                    break
                    
            # 保存到置换表
            entry_type = 'exact' if max_eval > alpha and max_eval < beta else (
                         'lower' if max_eval >= beta else 'upper')
            self.transposition_table[state_key] = {
                'value': max_eval, 
                'depth': depth,
                'type': entry_type
            }
            
            return max_eval
        else:
            min_eval = float('inf')
            for from_pos, to_pos in moves:
                # 检查思考时间是否超出限制
                if (time.time() - start_time) * 1000 > self.max_think_time:
                    break
                
                cloned_state = self._clone_game_state(game_state)
                self._make_move(cloned_state, from_pos, to_pos)
                
                # 递归搜索
                eval = self._alpha_beta_search(cloned_state, depth - 1, alpha, beta, True, start_time)
                
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                
                # Alpha-Beta剪枝
                if beta <= alpha:
                    # 更新历史表，记录导致剪枝的走法
                    self._update_history_move(from_pos, to_pos, depth)
                    break
                    
            # 保存到置换表
            entry_type = 'exact' if min_eval > alpha and min_eval < beta else (
                         'upper' if min_eval <= alpha else 'lower')
            self.transposition_table[state_key] = {
                'value': min_eval, 
                'depth': depth,
                'type': entry_type
            }
            
            return min_eval

    def _negamax(self, game_state, depth, alpha, beta, is_maximizing, start_time):
        """Negamax搜索算法
        
        Args:
            game_state: 游戏状态
            depth: 当前搜索深度
            alpha: Alpha值
            beta: Beta值
            is_maximizing: 是否是最大化层(AI回合)
            start_time: 搜索开始时间
            
        Returns:
            int: 局面评分
        """
        # 检查思考时间是否超出限制
        if (time.time() - start_time) * 1000 > self.max_think_time:
            # 时间耗尽，使用评估函数快速返回
            return self._evaluate_board(game_state)
        
        # 生成棋盘状态的唯一键
        state_key = self._get_state_key(game_state)
        
        # 检查置换表
        if state_key in self.transposition_table and self.transposition_table[state_key]['depth'] >= depth:
            entry = self.transposition_table[state_key]
            if entry['type'] == 'exact':
                return entry['value']
            elif entry['type'] == 'lower':
                alpha = max(alpha, entry['value'])
            elif entry['type'] == 'upper':
                beta = min(beta, entry['value'])
            if alpha >= beta:
                return entry['value']
        
        # 达到叶节点或游戏结束
        if depth == 0 or game_state.game_over:
            value = self._evaluate_board(game_state)
            # 保存到置换表
            self.transposition_table[state_key] = {
                'value': value, 
                'depth': depth,
                'type': 'exact'
            }
            return value
        
        # 空着剪枝（Null Move Pruning）
        if depth >= 3 and not self._is_in_check_for_current_player(game_state):
            # 创建一个克隆状态并执行空移动
            cloned_state = self._clone_game_state(game_state)
            cloned_state.player_turn = "red" if cloned_state.player_turn == "black" else "black"
            null_score = -self._negamax(cloned_state, depth-3, -beta, -beta+1, not is_maximizing, start_time)
            if null_score >= beta:
                return beta
        
        # 获取并排序走法
        moves = self._get_valid_moves(game_state, self.ai_color if is_maximizing else 
                                     ("red" if self.ai_color == "black" else "black"))
        moves = self._sort_moves(game_state, moves)
        
        # 如果没有可走的棋子，返回极大负值（表示被将死）
        if not moves:
            # 检查是否被将死
            if self._is_in_check_for_current_player(game_state):
                return float('-inf')  # 被将死，返回负无穷
            else:
                return 0  # 和棋（无子可动但未被将军）
        
        best_value = float('-inf')
        best_move = None  # 跟踪最佳走法
        
        for from_pos, to_pos in moves:
            # 检查思考时间是否超出限制
            if (time.time() - start_time) * 1000 > self.max_think_time:
                break
            
            cloned_state = self._clone_game_state(game_state)
            self._make_move(cloned_state, from_pos, to_pos)
            
            # 递归搜索
            eval = -self._negamax(cloned_state, depth - 1, -beta, -alpha, not is_maximizing, start_time)
            
            if eval > best_value:
                best_value = eval
                best_move = (from_pos, to_pos)  # 记录最佳走法
                
            alpha = max(alpha, eval)
            
            # 更新当前已知最佳走法，如果当前走法更好 - 线程安全
            with self.lock:
                if is_maximizing and eval > self.best_value_so_far:
                    self.best_value_so_far = eval
                    self.best_move_so_far = (from_pos, to_pos)
                elif not is_maximizing and -eval > self.best_value_so_far:
                    self.best_value_so_far = -eval
                    self.best_move_so_far = (from_pos, to_pos)
            
            # Alpha-Beta剪枝
            if alpha >= beta:
                # 更新历史表，记录导致剪枝的走法
                self._update_history_move(from_pos, to_pos, depth)
                break
        
        # 保存到置换表
        entry_type = 'exact' if best_value > alpha and best_value < beta else (
                     'lower' if best_value >= beta else 'upper')
        self.transposition_table[state_key] = {
            'value': best_value, 
            'depth': depth,
            'type': entry_type
        }
        
        # 如果是根节点，更新最佳走法
        if depth == self.search_depth and best_move is not None:
            with self.lock:
                self.best_move_so_far = best_move
                self.best_value_so_far = best_value
        
        return best_value
    
    def _evaluate_board(self, game_state):
        """改进的局面评估函数
        
        返回正分对AI有利，负分对玩家有利
        """
        # 如果游戏已结束
        if game_state.game_over:
            if game_state.winner == self.ai_color:
                return 100000  # AI获胜
            else:
                return -100000  # 玩家获胜
        
        score = 0
        
        # 1. 棋子价值基础分
        for piece in game_state.pieces:
            # 基础价值
            base_value = self._get_piece_value(piece)
            
            # 2. 位置价值加成
            pos_value = self._get_position_value(piece)
            base_value += pos_value
            
            # 3. 动态价值调整
            # 攻击能力加成
            attack_value = self._evaluate_attack_capability(piece, game_state)
            base_value += attack_value
            
            # 防守价值加成
            defense_value = self._evaluate_defense_value(piece, game_state)
            base_value += defense_value
            
            # 根据颜色累加分数
            if piece.color == self.ai_color:
                score += base_value
            else:
                score -= base_value
        
        # 4. 整体态势评估
        # 控制中心区域加成
        center_control = self._evaluate_center_control(game_state)
        if self.ai_color == "red":
            score += center_control
        else:
            score -= center_control
        
        # 王的安全性评估
        king_safety = self._evaluate_king_safety(game_state)
        if self.ai_color == "red":
            score += king_safety
        else:
            score -= king_safety
        
        # 5. 机动性评估（棋子可移动性）
        ai_mobility = self._evaluate_mobility(game_state, self.ai_color)
        opponent_mobility = self._evaluate_mobility(game_state, "red" if self.ai_color == "black" else "black")
        score += ai_mobility - opponent_mobility
        
        # 6. 将军状态评估
        if self._is_check(game_state, self.ai_color):
            score -= 1000  # 被将军严重扣分
        elif self._is_check(game_state, "red" if self.ai_color == "black" else "black"):
            score += 500  # 将军对手加分
        
        # 7. 棋子协调性评估
        coordination = self._evaluate_piece_coordination_simple(game_state, self.ai_color)
        if self.ai_color == "red":
            score += coordination
        else:
            score -= coordination
        
        # 8. 特殊能力评估
        special_abilities = self._evaluate_special_abilities_simple(game_state, self.ai_color)
        if self.ai_color == "red":
            score += special_abilities
        else:
            score -= special_abilities
        
        return score
    
    def _evaluate_attack_capability(self, piece, game_state):
        """评估棋子的攻击能力"""
        attack_value = 0
        
        # 获取可能的攻击位置
        possible_moves, capturable = game_state.calculate_possible_moves(piece.row, piece.col)
        
        # 评估可攻击的棋子价值
        for to_row, to_col in capturable:
            target_piece = game_state.get_piece_at(to_row, to_col)
            if target_piece and target_piece.color != piece.color:
                # MVV-LVA评估：吃掉高价值棋子加分
                target_value = self._get_piece_value(target_piece)
                piece_value = self._get_piece_value(piece)
                
                # 如果用低价值棋子吃高价值棋子，加分更多
                if target_value > piece_value:
                    attack_value += (target_value - piece_value) * 0.3
                else:
                    attack_value += target_value * 0.1
        
        return attack_value

    def _evaluate_defense_value(self, piece, game_state):
        """评估棋子的防守价值"""
        defense_value = 0
        
        # 检查当前棋子是否保护了其他棋子
        for other_piece in game_state.pieces:
            if (other_piece.color == piece.color and 
                other_piece != piece and 
                self._can_protect_simple(game_state, piece, other_piece)):
                # 保护高价值棋子加分
                protected_value = self._get_piece_value(other_piece)
                defense_value += protected_value * 0.05  # 保护价值的5%
        
        return defense_value

    def _evaluate_center_control(self, game_state):
        """评估对中心区域的控制"""
        center_rows = [5, 6, 7]
        center_cols = [5, 6, 7]
        control_score = 0
        
        # 检查中心区域的控制情况
        for row in center_rows:
            for col in center_cols:
                piece = game_state.get_piece_at(row, col)
                if piece:
                    if piece.color == self.ai_color:
                        # 己方棋子在中心加分
                        piece_value = self._get_piece_value(piece)
                        control_score += max(10, piece_value // 10)
                    else:
                        # 敌方棋子在中心扣分
                        piece_value = self._get_piece_value(piece)
                        control_score -= max(10, piece_value // 10)
        
        # 检查能够攻击中心的棋子
        for piece in game_state.pieces:
            if piece.color == self.ai_color:
                possible_moves, capturable = game_state.calculate_possible_moves(piece.row, piece.col)
                for to_row, to_col in capturable:
                    if to_row in center_rows and to_col in center_cols:
                        # 能够攻击中心区域加分
                        control_score += 5
        
        return control_score

    def _evaluate_king_safety(self, game_state):
        """评估王的安全性"""
        # 找出王
        king = None
        for piece in game_state.pieces:
            if isinstance(piece, King) and piece.color == self.ai_color:
                king = piece
                break
        
        if not king:
            return -5000  # 没有王，极度危险
        
        safety_score = 0
        
        # 王在九宫格内更安全
        if self.ai_color == "red":
            if 9 <= king.row <= 11 and 5 <= king.col <= 7:  # 红方王在九宫内
                safety_score += 100
            else:
                # 王在九宫外，检查周围保护情况
                protected_count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        adj_row, adj_col = king.row + dr, king.col + dc
                        adj_piece = game_state.get_piece_at(adj_row, adj_col)
                        if adj_piece and adj_piece.color == self.ai_color:
                            protected_count += 1
                safety_score += protected_count * 15
        else:  # black
            if 1 <= king.row <= 3 and 5 <= king.col <= 7:  # 黑方王在九宫内
                safety_score += 100
            else:
                # 王在九宫外，检查周围保护情况
                protected_count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        adj_row, adj_col = king.row + dr, king.col + dc
                        adj_piece = game_state.get_piece_at(adj_row, adj_col)
                        if adj_piece and adj_piece.color == self.ai_color:
                            protected_count += 1
                safety_score += protected_count * 15
        
        # 检查王周围是否有敌方攻击威胁
        enemy_threats = 0
        for piece in game_state.pieces:
            if piece.color != self.ai_color:  # 敌方棋子
                possible_moves, capturable = game_state.calculate_possible_moves(piece.row, piece.col)
                for to_row, to_col in capturable:
                    if to_row == king.row and to_col == king.col:  # 威胁到王
                        enemy_threats += 1
        
        safety_score -= enemy_threats * 50  # 每个威胁扣50分
        
        return safety_score
    
    def _evaluate_mobility(self, game_state, color):
        """评估棋子的机动性（可移动性）"""
        mobility_bonus = 0
        own_pieces = [p for p in game_state.pieces if p.color == color]
        
        for piece in own_pieces:
            # 计算该棋子的可移动位置数量
            possible_moves, _ = game_state.calculate_possible_moves(piece.row, piece.col)
            mobility = len(possible_moves)
            
            # 根据棋子类型给予不同的机动性权重
            if isinstance(piece, King):
                # 王的机动性权重较低
                mobility_bonus += mobility * 0.5
            elif isinstance(piece, Ju):  # 车
                # 车的机动性权重较高
                mobility_bonus += mobility * 1.5
            elif isinstance(piece, Pao):  # 炮
                # 炮的机动性权重较高
                mobility_bonus += mobility * 1.2
            elif isinstance(piece, Wei):  # 尉
                # 尉的机动性权重适中，因其跳跃能力
                mobility_bonus += mobility * 1.0
            else:
                # 其他棋子的机动性权重
                mobility_bonus += mobility * 0.8
        
        return mobility_bonus
    
    def _evaluate_special_abilities(self, game_state, color):
        """评估特殊棋子能力的价值"""
        special_value = 0
        
        for piece in game_state.pieces:
            if piece.color == color:
                # 评估相/象在敌方区域的特殊能力
                if isinstance(piece, Xiang):
                    # 检查相是否在敌方区域
                    if color == "red" and piece.row <= 6:  # 红方相在黑方区域
                        # 在敌方区域，相的价值增加，因为它有横竖隔一格吃子的能力
                        special_value += 150
                        
                        # 检查相在敌方区域是否能攻击敌方棋子
                        attackable_count = 0
                        for dr in [-2, 0, 2]:  # 横向移动2格
                            for dc in [-2, 0, 2]:
                                if (dr != 0 and dc == 0) or (dr == 0 and dc != 0):  # 只考虑横竖方向
                                    target_row, target_col = piece.row + dr, piece.col + dc
                                    if 0 <= target_row < 13 and 0 <= target_col < 13:
                                        # 检查中间是否有棋子（塞相眼）
                                        mid_row, mid_col = piece.row + dr//2, piece.col + dc//2
                                        if not game_state.get_piece_at(mid_row, mid_col):
                                            # 检查目标位置是否有敌方棋子
                                            target_piece = game_state.get_piece_at(target_row, target_col)
                                            if target_piece and target_piece.color != color:
                                                attackable_count += 1
                        special_value += attackable_count * 30
                        
                    elif color == "black" and piece.row >= 6:  # 黑方象在红方区域
                        # 在敌方区域，象的价值增加
                        special_value += 150
                        
                        # 检查象在敌方区域是否能攻击敌方棋子
                        attackable_count = 0
                        for dr in [-2, 0, 2]:  # 横向移动2格
                            for dc in [-2, 0, 2]:
                                if (dr != 0 and dc == 0) or (dr == 0 and dc != 0):  # 只考虑横竖方向
                                    target_row, target_col = piece.row + dr, piece.col + dc
                                    if 0 <= target_row < 13 and 0 <= target_col < 13:
                                        # 检查中间是否有棋子（塞相眼）
                                        mid_row, mid_col = piece.row + dr//2, piece.col + dc//2
                                        if not game_state.get_piece_at(mid_row, mid_col):
                                            # 检查目标位置是否有敌方棋子
                                            target_piece = game_state.get_piece_at(target_row, target_col)
                                            if target_piece and target_piece.color != color:
                                                attackable_count += 1
                        special_value += attackable_count * 30
                
                # 评估尉/衛的跳跃能力
                elif isinstance(piece, Wei):
                    # 尉的跳跃能力在复杂局面中更有价值
                    # 统计周围棋子数量
                    adjacent_pieces = 0
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            adj_row, adj_col = piece.row + dr, piece.col + dc
                            if 0 <= adj_row < 13 and 0 <= adj_col < 13:
                                adj_piece = game_state.get_piece_at(adj_row, adj_col)
                                if adj_piece:
                                    adjacent_pieces += 1
                    
                    # 周围棋子越多，尉的跳跃能力越有价值
                    special_value += adjacent_pieces * 15
                    
                    # 尉在中心区域更有价值
                    if 4 <= piece.row <= 8 and 4 <= piece.col <= 8:
                        special_value += 20
                    
                    # 检查尉是否能跨越棋子影响棋盘格局
                    crossable_count = 0
                    # 检查四个方向上是否有可跨越的棋子
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        r, c = piece.row + dr, piece.col + dc
                        while 0 <= r < 13 and 0 <= c < 13:
                            if game_state.get_piece_at(r, c):
                                crossable_count += 1
                                break
                            r += dr
                            c += dc
                    special_value += crossable_count * 10
                
                # 评估檑/礌的攻击能力
                elif isinstance(piece, Lei):
                    # 统计可以攻击的孤立敌方棋子数量
                    attackable_count = 0
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            target_row, target_col = piece.row + dr, piece.col + dc
                            if 0 <= target_row < 13 and 0 <= target_col < 13:
                                target_piece = game_state.get_piece_at(target_row, target_col)
                                if target_piece and target_piece.color != color:
                                    # 检查目标棋子是否孤立
                                    isolated = True
                                    for adj_dr in [-1, 0, 1]:
                                        for adj_dc in [-1, 0, 1]:
                                            if adj_dr == 0 and adj_dc == 0:
                                                continue
                                            adj_row, adj_col = target_row + adj_dr, target_col + adj_dc
                                            if 0 <= adj_row < 13 and 0 <= adj_col < 13:
                                                adj_piece = game_state.get_piece_at(adj_row, adj_col)
                                                if adj_piece and adj_piece.color == target_piece.color:
                                                    isolated = False
                                                    break
                                        if not isolated:
                                            break
                                    if isolated:
                                        attackable_count += 1
                    
                    # 檑可以攻击的孤立棋子越多，价值越高
                    special_value += attackable_count * 80
                
                # 评估刺的兑子能力
                elif isinstance(piece, Ci):
                    # 检查移动前起始位置的反方向一格是否有敌棋（兑子条件）
                    # 遍历可能的移动方向
                    for dr in [-1, 1]:
                        for dc in [-1, 1]:
                            # 检查直线方向
                            for dist in range(1, 13):
                                to_row = piece.row + dr * dist
                                to_col = piece.col + dc * dist
                                
                                # 检查目标位置是否在棋盘范围内
                                if not (0 <= to_row < 13 and 0 <= to_col < 13):
                                    break
                                
                                # 检查路径上是否有阻挡
                                blocked = False
                                for step in range(1, dist + 1):
                                    check_row = piece.row + dr * step
                                    check_col = piece.col + dc * step
                                    if game_state.get_piece_at(check_row, check_col):
                                        if (check_row, check_col) != (to_row, to_col):  # 路径阻挡
                                            blocked = True
                                            break
                                        else:  # 到达目标位置
                                            if game_state.get_piece_at(check_row, check_col):  # 目标位置有棋子
                                                blocked = True  # 刺不能吃子，目标必须为空
                                                break
                                            break
                                
                                if blocked:
                                    break
                                
                                # 计算起始位置的反方向
                                reverse_row = piece.row - dr
                                reverse_col = piece.col - dc
                                
                                # 检查反方向是否有敌方棋子（可以兑子）
                                if 0 <= reverse_row < 13 and 0 <= reverse_col < 13:
                                    reverse_piece = game_state.get_piece_at(reverse_row, reverse_col)
                                    if reverse_piece and reverse_piece.color != color:
                                        # 可以进行兑子，增加价值
                                        special_value += 200  # 兑子价值很高
                                
                                # 刺移动到该位置
                                break
                
                # 评估盾的防守价值
                elif isinstance(piece, Dun):
                    # 盾的价值在于其保护作用，与敌方棋子相邻时能提供保护
                    connected_enemy_count = 0
                    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
                    
                    for dr, dc in directions:
                        adj_row = piece.row + dr
                        adj_col = piece.col + dc
                        
                        if 0 <= adj_row < 13 and 0 <= adj_col < 13:
                            adj_piece = game_state.get_piece_at(adj_row, adj_col)
                            if adj_piece and adj_piece.color != color:
                                connected_enemy_count += 1
                    
                    # 与敌方棋子连接的数量越多，盾的防守价值越高
                    special_value += connected_enemy_count * 50
                    
                    # 盾不可被吃，增加其基础价值
                    special_value += 100
        
        return special_value
    
    def _evaluate_piece_coordination(self, game_state, color):
        """评估棋子协调性"""
        coordination_score = 0
        
        # 获取所有己方棋子
        own_pieces = [p for p in game_state.pieces if p.color == color]
        
        # 计算棋子间的协同效应
        for i, piece1 in enumerate(own_pieces):
            for piece2 in own_pieces[i+1:]:
                # 计算两棋子间的距离
                distance = abs(piece1.row - piece2.row) + abs(piece1.col - piece2.col)
                
                # 如果距离适中（不是太近也不是太远），增加协同价值
                if 2 <= distance <= 5:
                    # 检查是否有协同攻击可能
                    coordination_score += 5
        
        # 评估甲/胄的连线攻击能力
        jia_pieces = [p for p in own_pieces if isinstance(p, Jia)]
        for jia in jia_pieces:
            # 检查是否有形成2己1敌连线的可能
            # 水平方向检查
            for col_offset in [-2, -1, 1, 2]:
                if 0 <= jia.col + col_offset < 13 and 0 <= jia.col + 2*col_offset < 13:
                    piece1 = game_state.get_piece_at(jia.row, jia.col + col_offset)
                    piece2 = game_state.get_piece_at(jia.row, jia.col + 2*col_offset)
                    if piece1 and piece2 and piece1.color != color and piece2.color != color:
                        # 有潜在的连线攻击可能
                        coordination_score += 30
            
            # 垂直方向检查
            for row_offset in [-2, -1, 1, 2]:
                if 0 <= jia.row + row_offset < 13 and 0 <= jia.row + 2*row_offset < 13:
                    piece1 = game_state.get_piece_at(jia.row + row_offset, jia.col)
                    piece2 = game_state.get_piece_at(jia.row + 2*row_offset, jia.col)
                    if piece1 and piece2 and piece1.color != color and piece2.color != color:
                        # 有潜在的连线攻击可能
                        coordination_score += 30
        
        return coordination_score
    
    def _get_piece_value(self, piece):
        """获取棋子基础价值"""
        if not piece:
            return 0
        return self.piece_values.get(piece.name, 0)
    
    def _get_position_value(self, piece):
        """获取棋子在特定位置的附加价值"""
        if not piece:
            return 0
            
        return self._get_position_value_at_pos(piece, piece.row, piece.col)
    
    def _get_position_value_at_pos(self, piece, row, col):
        """获取棋子在特定位置的附加价值"""
        if not piece:
            return 0
            
        # 根据棋子类型选择相应的位置价值表
        if isinstance(piece, Pawn):
            if piece.color == "red":
                return self.pawn_pos_red[row][col]
            else:
                return self.pawn_pos_black[row][col]
        
        elif isinstance(piece, Ju):
            if piece.color == "red":
                return self.rook_pos_red[row][col]
            else:
                return self.rook_pos_black[row][col]
        
        elif isinstance(piece, Ma):
            if piece.color == "red":
                return self.knight_pos_red[row][col]
            else:
                return self.knight_pos_black[row][col]
        
        elif isinstance(piece, Pao):
            if piece.color == "red":
                return self.cannon_pos_red[row][col]
            else:
                return self.cannon_pos_black[row][col]
        
        elif isinstance(piece, Xiang):
            if piece.color == "red":
                return self.bishop_pos_red[row][col]
            else:
                return self.bishop_pos_black[row][col]
        
        elif isinstance(piece, Shi):
            if piece.color == "red":
                return self.advisor_pos_red[row][col]
            else:
                return self.advisor_pos_black[row][col]
        
        elif isinstance(piece, King):
            if piece.color == "red":
                return self.base_pos_value[row][col] + 50  # 王在九宫格内更有价值
            else:
                return self.base_pos_value[row][col] + 50
        
        elif isinstance(piece, Wei):
            if piece.color == "red":
                return self.guard_pos_red[row][col]
            else:
                return self.guard_pos_black[row][col]
                
        elif isinstance(piece, She):
            if piece.color == "red":
                return self.archer_pos_red[row][col]
            else:
                return self.archer_pos_black[row][col]
                
        elif isinstance(piece, Lei):
            if piece.color == "red":
                return self.rock_pos_red[row][col]
            else:
                return self.rock_pos_black[row][col]
                
        elif isinstance(piece, Jia):
            if piece.color == "red":
                return self.armor_pos_red[row][col]
            else:
                return self.armor_pos_black[row][col]
        
        return self.base_pos_value[row][col]
    
    def _is_check(self, game_state, color):
        """检查指定颜色是否被将军"""
        # 这里复用游戏规则已有的检查
        return color == game_state.player_turn and game_state.is_check
    
    def _is_in_check_for_current_player(self, game_state):
        """检查当前玩家是否被将军"""
        return game_state.is_check
    
    def _clone_game_state(self, game_state):
        """创建游戏状态的高效深拷贝用于模拟"""
        # 使用更高效的克隆方法

        # 创建一个新的game_state对象
        cloned_state = type('GameStateClone', (), {})()
        
        # 快速克隆棋子列表
        cloned_state.pieces = []
        for piece in game_state.pieces:
            cloned_piece = type('PieceClone', (), {})()
            cloned_piece.color = piece.color
            cloned_piece.name = piece.name
            cloned_piece.row = piece.row
            cloned_piece.col = piece.col
            cloned_state.pieces.append(cloned_piece)
        
        cloned_state.player_turn = game_state.player_turn
        cloned_state.game_over = game_state.game_over
        cloned_state.winner = game_state.winner
        cloned_state.is_check = game_state.is_check
        cloned_state.move_history = getattr(game_state, 'move_history', [])[:]
        cloned_state.captured_pieces = {
            'red': getattr(game_state, 'captured_pieces', {}).get('red', [])[:],
            'black': getattr(game_state, 'captured_pieces', {}).get('black', [])[:]
        }
        
        # 添加必要的方法
        def get_piece_at(row, col):
            for p in cloned_state.pieces:
                if p.row == row and p.col == col:
                    return p
            return None
        
        cloned_state.get_piece_at = get_piece_at
        cloned_state.calculate_possible_moves = game_state.calculate_possible_moves
        cloned_state.is_valid_move = getattr(game_state, 'is_valid_move', None)
        
        return cloned_state
    
    def _make_move(self, game_state, from_pos, to_pos):
        """在克隆的游戏状态中执行移动"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        # 找出要移动的棋子
        moving_piece = None
        for piece in game_state.pieces:
            if piece.row == from_row and piece.col == from_col:
                moving_piece = piece
                break
        
        if not moving_piece:
            return False
        
        # 查找目标位置是否有棋子（吃子）
        target_piece = None
        for piece in game_state.pieces:
            if piece.row == to_row and piece.col == to_col:
                target_piece = piece
                break
        
        # 如果有目标棋子，从列表中移除
        if target_piece:
            game_state.pieces.remove(target_piece)
        
        # 更新棋子位置
        moving_piece.row = to_row
        moving_piece.col = to_col
        
        # 切换回合
        game_state.player_turn = "red" if game_state.player_turn == "black" else "black"
        
        # 更新将军状态
        game_state.is_check = False  # 在实际游戏中这个会根据规则更新，这里简化处理
        
        return True
    
    def _get_state_key(self, game_state):
        """生成棋盘状态的唯一键，用于置换表"""
        # 简单实现，使用棋子位置组合
        pieces_str = ""
        for piece in sorted(game_state.pieces, key=lambda p: (p.color, p.name, p.row, p.col)):
            pieces_str += f"{piece.name}:{piece.color}:{piece.row}:{piece.col}|"
        
        return pieces_str + game_state.player_turn 

    def _evaluate_piece_threats_simple(self, game_state, piece):
        """简化版：评估棋子受到的威胁"""
        if not piece:
            return 0
        
        threat_value = 0
        opponent_color = "red" if piece.color == "black" else "black"
        
        # 简化：只检查对方是否可以直接吃掉当前棋子
        for opp_piece in game_state.pieces:
            if opp_piece.color == opponent_color:
                # 检查是否可以直接吃掉
                if self._can_capture_simple(game_state, opp_piece, piece):
                    # 威胁值与威胁棋子价值相关
                    threat_value += self._get_piece_value(piece) * 0.3  # 简化威胁系数
        
        return threat_value

    def _evaluate_piece_protection_simple(self, game_state, piece):
        """简化版：评估棋子受到的保护"""
        if not piece:
            return 0
        
        protection_value = 0
        
        # 简化：只检查己方棋子是否可以保护当前棋子
        for friendly_piece in game_state.pieces:
            if friendly_piece != piece and friendly_piece.color == piece.color:
                # 检查是否可以保护
                if self._can_protect_simple(game_state, friendly_piece, piece):
                    protection_value += self._get_piece_value(piece) * 0.2  # 简化保护系数
        
        return protection_value

    def _evaluate_center_control_simple(self, game_state, color):
        """简化版：评估对中心区域的控制"""
        # 定义中心区域 (行5-7, 列5-7)
        center_rows = [5, 6, 7]
        center_cols = [5, 6, 7]
        
        control_score = 0
        
        # 计算在中心区域的棋子数量
        for piece in game_state.pieces:
            if piece.color == color:
                # 棋子在中心区域得分
                if piece.row in center_rows and piece.col in center_cols:
                    # 根据棋子类型给予不同分数
                    piece_value = self._get_piece_value(piece)
                    control_score += max(1, piece_value // 100)  # 简化计算
        
        return control_score

    def _evaluate_king_safety_simple(self, game_state, color):
        """简化版：评估王的安全性"""
        # 找出王
        king = None
        for piece in game_state.pieces:
            if isinstance(piece, King) and piece.color == color:
                king = piece
                break
        
        if not king:
            return -500  # 没有王，非常危险
        
        safety_score = 0
        
        # 王在九宫格中央更安全
        if color == "red":
            if 9 <= king.row <= 11 and 5 <= king.col <= 7:  # 红方王在九宫内
                safety_score += 30
        else:  # black
            if 1 <= king.row <= 3 and 5 <= king.col <= 7:  # 黑方王在九宫内
                safety_score += 30
        
        return safety_score
    
    def _evaluate_special_abilities_simple(self, game_state, color):
        """简化版：评估特殊棋子能力的价值"""
        special_value = 0
        
        for piece in game_state.pieces:
            if piece.color == color:
                # 评估相/象在敌方区域的特殊能力
                if isinstance(piece, Xiang):
                    # 检查相是否在敌方区域
                    if color == "red" and piece.row <= 6:  # 红方相在黑方区域
                        special_value += 150  # 提高价值
                        # 检查相在敌方区域是否能攻击敌方棋子
                        attackable_count = 0
                        for dr in [-2, 0, 2]:  # 横向移动2格
                            for dc in [-2, 0, 2]:
                                if (dr != 0 and dc == 0) or (dr == 0 and dc != 0):  # 只考虑横竖方向
                                    target_row, target_col = piece.row + dr, piece.col + dc
                                    if 0 <= target_row < 13 and 0 <= target_col < 13:
                                        # 检查中间是否有棋子（塞相眼）
                                        mid_row, mid_col = piece.row + dr//2, piece.col + dc//2
                                        if not game_state.get_piece_at(mid_row, mid_col):
                                            # 检查目标位置是否有敌方棋子
                                            target_piece = game_state.get_piece_at(target_row, target_col)
                                            if target_piece and target_piece.color != color:
                                                attackable_count += 1
                        special_value += attackable_count * 40
                    elif color == "black" and piece.row >= 6:  # 黑方象在红方区域
                        special_value += 150  # 提高价值
                        # 检查象在敌方区域是否能攻击敌方棋子
                        attackable_count = 0
                        for dr in [-2, 0, 2]:  # 横向移动2格
                            for dc in [-2, 0, 2]:
                                if (dr != 0 and dc == 0) or (dr == 0 and dc != 0):  # 只考虑横竖方向
                                    target_row, target_col = piece.row + dr, piece.col + dc
                                    if 0 <= target_row < 13 and 0 <= target_col < 13:
                                        # 检查中间是否有棋子（塞相眼）
                                        mid_row, mid_col = piece.row + dr//2, piece.col + dc//2
                                        if not game_state.get_piece_at(mid_row, mid_col):
                                            # 检查目标位置是否有敌方棋子
                                            target_piece = game_state.get_piece_at(target_row, target_col)
                                            if target_piece and target_piece.color != color:
                                                attackable_count += 1
                        special_value += attackable_count * 40
                # 评估尉/衛的跳跃能力
                elif isinstance(piece, Wei):
                    # 尉在中心区域更有价值
                    if 4 <= piece.row <= 8 and 4 <= piece.col <= 8:
                        special_value += 25  # 提高价值
                    # 评估尉的跳跃能力在复杂局面中的价值
                    adjacent_pieces = 0
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            adj_row, adj_col = piece.row + dr, piece.col + dc
                            if 0 <= adj_row < 13 and 0 <= adj_col < 13:
                                adj_piece = game_state.get_piece_at(adj_row, adj_col)
                                if adj_piece:
                                    adjacent_pieces += 1
                    special_value += adjacent_pieces * 10
                # 评估檑/礌的攻击能力
                elif isinstance(piece, Lei):
                    # 统计可以攻击的孤立敌方棋子数量
                    attackable_count = 0
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            target_row, target_col = piece.row + dr, piece.col + dc
                            if 0 <= target_row < 13 and 0 <= target_col < 13:
                                target_piece = game_state.get_piece_at(target_row, target_col)
                                if target_piece and target_piece.color != color:
                                    # 检查目标棋子是否孤立
                                    if self._is_isolated_simple(game_state, target_piece):
                                        attackable_count += 1
                    # 提高檑的攻击价值
                    special_value += attackable_count * 70
                
                # 评估刺的兑子能力
                elif isinstance(piece, Ci):
                    # 检查移动前起始位置的反方向一格是否有敌棋（兑子条件）
                    # 遍历可能的移动方向
                    for dr in [-1, 1]:
                        for dc in [-1, 1]:
                            # 检查直线方向
                            for dist in range(1, 13):
                                to_row = piece.row + dr * dist
                                to_col = piece.col + dc * dist
                                
                                # 检查目标位置是否在棋盘范围内
                                if not (0 <= to_row < 13 and 0 <= to_col < 13):
                                    break
                                
                                # 检查路径上是否有阻挡
                                blocked = False
                                for step in range(1, dist + 1):
                                    check_row = piece.row + dr * step
                                    check_col = piece.col + dc * step
                                    if game_state.get_piece_at(check_row, check_col):
                                        if (check_row, check_col) != (to_row, to_col):  # 路径阻挡
                                            blocked = True
                                            break
                                        else:  # 到达目标位置
                                            if game_state.get_piece_at(check_row, check_col):  # 目标位置有棋子
                                                blocked = True  # 刺不能吃子，目标必须为空
                                                break
                                            break
                                
                                if blocked:
                                    break
                                
                                # 计算起始位置的反方向
                                reverse_row = piece.row - dr
                                reverse_col = piece.col - dc
                                
                                # 检查反方向是否有敌方棋子（可以兑子）
                                if 0 <= reverse_row < 13 and 0 <= reverse_col < 13:
                                    reverse_piece = game_state.get_piece_at(reverse_row, reverse_col)
                                    if reverse_piece and reverse_piece.color != color:
                                        # 可以进行兑子，增加价值
                                        special_value += 180  # 兑子价值很高
                                
                                # 刺移动到该位置
                                break
                
                # 评估盾的防守价值
                elif isinstance(piece, Dun):
                    # 盾的价值在于其保护作用，与敌方棋子相邻时能提供保护
                    connected_enemy_count = 0
                    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
                    
                    for dr, dc in directions:
                        adj_row = piece.row + dr
                        adj_col = piece.col + dc
                        
                        if 0 <= adj_row < 13 and 0 <= adj_col < 13:
                            adj_piece = game_state.get_piece_at(adj_row, adj_col)
                            if adj_piece and adj_piece.color != color:
                                connected_enemy_count += 1
                    
                    # 与敌方棋子连接的数量越多，盾的防守价值越高
                    special_value += connected_enemy_count * 40
                    
                    # 盾不可被吃，增加其基础价值
                    special_value += 80
        
        return special_value

    def _can_capture_simple(self, game_state, attacker, target):
        """简化版：检查攻击棋子是否可以吃掉目标棋子"""
        # 使用游戏规则检查移动是否合法
        from  program.core.game_rules import GameRules
        return GameRules.is_valid_move(game_state.pieces, attacker, attacker.row, attacker.col, target.row, target.col)

    def _can_protect_simple(self, game_state, protector, protected_piece):
        """简化版：检查保护棋子是否可以保护被保护棋子"""
        from program.core.game_rules import GameRules
        return GameRules.is_valid_move(game_state.pieces, protector, protector.row, protector.col, protected_piece.row, protected_piece.col)

    def _is_isolated_simple(self, game_state, piece):
        """简化版：检查棋子是否孤立"""
        from program.core.game_rules import GameRules
        return GameRules.is_isolated(piece, game_state.pieces)
    
    def _evaluate_piece_coordination_simple(self, game_state, color):
        """简化版：评估棋子协调性"""
        coordination_score = 0
        
        # 获取所有己方棋子
        own_pieces = [p for p in game_state.pieces if p.color == color]
        
        # 计算棋子间的协同效应
        for i, piece1 in enumerate(own_pieces):
            for piece2 in own_pieces[i+1:]:
                # 计算两棋子间的距离
                distance = abs(piece1.row - piece2.row) + abs(piece1.col - piece2.col)
                
                # 如果距离适中（不是太近也不是太远），增加协同价值
                if 2 <= distance <= 5:
                    # 检查是否有协同攻击可能
                    coordination_score += 8
        
        # 评估甲/胄的连线攻击能力
        jia_pieces = [p for p in own_pieces if isinstance(p, Jia)]
        for jia in jia_pieces:
            # 检查是否有形成2己1敌连线的可能
            # 水平方向检查
            for col_offset in [-2, -1, 1, 2]:
                if 0 <= jia.col + col_offset < 13 and 0 <= jia.col + 2*col_offset < 13:
                    piece1 = game_state.get_piece_at(jia.row, jia.col + col_offset)
                    piece2 = game_state.get_piece_at(jia.row, jia.col + 2*col_offset)
                    if piece1 and piece2 and piece1.color != color and piece2.color != color:
                        # 有潜在的连线攻击可能
                        coordination_score += 40
            
            # 垂直方向检查
            for row_offset in [-2, -1, 1, 2]:
                if 0 <= jia.row + row_offset < 13 and 0 <= jia.row + 2*row_offset < 13:
                    piece1 = game_state.get_piece_at(jia.row + row_offset, jia.col)
                    piece2 = game_state.get_piece_at(jia.row + 2*row_offset, jia.col)
                    if piece1 and piece2 and piece1.color != color and piece2.color != color:
                        # 有潜在的连线攻击可能
                        coordination_score += 40
        
        return coordination_score
    
    def _update_history_move(self, from_pos, to_pos, depth):
        """更新历史表，记录导致剪枝的好走法"""
        key = (from_pos, to_pos)
        self.history_table[key] = self.history_table.get(key, 0) + depth * depth