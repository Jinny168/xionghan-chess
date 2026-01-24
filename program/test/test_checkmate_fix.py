"""
测试匈汉象棋将军/绝杀逻辑修复
"""
from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import King, Ju


def test_check_position_logic():
    """测试将军位置逻辑"""
    print("=== 测试将军位置逻辑 ===")
    
    # 创建一个简单的将军场景
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置红方将
    red_king = King("red", 9, 6)
    game_state.pieces.append(red_king)
    
    # 放置黑方车将军
    black_ju = Ju("black", 8, 6)  # 黑车将军
    game_state.pieces.append(black_ju)
    
    print(f"棋子位置:")
    for piece in game_state.pieces:
        print(f"  {piece.name} at ({piece.row}, {piece.col}), color: {piece.color}")

    # 设置游戏状态为红方回合，这样黑方的移动后会检查红方是否被将军
    game_state.player_turn = "black"
    
    # 检查红方是否被将军
    is_red_in_check = GameRules.is_check(game_state.pieces, "red")
    print(f"红方是否被将军: {is_red_in_check}")
    
    # 获取被将军的王的位置
    king_pos = game_state.get_checked_king_position()
    print(f"被将军的王的位置: {king_pos}")
    
    if king_pos:
        row, col = king_pos
        king_at_pos = game_state.get_piece_at(row, col)
        print(f"位置({row}, {col})处的棋子: {king_at_pos.name if king_at_pos else 'None'}, 颜色: {king_at_pos.color if king_at_pos else 'N/A'}")
        
        # 验证确实是红方的王
        if king_at_pos and isinstance(king_at_pos, King) and king_at_pos.color == "red":
            print("✓ 正确返回了被将军的红方王的位置")
        else:
            print("✗ 错误：没有正确返回被将军的王的位置")
    else:
        print("✗ 没有返回被将军的王的位置")


def test_checkmate_position_logic():
    """测试绝杀位置逻辑"""
    print("\n=== 测试绝杀位置逻辑 ===")
    
    # 创建一个简单的绝杀场景
    game_state2 = GameState()
    game_state2.pieces.clear()
    
    # 放置红方将
    red_king2 = King("red", 9, 6)
    game_state2.pieces.append(red_king2)
    
    # 放置黑方车将军
    black_ju2 = Ju("black", 8, 6)  # 黑车将军
    game_state2.pieces.append(black_ju2)
    
    # 放置其他棋子封堵红将的逃跑路线
    # 假设在8,5位置有一个棋子堵住将的左前方
    from program.core.chess_pieces import Pawn
    blocker1 = Pawn("red", 8, 5)  # 红兵在8,5位置堵住将的一个逃跑路线
    game_state2.pieces.append(blocker1)
    
    print(f"绝杀场景棋子位置:")
    for piece in game_state2.pieces:
        print(f"  {piece.name} at ({piece.row}, {piece.col}), color: {piece.color}")
    
    # 设置游戏状态为黑方回合，这样黑方移动后会检查红方是否被将死
    game_state2.player_turn = "black"
    
    # 检查红方是否被将军
    is_red_in_check2 = GameRules.is_check(game_state2.pieces, "red")
    print(f"   绝杀测试 - 红方是否被将军: {is_red_in_check2}")
    
    # 检查红方是否被将死
    is_red_in_checkmate2 = GameRules.is_checkmate(game_state2.pieces, "red")
    print(f"   绝杀测试 - 红方是否被将死: {is_red_in_checkmate2}")
    
    if is_red_in_checkmate2:
        # 检查被将死的王的位置
        king_pos = game_state2.get_checked_king_position()
        print(f"   被将死的王的位置: {king_pos}")
        
        if king_pos:
            row, col = king_pos
            king_at_pos = game_state2.get_piece_at(row, col)
            print(f"   位置({row}, {col})处的棋子: {king_at_pos.name if king_at_pos else 'None'}, 颜色: {king_at_pos.color if king_at_pos else 'N/A'}")
            
            # 验证确实是红方的王（被将死的一方）
            if king_at_pos and isinstance(king_at_pos, King) and king_at_pos.color == "red":
                print("   ✓ 正确返回了被将死的红方王的位置")
            else:
                print("   ✗ 错误：没有正确返回被将死的王的位置")
        else:
            print("   ✗ 没有返回被将死的王的位置")
    
    # 检查游戏结束逻辑
    print("   3. 测试游戏结束逻辑...")
    
    # 测试is_game_over函数
    game_over, winner = GameRules.is_game_over(game_state2.pieces, "black")  # 黑方刚走完
    print(f"   游戏是否结束: {game_over}, 获胜方: {winner}")
    
    print("   4. 测试游戏状态中的检查方法...")
    
    # 设置游戏状态并测试
    game_state3 = GameState()
    game_state3.pieces.clear()
    
    # 放置红将和黑车形成绝杀局面
    red_king3 = King("red", 9, 6)
    black_ju3 = Ju("black", 8, 6)
    blocker2 = Bing("red", 8, 5)
    
    game_state3.pieces = [red_king3, black_ju3, blocker2]
    game_state3.player_turn = "black"
    
    # 模拟移动并检查游戏状态
    print(f"   游戏状态 - 是否游戏结束: {game_state3.game_over}")
    print(f"   游戏状态 - 是否将军: {game_state3.is_check}")
    print(f"   游戏状态 - 是否将死: {game_state3.is_checkmate()}")
    

def test_game_flow_logic():
    """测试游戏流程逻辑"""
    print("\n=== 测试游戏流程逻辑 ===")
    
    # 创建游戏状态
    game_state = GameState()
    
    # 检查游戏初始状态
    print(f"初始游戏状态:")
    print(f"  game_over: {game_state.game_over}")
    print(f"  is_check: {game_state.is_check}")
    print(f"  is_checkmate(): {game_state.is_checkmate()}")
    print(f"  player_turn: {game_state.player_turn}")
    
    # 创建一个将军场景
    game_state.pieces.clear()
    red_king = King("red", 9, 6)
    black_ju = Ju("black", 8, 6)
    game_state.pieces = [red_king, black_ju]
    
    # 模拟黑车将军红将
    game_state.player_turn = "black"
    
    # 手动触发将军检查（模拟移动后的逻辑）
    opponent_color = "red"  # 当前玩家是black，对手是red
    if GameRules.is_check(game_state.pieces, opponent_color):
        if GameRules.is_checkmate(game_state.pieces, opponent_color):
            print("  检测到绝杀!")
            game_state.game_over = True
            game_state.winner = game_state.player_turn  # 当前玩家获胜
            game_state.is_check = False  # 游戏结束，重置将军状态
        else:
            print("  检测到将军!")
            game_state.is_check = True
            game_state.check_animation_time = 0  # 模拟时间
    
    print(f"将军/绝杀检测后状态:")
    print(f"  game_over: {game_state.game_over}")
    print(f"  is_check: {game_state.is_check}")
    print(f"  is_checkmate(): {game_state.is_checkmate()}")
    print(f"  winner: {game_state.winner}")
    

if __name__ == "__main__":
    print("开始测试匈汉象棋将军/绝杀逻辑修复...\n")
    
    test_check_position_logic()
    test_checkmate_position_logic()
    test_game_flow_logic()
    
    print("\n测试完成！")