"""工具函数模块，包含导入导出棋局和复盘等功能"""
import json
import pygame
import copy
from tkinter import filedialog

from program.ui.button import Button


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


class ReplayController:
    """复盘控制器，用于控制棋局复盘过程"""
    
    def __init__(self, game_state):
        """初始化复盘控制器
        
        Args:
            game_state: 游戏状态对象
        """
        self.game_state = game_state
        self.original_state = None  # 原始游戏状态的备份
        self.current_step = 0  # 当前复盘步骤
        self.max_steps = 0  # 总步骤数
        self.replay_history = []  # 复盘历史记录
        self.is_replay_mode = False  # 是否处于复盘模式
        
    def start_replay(self):
        """开始复盘模式"""
        # 保存当前游戏状态
        self.backup_game_state()
        self.is_replay_mode = True
        
        # 构建复盘历史记录
        self.build_replay_history()
        
        # 重置到初始状态
        self.go_to_beginning()
    
    def backup_game_state(self):
        """备份当前游戏状态"""
        # 创建当前游戏状态的深拷贝
        self.original_state = copy.deepcopy({
            'pieces': [(p.__class__, p.color, p.name, p.row, p.col) for p in self.game_state.pieces],
            'player_turn': self.game_state.player_turn,
            'game_over': self.game_state.game_over,
            'winner': self.game_state.winner,
            'is_check': self.game_state.is_check,
            'move_history': self.game_state.move_history[:],  # 复制历史记录
            'captured_pieces': {
                'red': [copy.copy(piece) for piece in self.game_state.captured_pieces['red']],
                'black': [copy.copy(piece) for piece in self.game_state.captured_pieces['black']]
            },
            'board_position_history': self.game_state.board_position_history[:],
            'repetition_count': self.game_state.repetition_count.copy(),
            'moves_count': self.game_state.moves_count,
            'red_time': self.game_state.red_time,
            'black_time': self.game_state.black_time,
            'total_time': self.game_state.total_time
        })
    
    def restore_original_state(self):
        """恢复原始游戏状态"""
        if self.original_state:
            # 从备份恢复游戏状态
            from program.core.chess_pieces import (
                King, Ju, Ma, Xiang, Shi, Pao, Pawn, Wei, She, Lei, Jia, Ci, Dun, Xun
            )
            
            # 重建棋子
            self.game_state.pieces.clear()
            for piece_class, color, name, row, col in self.original_state['pieces']:
                piece = piece_class(color, row, col)
                piece.name = name  # 设置棋子名称
                self.game_state.pieces.append(piece)
            
            # 恢复其他状态
            self.game_state.player_turn = self.original_state['player_turn']
            self.game_state.game_over = self.original_state['game_over']
            self.game_state.winner = self.original_state['winner']
            self.game_state.is_check = self.original_state['is_check']
            self.game_state.move_history = self.original_state['move_history'][:]
            self.game_state.captured_pieces = {
                'red': [p for p in self.original_state['captured_pieces']['red']],
                'black': [p for p in self.original_state['captured_pieces']['black']]
            }
            self.game_state.board_position_history = self.original_state['board_position_history'][:]
            self.game_state.repetition_count = self.original_state['repetition_count'].copy()
            self.game_state.moves_count = self.original_state['moves_count']
            self.game_state.red_time = self.original_state['red_time']
            self.game_state.black_time = self.original_state['black_time']
            self.game_state.total_time = self.original_state['total_time']
            
            self.is_replay_mode = False
    
    def build_replay_history(self):
        """构建复盘历史记录"""
        # 清空当前复盘历史
        self.replay_history = []
        
        # 备份当前状态
        temp_state = copy.deepcopy(self.game_state)
        
        # 重置到初始状态
        self.reset_to_initial()
        
        # 逐步重演所有移动
        for i, move_record in enumerate(temp_state.move_history):
            # 执行移动并保存状态快照
            self.apply_move_record(move_record)
            # 保存当前状态快照
            self.replay_history.append(copy.deepcopy({
                'pieces': [(p.__class__, p.color, p.name, p.row, p.col) for p in self.game_state.pieces],
                'player_turn': self.game_state.player_turn,
                'move_index': i
            }))
        
        # 恢复原始状态
        self.restore_state_from_backup(temp_state)
        
        self.max_steps = len(self.replay_history)
        self.current_step = self.max_steps  # 设置为最后一步
    
    def reset_to_initial(self):
        """重置到初始状态"""
        # 重新初始化棋子
        from program.core.chess_pieces import create_initial_pieces
        self.game_state.pieces = create_initial_pieces()
        self.game_state.player_turn = "red"
        self.game_state.game_over = False
        self.game_state.winner = None
        self.game_state.is_check = False
        self.game_state.move_history = []
        self.game_state.captured_pieces = {"red": [], "black": []}
        self.game_state.board_position_history = []
        self.game_state.repetition_count = {}
        self.game_state.moves_count = 0
    
    def restore_state_from_backup(self, backup_state):
        """从备份状态恢复"""
        self.game_state.pieces = copy.deepcopy(backup_state.pieces)
        self.game_state.player_turn = backup_state.player_turn
        self.game_state.game_over = backup_state.game_over
        self.game_state.winner = backup_state.winner
        self.game_state.is_check = backup_state.is_check
        self.game_state.move_history = backup_state.move_history[:]
        self.game_state.captured_pieces = {
            'red': [copy.copy(piece) for piece in backup_state.captured_pieces['red']],
            'black': [copy.copy(piece) for piece in backup_state.captured_pieces['black']]
        }
        self.game_state.board_position_history = backup_state.board_position_history[:]
        self.game_state.repetition_count = backup_state.repetition_count.copy()
        self.game_state.moves_count = backup_state.moves_count
        self.game_state.red_time = backup_state.red_time
        self.game_state.black_time = backup_state.black_time
        self.game_state.total_time = backup_state.total_time
    
    def apply_move_record(self, move_record):
        """应用移动记录"""
        # 这里简化处理，实际需要根据move_record的格式进行解析和应用
        # 由于move_record包含复杂的格式，我们直接调用move_piece方法
        if len(move_record) >= 6:
            from_row, from_col, to_row, to_col = move_record[1:5]  # 获取from/to坐标
            # 从当前棋盘找到对应棋子（基于位置）
            current_piece = self.game_state.get_piece_at(from_row, from_col)
            if current_piece:
                # 执行移动
                self.game_state.move_piece(from_row, from_col, to_row, to_col)
    
    def go_to_beginning(self):
        """跳转到开局"""
        if not self.is_replay_mode:
            self.start_replay()
        
        self.reset_to_initial()
        self.current_step = 0
    
    def go_to_end(self):
        """跳转到终局"""
        if self.max_steps > 0:
            # 重置到初始状态
            self.reset_to_initial()
            
            # 逐步执行所有移动
            for i in range(self.max_steps):
                if i < len(self.replay_history):
                    self.restore_state_from_snapshot(self.replay_history[i])
            
            self.current_step = self.max_steps
    
    def restore_state_from_snapshot(self, snapshot):
        """从快照恢复状态"""
        from program.core.chess_pieces import (
            King, Ju, Ma, Xiang, Shi, Pao, Pawn, Wei, She, Lei, Jia, Ci, Dun, Xun
        )
        
        # 重建棋子
        self.game_state.pieces.clear()
        for piece_class, color, name, row, col in snapshot['pieces']:
            piece = piece_class(color, row, col)
            piece.name = name
            self.game_state.pieces.append(piece)
        
        self.game_state.player_turn = snapshot['player_turn']
    
    def go_to_previous(self):
        """上一步"""
        if self.current_step <= 0:
            return False
        
        self.current_step -= 1
        
        if self.current_step == 0:
            self.reset_to_initial()
        else:
            # 重置到初始状态，然后执行到当前步骤
            self.reset_to_initial()
            for i in range(self.current_step):
                if i < len(self.replay_history):
                    self.restore_state_from_snapshot(self.replay_history[i])
        
        return True
    
    def go_to_next(self):
        """下一步"""
        if self.current_step >= self.max_steps:
            return False
        
        self.current_step += 1
        
        if self.current_step <= len(self.replay_history):
            # 从快照恢复到指定步骤
            self.restore_state_from_snapshot(self.replay_history[self.current_step - 1])
        
        return True
    
    def get_progress_percentage(self):
        """获取复盘进度百分比"""
        if self.max_steps <= 0:
            return 0
        return int((self.current_step / self.max_steps) * 100) if self.max_steps > 0 else 0
    
    def set_progress(self, percentage):
        """设置复盘进度"""
        target_step = int((percentage / 100) * self.max_steps)
        self.jump_to_step(target_step)
    
    def jump_to_step(self, step):
        """跳转到指定步骤"""
        step = max(0, min(step, self.max_steps))
        self.current_step = step
        
        if step == 0:
            self.reset_to_initial()
        else:
            # 重置到初始状态，然后执行到目标步骤
            self.reset_to_initial()
            for i in range(step):
                if i < len(self.replay_history):
                    self.restore_state_from_snapshot(self.replay_history[i])


def enter_replay_mode(game_state):
    """进入复盘模式
    
    Args:
        game_state: 游戏状态对象
        
    Returns:
        ReplayController: 复盘控制器实例
    """
    controller = ReplayController(game_state)
    controller.start_replay()
    return controller