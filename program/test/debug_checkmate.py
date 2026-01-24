"""
调试绝杀逻辑
"""
from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import King, Ju, Pawn


def debug_checkmate():
    """调试绝杀逻辑"""
    print("=== 调试绝杀逻辑 ===")
    
    # 创建一个简单的绝杀场景
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置红方将
    red_king = King("red", 9, 6)
    game_state.pieces.append(red_king)
    
    # 放置黑方车将军
    black_ju = Ju("black", 8, 6)  # 黑车将军
    game_state.pieces.append(black_ju)
    
    # 放置其他棋子封堵红将的逃跑路线
    blocker1 = Pawn("red", 8, 5)  # 红兵在8,5位置堵住将的一个逃跑路线
    game_state.pieces.append(blocker1)
    
    blocker2 = Pawn("red", 10, 5)  # 红兵在10,5位置堵住将的另一个逃跑路线
    game_state.pieces.append(blocker2)
    
    blocker3 = Pawn("red", 10, 7)  # 红兵在10,7位置堵住将的另一个逃跑路线
    game_state.pieces.append(blocker3)
    
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
    
    # 手动检查红方的所有可能移动
    print("\n检查红方将的所有可能移动...")
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
        
        # 检查这些移动是否能解除将军
        safe_moves = []
        for move in possible_moves:
            new_row, new_col = move
            # 模拟移动，检查是否还会被将军
            # 这里需要使用虚拟移动来检查
            would_be_in_check = GameRules.would_be_in_check_after_move(game_state.pieces, red_king, new_row, new_col)
            print(f"  移动到 ({new_row}, {new_col}): 会继续被将军 = {would_be_in_check}")
            if not would_be_in_check:
                safe_moves.append((new_row, new_col))
        
        print(f"能解除将军的安全移动: {safe_moves}")
        
        if not safe_moves:
            print("✓ 确实没有安全移动，红方被将死")
        else:
            print(f"✗ 还有 {len(safe_moves)} 个安全移动，红方未被将死")
    
    # 检查是否有其他红方棋子可以移动来解除将军
    print("\n检查其他红方棋子是否可以移动解除将军...")
    red_pieces = [p for p in game_state.pieces if p.color == "red"]
    print(f"红方棋子数量: {len(red_pieces)}")
    
    safe_moves_for_any_piece = []
    for piece in red_pieces:
        if isinstance(piece, King):  # 跳过将，因为它已经在上面检查过了
            continue
        print(f"检查 {piece.name} at ({piece.row}, {piece.col}) 的可能移动...")
        
        for row in range(13):
            for col in range(13):
                if GameRules.is_valid_move(game_state.pieces, piece, piece.row, piece.col, row, col):
                    # 检查移动后是否还会被将军
                    would_be_in_check = GameRules.would_be_in_check_after_move(game_state.pieces, piece, row, col)
                    if not would_be_in_check:
                        safe_moves_for_any_piece.append((piece, (piece.row, piece.col), (row, col)))
    
    print(f"其他棋子能解除将军的移动: {len(safe_moves_for_any_piece)}")
    for move in safe_moves_for_any_piece:
        piece, from_pos, to_pos = move
        print(f"  {piece.name} from {from_pos} to {to_pos}")


if __name__ == "__main__":
    debug_checkmate()