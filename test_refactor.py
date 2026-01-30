#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试重构后的游戏功能
"""
import sys
import os
sys.path.append(os.getcwd())

def test_imports():
    """测试导入功能"""
    print("Testing imports...")
    try:
        from program.game import ChessGame
        print("✓ ChessGame imported successfully")
        
        from program.ui.game_screen import GameScreen
        print("✓ GameScreen imported successfully")
        
        from program.ui.chess_board import ChessBoard
        print("✓ ChessBoard imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_functionality():
    """测试基本功能"""
    print("\nTesting basic functionality...")
    try:
        from program.game import ChessGame
        from program.ui.game_screen import GameScreen
        from program.ui.chess_board import ChessBoard
        
        # 测试创建游戏实例
        game = ChessGame()
        print("✓ ChessGame instance created successfully")
        
        # 测试GameScreen是否具有所需的方法
        assert hasattr(game.game_screen, 'handle_event'), "GameScreen should have handle_event method"
        assert hasattr(game.game_screen, 'handle_resize'), "GameScreen should have handle_resize method"
        assert hasattr(game.game_screen, 'handle_undo'), "GameScreen should have handle_undo method"
        print("✓ GameScreen has required methods")
        
        # 测试ChessBoard是否具有所需的方法
        assert hasattr(game.game_screen.board, 'handle_click'), "ChessBoard should have handle_click method"
        print("✓ ChessBoard has required methods")
        
        # 测试没有input_handler引用
        import program.game
        import inspect
        game_source = inspect.getsource(program.game)
        if 'input_handler' in game_source:
            print("✗ Still contains input_handler references")
            return False
        else:
            print("✓ No input_handler references in game module")
        
        return True
    except Exception as e:
        print(f"✗ Functionality test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting refactoring tests...\n")
    
    success = True
    success &= test_imports()
    success &= test_functionality()
    
    print("\n" + "="*50)
    if success:
        print("✓ All tests passed! Refactoring completed successfully.")
    else:
        print("✗ Some tests failed!")
    print("="*50)