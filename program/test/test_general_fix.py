"""
匈汉象棋将军/绝杀UI显示修复验证测试
此文件用于验证将军/绝杀显示逻辑的修复
"""
from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import King, Ju, Pawn, Shi, Xiang
from program.ui.chess_board import ChessBoard
import pygame

def test_check_position_logic():
    """测试将军位置逻辑 - 验证被将军方王的坐标获取"""
    print("\n=== 测试将军位置逻辑 ===")
    
    # 创建将军场景：黑方走子让红方被将军
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置红方将
    red_king = King("red", 9, 6)  # 红将在九宫内
    game_state.pieces.append(red_king)
    
    # 放置黑方车将军
    black_ju = Ju("black", 6, 6)  # 黑车在红将正上方将军
    game_state.pieces.append(black_ju)
    
    # 设置当前是黑方回合（黑方刚走完，现在检查红方是否被将军）
    game_state.player_turn = "black"
    
    # 检查红方是否被将军
    is_red_in_check = GameRules.is_check(game_state.pieces, "red")
    print(f"   红方是否被将军: {is_red_in_check}")
    
    # 设置游戏状态
    game_state.is_check = is_red_in_check
    
    # 获取被将军王的位置
    king_pos = game_state.get_checked_king_position()
    print(f"   被将军王的位置: {king_pos}")
    
    # 验证位置是否正确（应该是红将的位置）
    if king_pos == (9, 6):
        print("   ✓ 将军位置获取正确（红方王的位置）")
    else:
        print(f"   ✗ 将军位置获取错误，期望(9, 6)，实际{king_pos}")
    
    # 验证获取的是被将军方的王，而不是走子方的王
    king_at_pos = game_state.get_piece_at(king_pos[0], king_pos[1]) if king_pos else None
    if king_at_pos and king_at_pos.color == "red":
        print("   ✓ 正确获取了被将军方（红方）的王")
    else:
        print("   ✗ 错误获取了非被将军方的王")


def test_checkmate_display_logic():
    """测试绝杀显示逻辑 - 验证绝杀时显示'绝杀'而非'将军'"""
    print("\n=== 测试绝杀显示逻辑 ===")
    
    # 创建一个简单的绝杀场景：黑方将被将死
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置黑方将（被将死的一方）
    black_king = King("black", 3, 6)  # 黑将在九宫内
    game_state.pieces.append(black_king)
    
    # 放置红方车将军
    red_ju = Ju("red", 2, 6)  # 红车紧贴黑将，形成将军
    game_state.pieces.append(red_ju)
    
    # 完全封堵黑将的所有逃跑路线
    # 封堵上方（1,6）- 已被红车将军占据
    # 封堵下方（4,6）- 用黑方自己的棋子
    black_pawn1 = Pawn("black", 4, 6)
    # 封堵左方（3,5）
    black_pawn2 = Pawn("black", 3, 5)  
    # 封堵右方（3,7）
    black_pawn3 = Pawn("black", 3, 7)
    # 封堵左上（2,5）- 红方棋子
    red_shi1 = Shi("red", 2, 5)
    # 封堵右上（2,7）- 红方棋子
    red_shi2 = Shi("red", 2, 7)
    # 封堵左下（4,5）
    black_pawn4 = Pawn("black", 4, 5)
    # 封堵右下（4,7）
    black_pawn5 = Pawn("black", 4, 7)
    
    game_state.pieces.extend([black_pawn1, black_pawn2, black_pawn3, red_shi1, red_shi2, black_pawn4, black_pawn5])
    
    # 设置当前是红方回合（红方刚走完，现在检查黑方是否被将死）
    game_state.player_turn = "red"
    
    # 检查黑方是否被将军和将死
    is_black_in_check = GameRules.is_check(game_state.pieces, "black")
    is_black_in_checkmate = GameRules.is_checkmate(game_state.pieces, "black")
    print(f"   黑方是否被将军: {is_black_in_check}")
    print(f"   黑方是否被将死: {is_black_in_checkmate}")
    
    # 设置游戏状态
    game_state.is_check = is_black_in_check
    
    # 检查GameState的is_checkmate方法（检查当前player_turn是否被将死）
    # 这里是红方回合，所以应该检查红方是否被将死（不应该被将死）
    is_current_player_checkmate = game_state.is_checkmate()
    print(f"   当前玩家（红方）是否被将死: {is_current_player_checkmate}")
    
    # 检查黑方是否被将死（对手）
    is_opponent_checkmate = GameRules.is_checkmate(game_state.pieces, "black")
    print(f"   对手（黑方）是否被将死: {is_opponent_checkmate}")
    
    # 验证绝杀检测逻辑
    if is_black_in_check and is_black_in_checkmate:
        print("   ✓ 绝杀检测逻辑正确")
    else:
        print(f"   ✗ 绝杀检测逻辑错误 - 黑方被将军: {is_black_in_check}, 黑方被将死: {is_black_in_checkmate}")


def test_chess_board_display():
    """测试棋盘UI显示逻辑"""
    print("\n=== 测试棋盘UI显示逻辑 ===")
    
    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    
    # 创建棋盘
    chess_board = ChessBoard(600, 600, 50, 50)
    
    # 创建一个将军场景
    game_state_check = GameState()
    game_state_check.pieces.clear()
    
    red_king = King("red", 9, 6)
    black_ju = Ju("black", 6, 6)
    game_state_check.pieces = [red_king, black_ju]
    game_state_check.player_turn = "black"
    game_state_check.is_check = True
    game_state_check.game_over = False  # 游戏未结束
    
    # 创建一个绝杀场景
    game_state_checkmate = GameState()
    game_state_checkmate.pieces.clear()
    
    black_king = King("black", 3, 6)
    red_ju = Ju("red", 2, 6)  # 紧贴将军
    black_pawn1 = Pawn("black", 4, 6)
    black_pawn2 = Pawn("black", 3, 5)
    black_pawn3 = Pawn("black", 3, 7)
    red_shi1 = Shi("red", 2, 5)
    red_shi2 = Shi("red", 2, 7)
    
    game_state_checkmate.pieces = [black_king, red_ju, black_pawn1, black_pawn2, black_pawn3, red_shi1, red_shi2]
    game_state_checkmate.player_turn = "red"
    game_state_checkmate.is_check = True
    game_state_checkmate.game_over = False  # 游戏未结束但被将死
    
    # 检查绝杀状态
    is_checkmate = GameRules.is_checkmate(game_state_checkmate.pieces, "black")
    print(f"   绝杀场景中黑方是否被将死: {is_checkmate}")
    
    # 获取被将军王的位置
    check_king_pos = game_state_check.get_checked_king_position()
    checkmate_king_pos = game_state_checkmate.get_checked_king_position()
    
    print(f"   将军场景被将军王位置: {check_king_pos}")
    print(f"   绝杀场景被将军王位置: {checkmate_king_pos}")
    
    # 验证位置获取
    if check_king_pos == (9, 6) and checkmate_king_pos == (3, 6):
        print("   ✓ 将军和绝杀场景中王的位置获取正确")
    else:
        print("   ✗ 王的位置获取错误")


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("匈汉象棋将军/绝杀UI显示修复验证测试")
    print("="*60)
    
    test_check_position_logic()
    test_checkmate_display_logic()
    test_chess_board_display()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()