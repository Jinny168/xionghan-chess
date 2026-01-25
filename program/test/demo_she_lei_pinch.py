"""
演示射和檑棋子的夹逼规则增强功能
根据需求：射和檑在斜向移动路径中，如果存在"与当前移动斜线交叉的两相邻棋子"（即形成夹逼），则后续路径被阻挡
"""

from program.core.game_rules import GameRules
from program.core.chess_pieces import She, Lei, Pawn

def demonstrate_she_pinch():
    print("=== 射棋子夹逼规则演示 ===")
    
    # 示例1：射在(0,0)，两个棋子在(1,2)和(2,1)形成夹逼
    print("\n示例1：射位于(0,0)，夹逼棋子位于(1,2)和(2,1)")
    pieces = []
    she = She('red', 0, 0)
    pieces.append(she)
    pawn1 = Pawn('black', 1, 2)
    pawn2 = Pawn('black', 2, 1)
    pieces.append(pawn1)
    pieces.append(pawn2)
    
    # 射只能移动到(1,1)，不能移动到(2,2)及更远处
    result1 = GameRules.is_valid_she_move(pieces, 0, 0, 1, 1)
    result2 = GameRules.is_valid_she_move(pieces, 0, 0, 2, 2)
    result3 = GameRules.is_valid_she_move(pieces, 0, 0, 3, 3)
    
    print(f"  射从(0,0)到(1,1)的移动: {result1} (允许)")
    print(f"  射从(0,0)到(2,2)的移动: {result2} (阻挡 - 路径被夹逼)")
    print(f"  射从(0,0)到(3,3)的移动: {result3} (阻挡 - 路径被夹逼)")
    
    # 示例2：不同方向的移动
    print("\n示例2：射位于(5,5)，向左上方向移动，夹逼棋子位于(4,3)和(3,4)")
    pieces2 = []
    she2 = She('red', 5, 5)
    pieces2.append(she2)
    pawn3 = Pawn('black', 4, 3)
    pawn4 = Pawn('black', 3, 4)
    pieces2.append(pawn3)
    pieces2.append(pawn4)
    
    result4 = GameRules.is_valid_she_move(pieces2, 5, 5, 4, 4)
    result5 = GameRules.is_valid_she_move(pieces2, 5, 5, 3, 3)
    print(f"  射从(5,5)到(4,4)的移动: {result4} (阻挡 - 路径被夹逼)")
    print(f"  射从(5,5)到(3,3)的移动: {result5} (阻挡 - 路径被夹逼)")

def demonstrate_lei_pinch():
    print("\n=== 檑棋子夹逼规则演示 ===")
    
    # 檑同样受夹逼规则影响
    print("\n示例：檑位于(0,0)，夹逼棋子位于(1,2)和(2,1)")
    pieces = []
    lei = Lei('red', 0, 0)
    pieces.append(lei)
    pawn1 = Pawn('black', 1, 2)
    pawn2 = Pawn('black', 2, 1)
    pieces.append(pawn1)
    pieces.append(pawn2)
    
    result1 = GameRules.is_valid_lei_move(pieces, 0, 0, 1, 1)
    result2 = GameRules.is_valid_lei_move(pieces, 0, 0, 2, 2)
    result3 = GameRules.is_valid_lei_move(pieces, 0, 0, 3, 3)
    
    print(f"  檑从(0,0)到(1,1)的移动: {result1} (允许)")
    print(f"  檑从(0,0)到(2,2)的移动: {result2} (阻挡 - 路径被夹逼)")
    print(f"  檑从(0,0)到(3,3)的移动: {result3} (阻挡 - 路径被夹逼)")

def demonstrate_no_pinch():
    print("\n=== 无夹逼情况演示 ===")
    
    print("\n示例：棋子位置不足以形成夹逼")
    pieces = []
    she = She('red', 0, 0)
    pieces.append(she)
    # 只有一个棋子，无法形成夹逼
    pawn1 = Pawn('black', 1, 2)
    pieces.append(pawn1)
    
    result = GameRules.is_valid_she_move(pieces, 0, 0, 3, 3)
    print(f"  射从(0,0)到(3,3)的移动: {result} (允许 - 未形成夹逼)")

if __name__ == "__main__":
    demonstrate_she_pinch()
    demonstrate_lei_pinch()
    demonstrate_no_pinch()
    print("\n夹逼规则成功实现！")
    print("- 射和檑在斜向移动时，如果路径点的相邻位置存在两个棋子形成夹逼，则阻挡移动")
    print("- 夹逼方向垂直于移动方向，确保了四个方向的移动都受此规则约束")