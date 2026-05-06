"""
命令调用者 - 管理命令的执行、撤销和重做
"""
from typing import List, Optional
from desktop.core.commands import Command


class CommandInvoker:
    """
    命令调用者
    负责执行命令并维护命令历史，支持撤销/重做
    """
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        
        # 命令历史栈
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        
        # 统计信息
        self.total_commands_executed = 0
        self.total_commands_undone = 0
        self.total_commands_redone = 0
    
    def execute_command(self, command: Command) -> bool:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            
        Returns:
            bool: 是否执行成功
        """
        if not command:
            return False
        
        # 执行新命令时，清空重做栈
        if self._redo_stack:
            self._redo_stack.clear()
        
        # 执行命令
        success = command.execute()
        
        if success:
            # 将命令加入撤销栈
            self._undo_stack.append(command)
            
            # 限制历史记录大小
            if len(self._undo_stack) > self.max_history:
                self._undo_stack.pop(0)
            
            self.total_commands_executed += 1
        
        return success
    
    def undo(self) -> bool:
        """
        撤销上一个命令
        
        Returns:
            bool: 是否撤销成功
        """
        if not self._undo_stack:
            return False
        
        # 获取最后一个命令
        command = self._undo_stack.pop()
        
        # 撤销命令
        success = command.undo()
        
        if success:
            # 将命令加入重做栈
            self._redo_stack.append(command)
            self.total_commands_undone += 1
        else:
            # 如果撤销失败，重新放回撤销栈
            self._undo_stack.append(command)
        
        return success
    
    def redo(self) -> bool:
        """
        重做上一个被撤销的命令
        
        Returns:
            bool: 是否重做成功
        """
        if not self._redo_stack:
            return False
        
        # 获取最后一个被撤销的命令
        command = self._redo_stack.pop()
        
        # 重做命令
        success = command.redo()
        
        if success:
            # 将命令重新加入撤销栈
            self._undo_stack.append(command)
            self.total_commands_redone += 1
        else:
            # 如果重做失败，重新放回重做栈
            self._redo_stack.append(command)
        
        return success
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return len(self._redo_stack) > 0
    
    def clear_history(self):
        """清空命令历史"""
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    def get_undo_stack_size(self) -> int:
        """获取撤销栈大小"""
        return len(self._undo_stack)
    
    def get_redo_stack_size(self) -> int:
        """获取重做栈大小"""
        return len(self._redo_stack)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'undo_stack_size': len(self._undo_stack),
            'redo_stack_size': len(self._redo_stack),
            'total_executed': self.total_commands_executed,
            'total_undone': self.total_commands_undone,
            'total_redone': self.total_commands_redone
        }
    
    def __repr__(self):
        return (f"CommandInvoker("
                f"undo={len(self._undo_stack)}, "
                f"redo={len(self._redo_stack)}, "
                f"executed={self.total_commands_executed})")

