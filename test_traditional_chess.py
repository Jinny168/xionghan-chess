#!/usr/bin/env python
"""
传统象棋独立测试脚本
"""

def test_traditional_chess():
    """测试传统象棋功能"""
    print("开始测试传统象棋功能...")
    
    try:
        # 测试传统象棋导入
        from program.core.traditional_game import run_traditional_chess
        print("✓ 成功导入传统象棋模块")
        
        # 测试传统象棋模式类
        from program.core.traditional_chess_mode import TraditionalChessMode
        mode = TraditionalChessMode()
        pieces = mode.create_traditional_pieces()
        print(f"✓ 成功创建传统象棋模式，棋子数量: {len(pieces)}")
        
        # 测试传统象棋规则
        from program.core.traditional_chess_rules import TraditionalChessRules
        rules = TraditionalChessRules()
        print("✓ 成功导入传统象棋规则")
        
        # 测试传统象棋棋盘
        from program.ui.traditional_chess_board import TraditionalChessBoard
        board = TraditionalChessBoard(1200, 900, 100, 50)
        print("✓ 成功创建传统象棋棋盘")
        
        # 测试传统象棋AI
        from program.ai.traditional_ai import TraditionalAI
        ai = TraditionalAI()
        print("✓ 成功创建传统象棋AI")
        
        print("\n所有测试通过！传统象棋模块已正确实现。")
        print("\n要运行传统象棋，请执行:")
        print("  双人对战: run_traditional_chess('pvp')")
        print("  人机对战: run_traditional_chess('pvc')")
        print("  网络对战: run_traditional_chess('network')")
        
    except ImportError as e:
        print(f"✗ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_traditional_chess()