"""
测试真正的绝杀场景
"""
from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import King, Ju, Pawn


def test_real_checkmate():
    """测试真正的绝杀场景"""
    print("=== 测试真正的绝杀场景 ===")
    
    # 创建一个真正的绝杀场景
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置红方将（在九宫格角落，更难逃脱）
    red_king = King("red", 11, 6)  # 将放在九宫格右下角
    game_state.pieces.append(red_king)
    
    # 放置黑方车将军（从上方将军）
    black_ju = Ju("black", 10, 6)  # 黑车在将的正上方
    game_state.pieces.append(black_ju)
    
    # 封堵所有可能的逃跑路线
    # 1. 封堵(11, 5) - 左侧
    blocker1 = Pawn("red", 11, 5)  # 红兵在将的左侧
    game_state.pieces.append(blocker1)
    
    # 2. 封堵(11, 7) - 右侧
    blocker2 = Pawn("red", 11, 7)  # 红兵在将的右侧
    game_state.pieces.append(blocker2)
    
    # 3. 封堵(10, 5) - 左上
    blocker3 = Pawn("black", 10, 5)  # 黑兵在将的左上方（敌方棋子，但会阻止将移动）
    game_state.pieces.append(blocker3)
    
    # 4. 封堵(10, 7) - 右上
    blocker4 = Pawn("black", 10, 7)  # 黑兵在将的右上方（敌方棋子，但会阻止将移动）
    game_state.pieces.append(blocker4)
    
    # 5. 封堵(9, 6) - 正上方
    blocker5 = Pawn("black", 9, 6)  # 黑兵在将的正上方（敌方棋子，但会阻止将移动）
    game_state.pieces.append(blocker5)
    
    print(f"棋子位置:")
    for piece in game_state.pieces:
        print(f"  {piece.name} at ({piece.row}, {piece.col}), color: {piece.color}")
    
    # 设置当前玩家
    game_state.player_turn = "black"  # 当前是黑方回合（刚走完）
    
    # 检查红方是否被将军
    is_red_in_check = GameRules.is_check(game_state.pieces, "red")
    print(f"红方是否被将军: {is_red_in_check}")
    
    # 检查红方是否被将死
    is_red_in_checkmate = GameRules.is_checkmate(game_state.pieces, "red")
    print(f"红方是否被将死: {is_red_in_checkmate}")
    
    # 手动检查红方将的所有可能移动
    print("\n详细检查红方将的所有可能移动...")
    red_king = None
    for piece in game_state.pieces:
        if isinstance(piece, King) and piece.color == "red":
            red_king = piece
            break
    
    if red_king:
        print(f"红方将的位置: ({red_king.row}, {red_king.col})")
        
        # 检查所有可能的移动（九宫格内）
        possible_moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                new_row, new_col = red_king.row + dr, red_king.col + dc
                # 检查是否在九宫格内（红方九宫：行9-11，列5-7）
                if 9 <= new_row <= 11 and 5 <= new_col <= 7:
                    # 检查目标位置是否有己方棋子
                    target_piece = GameRules.get_piece_at(game_state.pieces, new_row, new_col)
                    if target_piece is None or target_piece.color != "red":
                        # 检查移动是否合法
                        if GameRules.is_valid_move(game_state.pieces, red_king, red_king.row, red_king.col, new_row, new_col):
                            possible_moves.append((new_row, new_col))
        
        print(f"红方将的可能移动: {possible_moves}")
        
        # 详细检查这些移动是否能解除将军
        safe_moves = []
        for move in possible_moves:
            new_row, new_col = move
            print(f"  检查移动到 ({new_row}, {new_col}):")
            
            # 创建一个临时的棋盘状态，模拟移动
            temp_pieces = []
            for p in game_state.pieces:
                if p == red_king:
                    # 创建一个临时的将，模拟移动到新位置
                    temp_king = King(p.color, new_row, new_col)
                    temp_king.name = p.name
                    temp_pieces.append(temp_king)
                else:
                    temp_pieces.append(p)
            
            # 检查移动后是否还会被将军
            would_be_in_check = GameRules.is_check(temp_pieces, "red")
            print(f"    移动后是否被将军: {would_be_in_check}")
            
            if not would_be_in_check:
                safe_moves.append((new_row, new_col))
                print(f"    -> 这是一个安全移动!")
            else:
                print(f"    -> 不是安全移动，仍被将军")
        
        print(f"能解除将军的安全移动: {safe_moves}")
        
        if not safe_moves:
            print("✓ 确实没有安全移动，红方被将死")
        else:
            print(f"✗ 还有 {len(safe_moves)} 个安全移动，红方未被将死")
    
    # 检查游戏状态的将军位置方法
    print("\n检查游戏状态的将军位置方法:")
    game_state.is_check = is_red_in_check
    king_pos = game_state.get_checked_king_position()
    print(f"被将军的王的位置: {king_pos}")
    
    if king_pos:
        row, col = king_pos
        piece_at_pos = game_state.get_piece_at(row, col)
        print(f"位置({row}, {col})处的棋子: {piece_at_pos.name if piece_at_pos else 'None'}, 颜色: {piece_at_pos.color if piece_at_pos else 'N/A'}")
        
        if piece_at_pos and isinstance(piece_at_pos, King) and piece_at_pos.color == "red":
            print("✓ 正确返回了被将军的红方王的位置")
        else:
            print("✗ 错误：没有正确返回被将军的王的位置")
    
    # 测试游戏结束逻辑
    if is_red_in_checkmate:
        print("\n测试游戏结束逻辑:")
        game_state.game_over = True
        game_state.winner = "black"  # 黑方获胜
        print(f"游戏结束: {game_state.game_over}, 获胜方: {game_state.winner}")
    else:
        print("\n未达到绝杀状态，继续游戏...")


if __name__ == "__main__":
    test_real_checkmate()