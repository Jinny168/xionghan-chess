#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终验证测试：检查对局过程中棋谱记录及对局结束时导出棋局的完整逻辑
"""

import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from program.core.game_state import GameState
from program.controllers.game_io_controller import GameIOController


def simulate_game_with_moves(game_state):
    """模拟一个带有实际走子的游戏过程"""
    from program.core.game_rules import GameRules
    
    print("开始模拟带实际走子的游戏过程...")
    
    # 执行几个实际的移动
    moves_made = 0
    
    # 红方移动一个兵
    for piece in game_state.pieces:
        if piece.name == "兵" and piece.color == "red" and piece.row == 8:
            # 找到一个可移动的位置
            target_row, target_col = piece.row - 1, piece.col  # 兵向前移动
            
            if GameRules.is_valid_move(game_state.pieces, piece, piece.row, piece.col, target_row, target_col):
                if not GameRules.would_be_in_check_after_move(game_state.pieces, piece, target_row, target_col):
                    original_pos = (piece.row, piece.col)
                    success = game_state.move_piece(piece.row, piece.col, target_row, target_col)
                    if success:
                        moves_made += 1
                        print(f"红方兵从 ({original_pos[0]}, {original_pos[1]}) 移动到 ({target_row}, {target_col})")
                        print(f"移动后玩家: {game_state.player_turn}")
                        if moves_made >= 1:
                            break
    
    # 黑方移动一个卒
    if moves_made > 0:
        for piece in game_state.pieces:
            if piece.name == "卒" and piece.color == "black" and piece.row == 4:
                # 找到一个可移动的位置
                target_row, target_col = piece.row + 1, piece.col  # 卒向前移动
                
                if GameRules.is_valid_move(game_state.pieces, piece, piece.row, piece.col, target_row, target_col):
                    if not GameRules.would_be_in_check_after_move(game_state.pieces, piece, target_row, target_col):
                        original_pos = (piece.row, piece.col)
                        success = game_state.move_piece(piece.row, piece.col, target_row, target_col)
                        if success:
                            moves_made += 1
                            print(f"黑方卒从 ({original_pos[0]}, {original_pos[1]}) 移动到 ({target_row}, {target_col})")
                            print(f"移动后玩家: {game_state.player_turn}")
                            if moves_made >= 2:
                                break
    
    print(f"总共执行了 {moves_made} 步移动")
    print(f"当前历史记录长度: {len(game_state.move_history)}")
    
    return moves_made


def test_export_logic_from_game_end():
    """测试从游戏结束时的导出逻辑"""
    print("=" * 60)
    print("测试对局过程中棋谱记录及对局结束时导出棋局的完整逻辑")
    print("=" * 60)
    
    # 创建游戏状态
    game_state = GameState()
    
    print(f"初始玩家: {game_state.player_turn}")
    print(f"初始棋子数量: {len(game_state.pieces)}")
    print(f"初始历史记录长度: {len(game_state.move_history)}")
    
    # 模拟游戏过程，产生一些走子记录
    moves_made = simulate_game_with_moves(game_state)
    
    print(f"模拟移动后:")
    print(f"  当前玩家: {game_state.player_turn}")
    print(f"  历史记录长度: {len(game_state.move_history)}")
    print(f"  棋子数量: {len(game_state.pieces)}")
    
    # 检查历史记录是否正确保存
    if len(game_state.move_history) > 0:
        print(f"  ✓ 棋谱历史记录已保存，包含 {len(game_state.move_history)} 条记录")
        
        # 检查第一条记录的格式
        first_record = game_state.move_history[0]
        print(f"  第一条记录格式: {len(first_record)} 个元素")
        if len(first_record) >= 6:
            piece, from_row, from_col, to_row, to_col, captured = first_record[:6]
            print(f"    棋子: {piece.name} ({piece.color}) 从 ({from_row}, {from_col}) 到 ({to_row}, {to_col})")
    else:
        print("  ✗ 没有棋谱历史记录")
    
    # 模拟游戏结束
    print(f"\n模拟游戏结束...")
    game_state.game_over = True
    game_state.winner = "red"  # 红方获胜
    print(f"游戏结束状态: {game_state.game_over}, 胜者: {game_state.winner}")
    
    # 测试导出功能（模拟游戏结束弹窗中的导出按钮点击）
    print(f"\n--- 测试导出功能 ---")
    
    # 使用临时文件进行测试
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False, encoding='utf-8') as tmp_file:
        temp_filename = tmp_file.name
    
    try:
        # 创建控制器并执行导出
        controller = GameIOController()
        export_success = controller.export_game(game_state, temp_filename)
        
        print(f"导出结果: {export_success}")
        
        if export_success:
            # 验证导出的文件
            if os.path.exists(temp_filename):
                file_size = os.path.getsize(temp_filename)
                print(f"✓ 文件已创建，大小: {file_size} 字节")
                
                # 读取并验证文件内容
                with open(temp_filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content.strip():
                    print("✓ 文件内容非空")
                    
                    # 尝试解析JSON
                    try:
                        game_data = json.loads(content)
                        print("✓ 文件内容为有效的JSON格式")
                        
                        # 验证关键字段
                        expected_fields = ['position', 'move_history', 'captured_pieces', 
                                         'player_turn', 'game_over', 'winner', 'total_time']
                        
                        print(f"解析出的字段: {list(game_data.keys())}")
                        
                        all_fields_present = True
                        for field in expected_fields:
                            if field in game_data:
                                print(f"  ✓ {field}: 存在")
                                if field == 'move_history':
                                    print(f"    历史记录数量: {len(game_data[field])}")
                                    if len(game_data[field]) > 0:
                                        print(f"    示例记录: {game_data[field][0][:2]}...")  # 显示前两个元素
                                elif field == 'game_over':
                                    print(f"    游戏结束状态: {game_data[field]}")
                                elif field == 'winner':
                                    print(f"    胜者: {game_data[field]}")
                            else:
                                print(f"  ✗ {field}: 缺失")
                                all_fields_present = False
                        
                        if all_fields_present:
                            print("✓ 所有关键字段都已正确导出")
                        else:
                            print("✗ 部分关键字段缺失")
                            
                    except json.JSONDecodeError as e:
                        print(f"✗ 文件内容不是有效的JSON格式: {e}")
                        print(f"文件内容预览: {content[:200]}...")
                else:
                    print("✗ 文件内容为空")
            else:
                print("✗ 文件未创建")
        else:
            print("✗ 导出失败")
            
        # 测试导入功能（验证导出的数据可以被正确导入）
        print(f"\n--- 测试导入功能 ---")
        
        if export_success:
            # 创建新的游戏状态用于导入测试
            new_game_state = GameState()
            print(f"导入前状态 - 玩家: {new_game_state.player_turn}, 历史记录: {len(new_game_state.move_history)}")
            
            import_success = controller.import_game(new_game_state, temp_filename)
            print(f"导入结果: {import_success}")
            
            if import_success:
                print(f"导入后状态 - 玩家: {new_game_state.player_turn}")
                print(f"导入后历史记录长度: {len(new_game_state.move_history)}")
                print(f"导入后游戏结束状态: {new_game_state.game_over}")
                print(f"导入后胜者: {new_game_state.winner}")
                
                # 验证导入的数据是否与原始数据一致
                original_history_len = len(game_state.move_history)
                imported_history_len = len(new_game_state.move_history)
                
                if imported_history_len == original_history_len:
                    print("✓ 历史记录长度匹配")
                else:
                    print(f"✗ 历史记录长度不匹配: 原始 {original_history_len}, 导入 {imported_history_len}")
                
                if new_game_state.winner == game_state.winner:
                    print("✓ 胜者信息匹配")
                else:
                    print(f"✗ 胜者信息不匹配: 原始 {game_state.winner}, 导入 {new_game_state.winner}")
                    
                if new_game_state.game_over == game_state.game_over:
                    print("✓ 游戏结束状态匹配")
                else:
                    print(f"✗ 游戏结束状态不匹配: 原始 {game_state.game_over}, 导入 {new_game_state.game_over}")
            else:
                print("✗ 导入失败")
        else:
            print("由于导出失败，跳过导入测试")
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print(f"\n已清理临时文件: {temp_filename}")
    
    print(f"\n{'='*60}")
    print("最终验证测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_export_logic_from_game_end()