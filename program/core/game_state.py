import time

import program.utils.tools as tools
from program.controllers.game_config_manager import game_config
from program.controllers.statistics_manager import statistics_manager
from program.controllers.step_counter import step_counter
from program.core.chess_pieces import create_initial_pieces, King, Jia, Ci, Dun, Pawn, Wei
from program.core.game_rules import GameRules
from program.utils.utils import print_board


class GameState:
    """游戏状态管理类，负责维护当前棋局、历史记录和状态判断"""

    @staticmethod
    def is_position_on_board(row, col):
        """检查位置是否在棋盘范围内

        Args:
            row (int): 行坐标
            col (int): 列坐标

        Returns:
            bool: 位置是否在棋盘范围内
        """
        if GameRules.traditional_mode:
            # 传统中国象棋：9列 x 10行 (0-8列, 0-9行)
            return 0 <= row < 10 and 0 <= col < 9
        else:
            # 匈汉象棋：13列 x 13行 (0-12列, 0-12行)
            return 0 <= row < 13 and 0 <= col < 13

    def __init__(self):
        """初始化游戏状态"""
        # 初始化棋子
        self.is_game_over = None
        self.pieces = create_initial_pieces()

        # 游戏状态
        self.player_turn = "red"  # 红方先行
        self.game_over = False
        self.winner = None

        # 将军状态
        self.is_check = False  # 当前是否有一方被将军
        self.check_animation_time = 0  # 将军动画开始的时间戳
        self.check_animation_duration = 4.0  # 将军动画持续时间（秒），延长为4秒

        # 历史记录 - 用于悔棋功能
        self.move_history = []  # 存储 (piece, from_row, from_col, to_row, to_col, captured_piece)

        # 阵亡棋子记录
        self.captured_pieces = {"red": [], "black": []}  # 记录双方阵亡的棋子

        # 时间跟踪
        self.start_time = time.time()  # 游戏开始时间
        self.total_time = 0  # 游戏总时长（秒）
        self.red_time = 0  # 红方已用时间（秒）
        self.black_time = 0  # 黑方已用时间（秒）
        self.current_turn_start_time = time.time()  # 当前回合开始时间

        # 升变相关属性
        self.needs_promotion = False  # 是否需要升变
        self.promotion_pawn = None  # 需要升变的兵/卒
        self.available_promotion_pieces = []  # 可供升变的阵亡棋子

        # 升变完成标志
        self.just_completed_promotion = False  # 记录是否刚刚完成升变

        # 添加局面历史记录，用于检测重复局面
        self.board_position_history = []  # 记录局面哈希值的历史
        self.repetition_count = {}  # 记录每个局面出现的次数

        # 统计数据跟踪
        self.moves_count = 0  # 当前对局走子数

        self.history_scroll_y = 0

        # 尉照面追踪：记录当前被尉照面的棋子
        self.facing_pairs = []  # 存储 (wei_piece, facing_target_piece) 的元组

    def get_piece_at(self, row, col):
        """获取指定位置的棋子"""
        return GameRules.get_piece_at(self.pieces, row, col)

    def update_facing_pairs(self):
        """更新尉照面关系"""
        self.facing_pairs = []
        for piece in self.pieces:
            if isinstance(piece, Wei) and GameRules.is_facing_enemy(piece, self.pieces):
                facing_target = GameRules.get_facing_piece(piece, self.pieces)
                if facing_target:
                    self.facing_pairs.append((piece, facing_target))

    def move_piece(self, from_row, from_col, to_row, to_col):
        """移动棋子
        
        Args:
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 移动是否成功
        """
        # 获取要移动的棋子
        piece = self.get_piece_at(from_row, from_col)
        if not piece or piece.color != self.player_turn:
            return False

        # 更新尉照面关系，然后再检查移动是否合法
        self.update_facing_pairs()
        if not GameRules.is_valid_move(self.pieces, piece, from_row, from_col, to_row, to_col):
            return False

        # 检查移动后是否会导致自己被将军（送将）
        if GameRules.would_be_in_check_after_move(self.pieces, piece, to_row, to_col):
            return False

        # 获取目标位置的棋子（如果有）
        captured_piece = self.get_piece_at(to_row, to_col)

        # 记录移动历史 - 暂时不包括甲/胄连线吃子和刺兑子（因为需要在移动后检测）
        # 先创建临时记录
        temp_move_record = (
            piece,
            from_row,
            from_col,
            to_row,
            to_col,
            captured_piece
        )

        # 更新当前玩家的用时
        current_time = time.time()
        elapsed = max(0.0, current_time - self.current_turn_start_time)  # 确保elapsed不为负数
        if self.player_turn == "red":
            self.red_time += elapsed
        else:
            self.black_time += elapsed

        # 如果有棋子被吃掉（直接移动到目标位置的棋子），移除它并记录到阵亡列表
        if captured_piece:

            self.pieces.remove(captured_piece)
            self.captured_pieces[captured_piece.color].append(captured_piece)

            piece_type = captured_piece.__class__.__name__.lower()
            statistics_manager.update_pieces_captured(piece_type, 1)

            # 如果吃掉的是对方将/帅/汉/汗，游戏结束
            if isinstance(captured_piece, King):
                self.game_over = True
                self.winner = piece.color
                # 更新游戏总时长
                self.total_time = max(0.0, current_time - self.start_time)
                return True

        # 执行移动
        piece.move_to(to_row, to_col)

        # 打印当前棋局状态
        print_board(self.pieces, [step_counter.get_step()], show_step=True)

        # 增加步数计数器
        step_counter.increment()

        # 处理甲/胄的特殊吃子规则（移动后检查）- 这是关键步骤
        jia_captured_pieces = []
        if isinstance(piece, Jia):
            # 查找所有被吃掉的敌方棋子 - 在棋子移动到新位置后检查
            jia_captured_pieces = GameRules.find_jia_capture_moves(self.pieces, piece)

        # 处理刺的兑子规则
        ci_captured_pieces = []  # 记录刺兑子时涉及的棋子
        if isinstance(piece, Ci):
            # 检查移动前起始位置的反方向一格是否有敌棋（兑子条件）
            row_diff = to_row - from_row
            col_diff = to_col - from_col

            # 计算起始位置的反方向
            reverse_row = from_row - row_diff
            reverse_col = from_col - col_diff

            # 检查反方向位置是否在棋盘范围内
            if GameState.is_position_on_board(reverse_row, reverse_col):
                reverse_piece = GameRules.get_piece_at(self.pieces, reverse_row, reverse_col)
                # 如果反方向有敌方棋子，则进行兑子（双方都阵亡）
                if reverse_piece and reverse_piece.color != piece.color:
                    # 检查反方向的棋子是否是盾（盾不可被兑子）
                    if not isinstance(reverse_piece, Dun):
                        # 检查移动的刺是否与敌方盾相邻（8邻域），如果是则不能触发兑子
                        shield_nearby = False
                        for p in self.pieces:
                            if isinstance(p, Dun) and p.color != piece.color:
                                # 检查该敌方盾是否与移动的刺相邻（8邻域）
                                row_diff_to_dun = abs(p.row - to_row)  # 检查移动后的位置
                                col_diff_to_dun = abs(p.col - to_col)
                                if row_diff_to_dun <= 1 and col_diff_to_dun <= 1 and (
                                        row_diff_to_dun != 0 or col_diff_to_dun != 0):
                                    shield_nearby = True
                                    break

                        if not shield_nearby:
                            # 执行兑子：移除刺和反方向的敌棋
                            if piece in self.pieces:
                                self.pieces.remove(piece)
                                self.captured_pieces[piece.color].append(piece)
                                ci_captured_pieces.append(piece)  # 记录刺自身（虽然它不是被吃掉的，但参与了兑子）
                            # 移除反方向的敌方棋子
                            if reverse_piece in self.pieces:
                                self.pieces.remove(reverse_piece)
                                self.captured_pieces[reverse_piece.color].append(reverse_piece)
                                ci_captured_pieces.append(reverse_piece)  # 记录被兑掉的敌方棋子

                                # 如果吃掉的是对方将/帅/汉/汗，游戏结束
                                if isinstance(reverse_piece, King):
                                    self.game_over = True
                                    self.winner = piece.color
                                    # 更新游戏总时长
                                    current_time = time.time()
                                    self.total_time = max(0.0, current_time - self.start_time)
                                    # 现在将完整的记录添加到历史中，包括甲/胄吃子信息和刺兑子信息
                                    self.move_history.append(temp_move_record + (
                                    jia_captured_pieces[:], ci_captured_pieces[:]))  # 添加甲/胄吃子信息和刺兑子信息
                                    return True

                            # 由于刺和敌棋都被移除了，无需继续处理
                            # 切换玩家
                            opponent_color = "black" if self.player_turn == "red" else "red"

                            # 检查是否将军
                            self.is_check = GameRules.is_check(self.pieces, opponent_color)
                            if self.is_check:
                                # 设置将军动画计时器
                                self.check_animation_time = current_time

                            # 检查是否将死或获胜
                            game_over, winner = GameRules.is_game_over(self.pieces, self.player_turn)

                            if game_over:
                                self.game_over = True
                                self.winner = winner
                                # 更新游戏总时长
                                self.total_time = max(0.0, current_time - self.start_time)
                            else:
                                # 切换玩家回合
                                self.player_turn = opponent_color
                                # 重置当前回合开始时间
                                self.current_turn_start_time = current_time

                            # 现在将完整的记录添加到历史中，包括甲/胄吃子信息和刺兑子信息
                            self.move_history.append(
                                temp_move_record + (jia_captured_pieces[:], ci_captured_pieces[:]))  # 添加甲/胄吃子信息和刺兑子信息

                            return True

        # 现在将完整的记录添加到历史中
        self.move_history.append(temp_move_record + (jia_captured_pieces[:], ci_captured_pieces[:]))  # 添加甲/胄吃子信息和刺兑子信息

        # 更新走子计数
        self.moves_count += 1
        statistics_manager.update_total_moves(1)

        # 实际移除甲/胄连线吃掉的棋子
        for captured in jia_captured_pieces:
            if captured in self.pieces:
                self.pieces.remove(captured)
                self.captured_pieces[captured.color].append(captured)

                # 直接使用类名作为统计类型
                piece_type = captured_piece.__class__.__name__.lower()

                # 更新统计数据
                statistics_manager.update_pieces_captured(piece_type, 1)

                # 如果吃掉的是对方将/帅/汉/汗，游戏结束
                if isinstance(captured, King):
                    self.game_over = True
                    self.winner = piece.color
                    # 更新游戏总时长
                    current_time = time.time()
                    self.total_time = max(0.0, current_time - self.start_time)
                    return True

        # 检查兵/卒是否到达对方底线，触发升变
        if (isinstance(piece, Pawn) and tools.is_pawn_at_opponent_base(piece, to_row) and
                game_config.get_setting("pawn_promotion_enabled", True)):
            print(f"[DEBUG] 兵到达对方底线: {piece.color}兵从({from_row},{from_col})移动到({to_row},{to_col})")
            # 标记需要进行升变，但实际升变将在游戏主循环中处理
            self.needs_promotion = True
            self.promotion_pawn = piece
            self.available_promotion_pieces = self.get_available_promotion_pieces(piece.color)

            # 不立即切换玩家回合，等待升变完成后再切换
        else:
            # 重置升变标志
            self.needs_promotion = False
            self.promotion_pawn = None
            self.available_promotion_pieces = []

            # 切换玩家
            opponent_color = "black" if self.player_turn == "red" else "red"

            # 检查是否将军（在检查游戏结束之前）
            self.is_check = GameRules.is_check(self.pieces, opponent_color)
            if self.is_check:
                # 设置将军动画计时器
                self.check_animation_time = current_time
                print(f"[DEBUG] 检测到将军状态，被将军方: {opponent_color}")

            # 检查是否将死或获胜
            game_over, winner = GameRules.is_game_over(self.pieces, self.player_turn)

            if game_over:
                self.game_over = True
                self.winner = winner
                # 更新游戏总时长
                self.total_time = max(0.0, current_time - self.start_time)
                # 更新统计数据
                statistics_manager.update_games_played(1)
                statistics_manager.update_game_result(winner, self.total_time)
            else:
                # 检查是否和棋
                if self.is_draw():
                    self.game_over = True
                    self.winner = None  # 和棋没有获胜方

                # 切换玩家回合
                self.player_turn = opponent_color
                # 重置当前回合开始时间
                self.current_turn_start_time = current_time
                print(f"[DEBUG] 移动后切换玩家: {opponent_color}")

        return True

    def handle_captured_piece(self, captured_piece, current_time=time.time()):
        """处理被吃掉的棋子

        Args:
            captured_piece: 被吃掉的棋子
            current_time: 当前时间，默认为当前时刻

        Returns:
            tuple: (piece_type, should_end_game, winner_or_none, total_time_if_ends)
        """
        # 从棋盘上移除棋子并记录到阵亡列表
        self.pieces.remove(captured_piece)
        self.captured_pieces[captured_piece.color].append(captured_piece)

        # 直接使用类名作为统计类型
        piece_type = captured_piece.__class__.__name__.lower()

        # 更新统计数据
        statistics_manager.update_pieces_captured(piece_type, 1)

        # 检查是否吃掉了对方将/帅/汉/汗，游戏结束
        if isinstance(captured_piece, King):
            # 更新游戏总时长
            self.total_time = max(0.0, current_time - self.start_time)
            return piece_type, True, captured_piece.color, max(0.0, current_time - self.start_time)

        return piece_type, False, None, None

    def is_draw(self):
        """检查是否和棋
        
        Returns:
            bool: 是否和棋
        """
        # 检查是否为不可能取胜的简单局势
        if GameRules.has_insufficient_material(self.pieces):
            return True

        # 检查是否出现困毙
        if GameRules.is_stalemate(self.pieces, self.player_turn):
            return True

        # 检查是否出现循环反复的局面（重复三次）
        # 这里需要先更新局面历史
        board_hash = GameRules.get_board_hash(self.pieces)

        # 更新局面历史记录
        self.board_position_history.append(board_hash)

        # 更新重复计数
        if board_hash in self.repetition_count:
            self.repetition_count[board_hash] += 1
        else:
            self.repetition_count[board_hash] = 1

        # 如果某个局面出现了3次或以上，视为和棋
        if self.repetition_count[board_hash] >= 3:
            return True

        # 使用GameRules中的方法检测重复局面
        if GameRules.is_repeated_move(self.board_position_history, 3):
            return True

        return False

    def reset_draw_tracking(self):
        """重置和棋追踪数据"""
        self.board_position_history = []
        self.repetition_count = {}

    def get_draw_reason(self):
        """获取和棋原因
        
        Returns:
            str: 和棋原因描述
        """
        if GameRules.has_insufficient_material(self.pieces):
            return "双方均无可能取胜的简单局势"
        if GameRules.is_stalemate(self.pieces, self.player_turn):
            return "困毙（无子可走）"

        # 检查重复局面
        board_hash = GameRules.get_board_hash(self.pieces)
        if board_hash in self.repetition_count and self.repetition_count[board_hash] >= 3:
            return "循环反复三次局面"

        return "未知原因"

    def undo_move(self):
        """撤销上一步移动
        
        Returns:
            bool: 是否成功撤销
        """
        if not self.move_history:
            return False

        # 获取上一步移动记录
        # 注意：现在历史记录包含额外的甲/胄吃子信息和刺兑子信息
        if len(self.move_history[-1]) == 8:  # 包含甲/胄吃子信息和刺兑子信息
            piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces, ci_captured_pieces = self.move_history.pop()
        elif len(self.move_history[-1]) == 7:  # 包含甲/胄吃子信息
            piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces = self.move_history.pop()
            ci_captured_pieces = []
        else:  # 旧格式（不包含甲/胄吃子信息和刺兑子信息）
            piece, from_row, from_col, to_row, to_col, captured_piece = self.move_history.pop()
            jia_captured_pieces = []
            ci_captured_pieces = []

        # 将棋子移回原位置
        piece.move_to(from_row, from_col)

        # 恢复被直接吃掉的棋子
        if captured_piece:
            self.pieces.append(captured_piece)
            # 从阵亡列表中移除
            if captured_piece in self.captured_pieces[captured_piece.color]:
                self.captured_pieces[captured_piece.color].remove(captured_piece)

        # 恢复甲/胄连线吃掉的棋子
        for captured in jia_captured_pieces:
            if captured not in self.pieces:  # 避免重复添加
                self.pieces.append(captured)
                # 从阵亡列表中移除
                if captured in self.captured_pieces[captured.color]:
                    self.captured_pieces[captured.color].remove(captured)

        # 恢复刺兑子中失去的棋子
        for captured in ci_captured_pieces:
            if captured not in self.pieces:  # 避免重复添加
                self.pieces.append(captured)
                # 从阵亡列表中移除
                if captured in self.captured_pieces[captured.color]:
                    self.captured_pieces[captured.color].remove(captured)

        # 悔棋时也需要回退局面历史记录
        if self.board_position_history:
            self.board_position_history.pop()

        # 重新计算重复计数（重新统计当前局面历史）
        self.repetition_count = {}
        for board_hash in self.board_position_history:
            if board_hash in self.repetition_count:
                self.repetition_count[board_hash] += 1
            else:
                self.repetition_count[board_hash] = 1

        # 切换玩家回合
        self.player_turn = "black" if self.player_turn == "red" else "red"

        # 重置游戏状态
        self.game_over = False
        self.winner = None

        # 重置将军状态
        self.is_check = False

        # 重置当前回合开始时间
        self.current_turn_start_time = time.time()

        return True

    def update_times(self):
        """更新当前时间计数，但不切换回合"""
        if not self.game_over:
            current_time = time.time()
            elapsed = current_time - self.current_turn_start_time
            # 更新总游戏时长
            self.total_time = max(0.0, current_time - self.start_time)

            # 这里我们只计算临时的当前回合时间，不更新累计时间
            # 因为累计时间只在移动棋子时更新
            if self.player_turn == "red":
                return self.red_time + elapsed, self.black_time
            else:
                return self.red_time, self.black_time + elapsed
        return self.red_time, self.black_time

    def should_show_check_animation(self):
        """检查是否应该显示将军动画"""
        # 修复逻辑：如果游戏已经结束，不应该显示将军动画
        if not self.is_check or self.game_over:
            return False

        # 检查动画是否在有效时间内
        current_time = time.time()
        elapsed = current_time - self.check_animation_time
        return elapsed < self.check_animation_duration

    def get_checked_king_position(self):
        """获取被将军的将/帅的位置"""
        # 修复逻辑：如果游戏已经结束，不应该再显示将军动画
        if not self.is_check or self.game_over:
            return None

        # 确定被将军的一方 - 根据player_turn确定当前受威胁方
        # player_turn表示当前轮到谁走，因此被将军的是当前回合的对手
        checked_color = "red" if self.player_turn == "red" else "black"  # 修正：被将军的是当前玩家，而不是对手
        for piece in self.pieces:
            if isinstance(piece, King) and piece.color == checked_color:
                return piece.row, piece.col

        return None

    def calculate_possible_moves(self, row, col):
        """计算指定位置棋子的所有可能移动
        
        Args:
            row (int): 棋子的行坐标
            col (int): 棋子的列坐标
            
        Returns:
            tuple: (可移动位置列表, 可吃子位置列表)
        """
        piece = self.get_piece_at(row, col)
        if not piece:
            return [], []

        moves, capturable = GameRules.calculate_possible_moves(self.pieces, piece)

        # 过滤掉会导致被将军的移动（送将）和被尉照面限制的移动
        safe_moves = self.filter_safe_moves_and_regular_moves(moves, piece)

        # 过滤掉会导致被将军的吃子移动和被尉照面限制的吃子移动
        safe_capturable = self.filter_safe_moves(capturable, piece)

        return safe_moves, safe_capturable

    def is_piece_facing_restricted(self, piece):
        """检查棋子是否被尉照面限制移动"""
        for wei_piece, facing_target in self.facing_pairs:
            if facing_target == piece and piece != wei_piece:
                return True
        return False

    def filter_safe_moves(self, capturable, piece):
        safe_capturable = []
        for to_row, to_col in capturable:
            # 检查是否被尉照面限制
            if self.is_piece_facing_restricted(piece):
                continue  # 被尉照面限制的棋子不能移动
            if not GameRules.would_be_in_check_after_move(self.pieces, piece, to_row, to_col):
                # 如果目标位置有盾，且不是己方的盾，则不能吃（盾不可被吃）
                target_piece = self.get_piece_at(to_row, to_col)
                if target_piece and isinstance(target_piece, Dun) and target_piece.color != piece.color:
                    continue  # 不能吃盾
                safe_capturable.append((to_row, to_col))
        return safe_capturable

    def filter_safe_moves_and_regular_moves(self, moves, piece):
        """过滤安全的移动（包括非吃子移动）"""
        safe_moves = []
        for to_row, to_col in moves:
            # 检查是否被尉照面限制
            if self.is_piece_facing_restricted(piece):
                continue  # 被尉照面限制的棋子不能移动
            if not GameRules.would_be_in_check_after_move(self.pieces, piece, to_row, to_col):
                safe_moves.append((to_row, to_col))
        return safe_moves

    def get_winner_text(self):
        """获取胜利方文本
        
        Returns:
            str: 胜利信息文本
        """
        if not self.game_over or not self.winner:
            return ""

        return f"{'红方' if self.winner == 'red' else '黑方'}胜利!"

    def get_pawn_count(self, color):
        """获取指定颜色在局的兵/卒数量
        
        Args:
            color (str): 棋子颜色，"red" 或 "black"
            
        Returns:
            int: 兵/卒数量
        """
        count = 0
        for piece in self.pieces:
            if isinstance(piece, Pawn) and piece.color == color:
                count += 1
        return count

    def can_perform_pawn_resurrection(self, color, position):
        """检查是否可以执行兵/卒复活
        
        Args:
            color (str): 棋子颜色，"red" 或 "black"
            position (tuple): 位置(row, col)
            
        Returns:
            bool: 是否可以执行复活
        """
        # 检查复活机制是否启用
        if not game_config.get_setting("pawn_resurrection_enabled", True):
            return False

        row, col = position

        # 检查目标位置是否为空
        target_piece = self.get_piece_at(row, col)
        if target_piece is not None:
            return False

        # 检查是否是兵/卒的初始位置
        # 黑方兵初始位置：第4行的 (4,0), (4,2), (4,4), (4,6), (4,8), (4,10), (4,12)
        # 红方兵初始位置：第8行的 (8,0), (8,2), (8,4), (8,6), (8,8), (8,10), (8,12)
        if color == "red":
            # 红方兵的初始位置行是8，列必须是偶数
            if row != 8 or col % 2 != 0:
                return False
        else:  # black
            # 黑方兵的初始位置行是4，列必须是偶数
            if row != 4 or col % 2 != 0:
                return False

        # 检查该玩家在局的兵/卒数量是否小于7
        alive_pawns = self.get_pawn_count(color)
        if alive_pawns >= 7:
            return False

        # 检查是否有阵亡的兵/卒可以复活
        has_dead_pawn = any(isinstance(piece, Pawn) and piece.color == color for piece in self.captured_pieces[color])
        if not has_dead_pawn and alive_pawns >= 6:  # 如果没有阵亡兵卒，且在局数量已经>=6，则无法复活
            return False

        return True

    def perform_pawn_resurrection(self, color, position):
        """执行兵/卒复活
        
        Args:
            color (str): 棋子颜色，"red" 或 "black"
            position (tuple): 位置(row, col)
            
        Returns:
            bool: 是否成功执行复活
        """
        row, col = position

        # 检查是否可以执行复活
        if not self.can_perform_pawn_resurrection(color, position):
            return False

        # 从阵亡棋子列表中找到一个兵/卒并移除
        # 从阵亡列表中移除一个兵/卒
        for i, captured_piece in enumerate(self.captured_pieces[color][:]):  # 使用副本遍历
            if isinstance(captured_piece, Pawn) and captured_piece.color == color:
                # 从阵亡棋子列表中移除这个兵/卒
                self.captured_pieces[color].remove(captured_piece)
                break

        # 如果没有找到阵亡的兵/卒，但当前在局兵/卒数量不足7个，仍然可以复活
        # 创建新的兵/卒并添加到棋盘
        new_pawn = Pawn(color, row, col)
        self.pieces.append(new_pawn)

        return True

    def get_available_promotion_pieces(self, color):
        """获取可升变的阵亡棋子列表
        
        Args:
            color (str): 棋子颜色
            
        Returns:
            list: 可升变的阵亡棋子列表
        """
        # 过滤掉兵/卒，因为升变是将兵/卒变成其他阵亡棋子
        return [piece for piece in self.captured_pieces[color] if not isinstance(piece, Pawn)]

    def reset(self):
        """重置游戏状态"""
        # 重新创建棋子，以便根据当前设置使用正确的布局
        self.__init__()

        step_counter.reset()

    def perform_promotion(self, selected_piece_index):
        """执行兵卒升变
        
        Args:
            selected_piece_index (int): 选中的阵亡棋子索引
            
        Returns:
            bool: 是否成功执行升变
        """
        if not self.needs_promotion or self.promotion_pawn is None:
            return False

        if selected_piece_index < 0 or selected_piece_index >= len(self.available_promotion_pieces):
            return False

        # 获取选中的阵亡棋子
        selected_piece = self.available_promotion_pieces[selected_piece_index]

        # 从阵亡列表中移除选中的棋子
        self.captured_pieces[selected_piece.color].remove(selected_piece)

        # 用选中的棋子替换兵/卒（保持位置不变）
        pawn_row, pawn_col = self.promotion_pawn.row, self.promotion_pawn.col
        self.pieces.remove(self.promotion_pawn)

        # 创建新的棋子（复制选中棋子的类型，但保持原位置和颜色）
        new_piece = selected_piece.__class__(self.promotion_pawn.color, pawn_row, pawn_col)
        new_piece.name = selected_piece.name  # 保持棋子名称
        self.pieces.append(new_piece)

        # 重置升变标志
        self.needs_promotion = False
        self.promotion_pawn = None
        self.available_promotion_pieces = []

        # 标记刚刚完成升变
        self.just_completed_promotion = True

        return True

    def is_checkmate(self):
        """检查当前玩家是否被将死
        
        Returns:
            bool: 当前玩家是否被将死
        """
        return GameRules.is_checkmate(self.pieces, self.player_turn)

    def get_resurrection_positions(self):
        """获取可以执行兵/卒复活的位置列表
        
        Returns:
            dict: 包含红方和黑方可复活位置的字典
        """
        resurrection_positions = {"red": [], "black": []}

        # 检查复活机制是否启用
        if not game_config.get_setting("pawn_resurrection_enabled", True):
            return resurrection_positions

        # 检查红方兵初始行（第8行）
        for col in range(13):
            row = 8
            if self.can_perform_pawn_resurrection("red", (row, col)):
                resurrection_positions["red"].append((row, col))

        # 检查黑方兵初始行（第4行）
        for col in range(13):
            row = 4
            if self.can_perform_pawn_resurrection("black", (row, col)):
                resurrection_positions["black"].append((row, col))

        return resurrection_positions

    def export_position(self):
        """导出当前棋局位置
        Returns:
            str: FEN格式的棋盘表示
        """
        if GameRules.traditional_mode:
            # 传统中国象棋的FEN映射和处理
            piece_fen_map = {
                '汗': 'k',  # 黑方将/帅
                '車': 'r', '馬': 'n', '象': 'b', '士': 'a', '砲': 'c', '卒': 'p',
                '汉': 'K',  # 红方将/帅
                '俥': 'R', '傌': 'N', '相': 'B', '仕': 'A', '炮': 'C', '兵': 'P',
            }

            # 创建9x10的传统象棋棋盘
            board = [['.' for _ in range(9)] for _ in range(10)]

            # 只将传统象棋棋子放置到棋盘上
            for piece in self.pieces:
                # 只处理传统象棋的棋子
                if piece.name in ['汗',
                                  '車', '馬', '象', '士', '砲', '卒',
                                  '汉',
                                  '俥', '傌', '相', '仕', '炮', '兵']:
                    if piece.row < 10 and piece.col < 9:  # 确保在9x10棋盘范围内
                        board[piece.row][piece.col] = piece.name

            # 将棋盘转换为FEN格式（传统象棋格式）
            fen_parts = []
            for row in board:
                empty_count = 0
                fen_row = ""
                for cell in row:
                    if cell == '.':
                        empty_count += 1
                    else:
                        if empty_count > 0:
                            fen_row += str(empty_count)
                            empty_count = 0
                        fen_char = piece_fen_map.get(cell, '?')
                        fen_row += fen_char
                if empty_count > 0:
                    fen_row += str(empty_count)
                fen_parts.append(fen_row)

            fen_code = '/'.join(fen_parts)

        else:
            # 原有的匈汉象棋处理逻辑
            piece_fen_map = {
                # 黑方棋子（小写）
                '汗': 'k',  # 黑方将/帅
                '車': 'r', '馬': 'n', '象': 'b', '士': 'a', '砲': 'c', '卒': 'p',
                '衛': 'w', '䠶': 's', '礌': 'l', '胄': 'j', '刺': 'i', '盾': 'u', '廵': 'x',
                # 红方棋子（大写）
                '汉': 'K',  # 红方将/帅
                '俥': 'R', '傌': 'N', '相': 'B', '仕': 'A', '炮': 'C', '兵': 'P',
                '尉': 'W', '射': 'S', '檑': 'L', '甲': 'J', '巡': 'X',
            }

            # 创建棋盘表示 - 使用13x13的棋盘
            board = [['.' for _ in range(13)] for _ in range(13)]

            # 将棋子放置到棋盘上
            for piece in self.pieces:
                board[piece.row][piece.col] = piece.name

            # 将棋盘转换为FEN格式
            fen_parts = []
            for row in board:
                empty_count = 0
                fen_row = ""
                for cell in row:
                    if cell == '.':
                        empty_count += 1
                    else:
                        if empty_count > 0:
                            fen_row += str(empty_count)
                            empty_count = 0
                        fen_char = piece_fen_map.get(cell, '?')
                        fen_row += fen_char
                if empty_count > 0:
                    fen_row += str(empty_count)
                fen_parts.append(fen_row)

            fen_code = '/'.join(fen_parts)

        # 添加当前玩家信息
        current_player = 'r' if self.player_turn == 'red' else 'b'

        # 组合完整的FEN字符串
        fen_string = f"{fen_code} {current_player}"

        return fen_string

    def import_position(self, fen_string):
        """导入棋局位置

        Args:
            fen_string (str): FEN格式的棋盘表示
            traditional_mode (bool): 是否为传统象棋模式

        Returns:
            bool: 是否成功导入
        """
        try:
            # 解析FEN字符串
            parts = fen_string.strip().split()
            if len(parts) < 2:
                print("FEN格式错误：缺少必要参数")
                return False

            fen_board = parts[0]
            fen_player = parts[1]

            if GameRules.traditional_mode:
                # 传统中国象棋的FEN映射
                fen_piece_map = {
                    # 小写为黑方，大写为红方
                    'k': ('black', '汗'),  # 黑方将/帅
                    'r': ('black', '車'), 'n': ('black', '馬'), 'b': ('black', '象'),
                    'a': ('black', '士'), 'c': ('black', '砲'), 'p': ('black', '卒'),
                    'K': ('red', '漢'),  # 红方将/帅
                    'R': ('red', '俥'), 'N': ('red', '傌'), 'B': ('red', '相'),
                    'A': ('red', '仕'), 'C': ('red', '炮'), 'P': ('red', '兵'),
                }

                # 从FEN解析棋盘（传统象棋：9列x10行）
                rows = fen_board.split('/')
                if len(rows) != 10:  # 传统象棋有10行
                    print("FEN格式错误：传统象棋棋盘行数应为10")
                    return False

                # 清空当前棋子
                self.pieces.clear()

                # 逐行解析传统象棋
                for row_idx, row_str in enumerate(rows):
                    col_idx = 0
                    i = 0
                    while i < len(row_str):
                        if row_str[i].isdigit():
                            # 处理数字（空位）
                            num_str = ""
                            while i < len(row_str) and row_str[i].isdigit():
                                num_str += row_str[i]
                                i += 1
                            empty_spaces = int(num_str)
                            col_idx += empty_spaces
                        else:
                            # 字符表示棋子
                            if row_str[i] in fen_piece_map:
                                color, name = fen_piece_map[row_str[i]]
                                piece_class = tools.get_piece_class_by_name(name)
                                if piece_class:
                                    piece = piece_class(color, row_idx, col_idx)
                                    self.pieces.append(piece)
                            col_idx += 1
                            i += 1
                    if col_idx != 9:  # 传统象棋有9列
                        print(f"传统象棋FEN格式错误：第{row_idx}行列数不正确")
                        return False
            else:
                # 原有的匈汉象棋处理逻辑
                fen_piece_map = {
                    # 小写为黑方，大写为红方
                    'k': ('black', '汗'),  # 黑方将/帅
                    'r': ('black', '車'), 'n': ('black', '馬'), 'b': ('black', '象'),
                    'a': ('black', '士'), 'c': ('black', '砲'), 'p': ('black', '卒'),
                    'w': ('black', '衛'), 's': ('black', '䠶'), 'l': ('black', '礌'),
                    'j': ('black', '胄'), 'i': ('black', '伺'), 'u': ('black', '碷'),
                    'x': ('black', '廵'),
                    # 红方棋子（大写）
                    'K': ('red', '漢'),  # 红方将/帅
                    'R': ('red', '俥'), 'N': ('red', '傌'), 'B': ('red', '相'),
                    'A': ('red', '仕'), 'C': ('red', '炮'), 'P': ('red', '兵'),
                    'W': ('red', '尉'), 'S': ('red', '射'), 'L': ('red', '檑'),
                    'J': ('red', '甲'), 'I': ('red', '刺'), 'U': ('red', '楯'),
                    'X': ('red', '巡'),
                }

                # 从FEN解析棋盘（匈汉象棋：13x13）
                rows = fen_board.split('/')
                if len(rows) != 13:
                    print("FEN格式错误：棋盘行数不正确")
                    return False

                # 清空当前棋子
                self.pieces.clear()

                # 逐行解析匈汉象棋
                for row_idx, row_str in enumerate(rows):
                    col_idx = 0
                    i = 0
                    while i < len(row_str):
                        if row_str[i].isdigit():
                            # 提取整个数字（可能有多位）
                            num_str = ""
                            while i < len(row_str) and row_str[i].isdigit():
                                num_str += row_str[i]
                                i += 1
                            empty_spaces = int(num_str)
                            col_idx += empty_spaces
                        else:
                            # 字符表示棋子
                            if row_str[i] in fen_piece_map:
                                color, name = fen_piece_map[row_str[i]]
                                # 根据颜色和名称创建对应的棋子类
                                piece_class = tools.get_piece_class_by_name(name)
                                if piece_class:
                                    piece = piece_class(color, row_idx, col_idx)
                                    self.pieces.append(piece)
                            col_idx += 1
                            i += 1
                    if col_idx != 13:
                        print(f"FEN格式错误：第{row_idx}行列数不正确，实际为{col_idx}，期望为13")
                        return False

            # 设置当前玩家
            self.player_turn = 'red' if fen_player.lower() in ['r', 'red'] else 'black'

            # 重置游戏状态
            self.game_over = False
            self.winner = None
            self.is_check = False

            # 重置将军状态
            self.check_animation_time = 0

            # 重置历史记录
            self.move_history = []
            self.captured_pieces = {"red": [], "black": []}

            # 重置升变相关
            self.needs_promotion = False
            self.promotion_pawn = None
            self.available_promotion_pieces = []
            self.just_completed_promotion = False

            # 重置局面历史
            self.board_position_history = []
            self.repetition_count = {}

            # 重置步数计数器
            self.moves_count = 0

            step_counter.reset()

            print("棋局导入成功")
            return True
        except Exception as e:
            print(f"导入棋局失败: {str(e)}")
            return False
