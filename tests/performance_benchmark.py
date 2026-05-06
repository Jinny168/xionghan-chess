"""
性能基准测试框架
用于测试游戏核心组件的性能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import statistics
from typing import Callable, Dict, List
from program.core.chess_pieces import create_initial_pieces
from program.core import (
    BoardManager,
    MoveValidator,
    HistoryManager,
    CommandInvoker,
)


class BenchmarkResult:
    """基准测试结果"""
    
    def __init__(self, name: str, times: List[float]):
        self.name = name
        self.times = times
        self.min_time = min(times)
        self.max_time = max(times)
        self.avg_time = statistics.mean(times)
        self.median_time = statistics.median(times)
        self.stdev_time = statistics.stdev(times) if len(times) > 1 else 0
    
    def __str__(self):
        return (f"{self.name}:\n"
                f"  平均: {self.avg_time*1000:.3f}ms\n"
                f"  中位数: {self.median_time*1000:.3f}ms\n"
                f"  最小: {self.min_time*1000:.3f}ms\n"
                f"  最大: {self.max_time*1000:.3f}ms\n"
                f"  标准差: {self.stdev_time*1000:.3f}ms")


class PerformanceBenchmark:
    """
    性能基准测试器
    """
    
    def __init__(self, iterations: int = 1000):
        """
        初始化基准测试器
        
        Args:
            iterations: 每个测试的迭代次数
        """
        self.iterations = iterations
        self.results: Dict[str, BenchmarkResult] = {}
    
    def run_benchmark(self, name: str, func: Callable, *args, **kwargs) -> BenchmarkResult:
        """
        运行单个基准测试
        
        Args:
            name: 测试名称
            func: 要测试的函数
            *args, **kwargs: 函数参数
            
        Returns:
            BenchmarkResult: 测试结果
        """
        times = []
        
        # 预热
        for _ in range(10):
            func(*args, **kwargs)
        
        # 正式测试
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        result = BenchmarkResult(name, times)
        self.results[name] = result
        
        return result
    
    def run_all_benchmarks(self):
        """运行所有基准测试"""
        print("=" * 60)
        print("性能基准测试")
        print("=" * 60)
        
        self._benchmark_board_manager()
        self._benchmark_move_validator()
        self._benchmark_history_manager()
        self._benchmark_command_invoker()
        
        self._print_summary()
    
    def _benchmark_board_manager(self):
        """测试BoardManager性能"""
        pieces = create_initial_pieces()
        
        # 测试创建
        self.run_benchmark(
            "BoardManager创建",
            lambda: BoardManager(pieces)
        )
        
        # 测试获取棋子
        board = BoardManager(pieces)
        self.run_benchmark(
            "BoardManager.get_piece_at",
            lambda: board.get_piece_at(0, 0)
        )
        
        # 测试移动棋子
        pawn = board.get_piece_at(8, 0)
        if pawn:
            self.run_benchmark(
                "BoardManager.move_piece",
                lambda: board.move_piece(pawn, 7, 0)
            )
    
    def _benchmark_move_validator(self):
        """测试MoveValidator性能"""
        pieces = create_initial_pieces()
        validator = MoveValidator(pieces, "red")
        pawn = [p for p in pieces if hasattr(p, 'color') and p.color == "red"][0]
        
        # 测试验证移动
        self.run_benchmark(
            "MoveValidator.is_valid_move",
            lambda: validator.is_valid_move(pawn, pawn.row, pawn.col, pawn.row-1, pawn.col)
        )
        
        # 测试获取安全移动
        self.run_benchmark(
            "MoveValidator.get_safe_moves",
            lambda: validator.get_safe_moves(pawn)
        )
    
    def _benchmark_history_manager(self):
        """测试HistoryManager性能"""
        history = HistoryManager()
        from program.core.chess_pieces import Pawn
        piece = Pawn("red", 8, 0)
        
        # 测试记录走子
        self.run_benchmark(
            "HistoryManager.record_move",
            lambda: history.record_move(piece, 8, 0, 7, 0)
        )
        
        # 测试局面记录
        pieces = create_initial_pieces()
        self.run_benchmark(
            "HistoryManager.record_board_position",
            lambda: history.record_board_position(pieces)
        )
    
    def _benchmark_command_invoker(self):
        """测试CommandInvoker性能"""
        invoker = CommandInvoker()
        from unittest.mock import Mock
        
        command = Mock()
        command.execute.return_value = True
        command.undo.return_value = True
        
        # 测试执行命令
        self.run_benchmark(
            "CommandInvoker.execute_command",
            lambda: invoker.execute_command(command)
        )
        
        # 测试撤销
        invoker.execute_command(command)
        self.run_benchmark(
            "CommandInvoker.undo",
            lambda: invoker.undo()
        )
    
    def _print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试结果摘要")
        print("=" * 60)
        
        for name, result in self.results.items():
            print(f"\n{result}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
    
    def get_slowest_operations(self, n: int = 5) -> List[BenchmarkResult]:
        """
        获取最慢的操作
        
        Args:
            n: 返回数量
            
        Returns:
            最慢的操作列表
        """
        sorted_results = sorted(
            self.results.values(),
            key=lambda r: r.avg_time,
            reverse=True
        )
        return sorted_results[:n]


def run_quick_benchmark():
    """快速基准测试（用于日常开发）"""
    benchmark = PerformanceBenchmark(iterations=100)
    benchmark.run_all_benchmarks()
    
    # 显示最慢的操作
    print("\n最慢的5个操作:")
    for i, result in enumerate(benchmark.get_slowest_operations(5), 1):
        print(f"{i}. {result.name}: {result.avg_time*1000:.3f}ms")


def run_full_benchmark():
    """完整基准测试（用于发布前）"""
    benchmark = PerformanceBenchmark(iterations=10000)
    benchmark.run_all_benchmarks()
    
    # 详细报告
    print("\n最慢的10个操作:")
    for i, result in enumerate(benchmark.get_slowest_operations(10), 1):
        print(f"{i}. {result.name}: {result.avg_time*1000:.3f}ms")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        run_full_benchmark()
    else:
        run_quick_benchmark()
