"""
移动验证器 - 负责棋子移动的合法性验证
从GameState中提取的移动验证逻辑
"""
from typing import List, Tuple, Optional, Dict
from desktop.core.chess_pieces import ChessPiece, King, Dun
from desktop.core.game_rules import GameRules


class MoveValidator:
    """
    移动验证器
    封装所有与移动合法性相关的验证逻辑
    """
    
    def __init__(self, pieces: List[ChessPiece], player_turn: str):
        """
        初始化移动验证器
        
        Args:
            pieces: 当前棋盘上的所有棋子
            player_turn: 当前回合玩家
        """
        self.pieces = pieces
        self.player_turn = player_turn
        
        # 性能优化：缓存尉照面对，避免重复计算
        self._facing_pairs_cache: Optional[List[Tuple[ChessPiece, ChessPiece]]] = None
    
    def is_valid_move(self, piece: ChessPiece, from_row: int, from_col: int, 
                     to_row: int, to_col: int) -> bool:
        """
        检查移动是否合法（综合验证）
        
        Args:
            piece: 要移动的棋子
            from_row, from_col: 起始位置
            to_row, to_col: 目标位置
            
        Returns:
            bool: 移动是否合法
        """
        # 防御性检查：确保piece不为None
        if piece is None:
            return False
        
        # 1. 基础规则验证
        if not GameRules.is_valid_move(self.pieces, piece, from_row, from_col, to_row, to_col):
            return False
        
        # 2. 不能送将（移动后不能被将军）
        if GameRules.would_be_in_check_after_move(self.pieces, piece, to_row, to_col):
            return False
        
        # 3. 尉照面限制检查
        if self._is_facing_restricted(piece, to_row, to_col):
            return False
        
        # 4. 盾不可被吃检查
        if self._is_shield_capture(piece, to_row, to_col):
            return False
        
        return True
    
    def _is_facing_restricted(self, piece: ChessPiece, to_row: int, to_col: int) -> bool:
        """
        检查是否被尉照面限制
        
        Args:
            piece: 要移动的棋子
            to_row, to_col: 目标位置
            
        Returns:
            bool: 是否被限制
        """
        # 查找尉照面对
        facing_pairs = self._get_facing_pairs()
        
        for wei_piece, facing_target in facing_pairs:
            if facing_target == piece and piece != wei_piece:
                return True
        
        return False
    
    def _is_shield_capture(self, piece: ChessPiece, to_row: int, to_col: int) -> bool:
        """
        检查是否尝试吃掉盾（盾不可被吃）
        
        Args:
            piece: 攻击方棋子
            to_row, to_col: 目标位置
            
        Returns:
            bool: 是否尝试吃盾
        """
        # 防御性检查：确保piece不为None
        if piece is None:
            return False
        
        target_piece = self._get_piece_at(to_row, to_col)
        return (target_piece and 
                isinstance(target_piece, Dun) and 
                target_piece.color != piece.color)
    
    def _get_facing_pairs(self) -> List[Tuple[ChessPiece, ChessPiece]]:
        """
        获取所有尉照面对（带缓存优化）
        
        Returns:
            List of (wei_piece, facing_target) tuples
        """
        # 如果已有缓存，直接返回
        if self._facing_pairs_cache is not None:
            return self._facing_pairs_cache
        
        from desktop.core.chess_pieces import Wei
        
        pairs = []
        for piece in self.pieces:
            # 防御性检查：确保piece不为None
            if piece is None:
                continue
            if isinstance(piece, Wei) and GameRules.is_facing_enemy(piece, self.pieces):
                facing_target = GameRules.get_facing_piece(piece, self.pieces)
                if facing_target:
                    pairs.append((piece, facing_target))
        
        # 缓存结果
        self._facing_pairs_cache = pairs
        return pairs
    
    def invalidate_cache(self):
        """
        清除缓存（当棋盘状态改变时调用）
        """
        self._facing_pairs_cache = None
    
    def get_safe_moves(self, piece: ChessPiece) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        获取棋子的安全移动位置（过滤掉会导致被将军或违反规则的移动）
        性能优化：使用局部变量减少属性访问，预计算常用值
        
        Args:
            piece: 棋子
            
        Returns:
            tuple: (可移动位置列表, 可吃子位置列表)
        """
        # 获取所有可能的移动
        moves, capturable = GameRules.calculate_possible_moves(self.pieces, piece)
        
        # 预计算尉照面对（只计算一次，供两次过滤使用）
        facing_pairs = self._get_facing_pairs()
        
        # 过滤安全的普通移动
        safe_moves = self._filter_safe_positions_optimized(moves, piece, facing_pairs)
        
        # 过滤安全的吃子移动
        safe_capturable = self._filter_safe_positions_optimized(capturable, piece, facing_pairs)
        
        return safe_moves, safe_capturable
    
    def _filter_safe_positions_optimized(self, positions: List[Tuple[int, int]], 
                                         piece: ChessPiece,
                                         facing_pairs: List[Tuple[ChessPiece, ChessPiece]]) -> List[Tuple[int, int]]:
        """
        过滤出安全的位置（优化版本，减少重复计算）
        
        Args:
            positions: 候选位置列表
            piece: 棋子
            facing_pairs: 预计算的尉照面对
            
        Returns:
            安全位置列表
        """
        safe_positions = []
        
        # 构建尉照面限制集合，O(1)查找
        restricted_targets = set()
        for wei_piece, facing_target in facing_pairs:
            if facing_target == piece and piece != wei_piece:
                # 记录被限制的棋子ID
                restricted_targets.add(id(piece))
        
        is_restricted = id(piece) in restricted_targets
        
        for to_row, to_col in positions:
            # 检查尉照面限制（使用预计算结果）
            if is_restricted:
                continue
            
            # 检查是否会送将
            if GameRules.would_be_in_check_after_move(self.pieces, piece, to_row, to_col):
                continue
            
            # 检查是否尝试吃盾（内联检查，避免函数调用开销）
            target_piece = GameRules.get_piece_at(self.pieces, to_row, to_col)
            if target_piece and isinstance(target_piece, Dun) and target_piece.color != piece.color:
                continue
            
            safe_positions.append((to_row, to_col))
        
        return safe_positions
    
    def _filter_safe_positions(self, positions: List[Tuple[int, int]], 
                               piece: ChessPiece) -> List[Tuple[int, int]]:
        """
        过滤出安全的位置（旧版本，保留向后兼容）
        
        Args:
            positions: 候选位置列表
            piece: 棋子
            
        Returns:
            安全位置列表
        """
        safe_positions = []
        
        for to_row, to_col in positions:
            # 检查尉照面限制
            if self._is_facing_restricted(piece, to_row, to_col):
                continue
            
            # 检查是否会送将
            if GameRules.would_be_in_check_after_move(self.pieces, piece, to_row, to_col):
                continue
            
            # 检查是否尝试吃盾
            if self._is_shield_capture(piece, to_row, to_col):
                continue
            
            safe_positions.append((to_row, to_col))
        
        return safe_positions
    
    def would_cause_game_over(self, piece: ChessPiece, to_row: int, to_col: int) -> bool:
        """
        检查移动是否会导致游戏结束（吃掉对方将/帅）
        
        Args:
            piece: 移动的棋子
            to_row, to_col: 目标位置
            
        Returns:
            bool: 是否会导致游戏结束
        """
        target_piece = self._get_piece_at(to_row, to_col)
        return target_piece and isinstance(target_piece, King)
    
    def _get_piece_at(self, row: int, col: int) -> Optional[ChessPiece]:
        """
        获取指定位置的棋子
        
        Args:
            row, col: 位置坐标
            
        Returns:
            棋子对象或None
        """
        return GameRules.get_piece_at(self.pieces, row, col)
    
    def is_own_piece(self, piece: ChessPiece) -> bool:
        """
        检查是否是己方棋子
        
        Args:
            piece: 棋子
            
        Returns:
            bool: 是否是己方棋子
        """
        return piece is not None and piece.color == self.player_turn

