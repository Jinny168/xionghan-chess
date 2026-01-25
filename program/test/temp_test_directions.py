from program.core.game_rules import GameRules
from program.core.chess_pieces import She, Pawn

print("测试不同方向的夹逼规则...")

# 测试左上方向 (-1,-1) 移动：从(5,5)到(3,3)
print("\n测试左上方向移动 (5,5) -> (3,3):")
pieces = []
she = She('red', 5, 5)
pieces.append(she)
# 夹逼棋子应该在路径点(4,4)的相邻位置：(4,3)和(3,4)
pawn1 = Pawn('black', 4, 3)
pawn2 = Pawn('black', 3, 4)
pieces.append(pawn1)
pieces.append(pawn2)

result = GameRules.is_valid_she_move(pieces, 5, 5, 3, 3)
print(f'射从(5,5)到(3,3)的移动: {result} (应为False，因夹逼)')

# 测试右上方向 (-1,1) 移动：从(5,5)到(3,7)
print("\n测试右上方向移动 (5,5) -> (3,7):")
pieces = []
she = She('red', 5, 5)
pieces.append(she)
# 移动方向(-1,1)，step_row=-1, step_col=1
# 路径点(4,6)的夹逼方向：(0,1)向上 和 (-1,0)向左
# 所以夹逼点应为(4,7)和(3,6)
pawn1 = Pawn('black', 4, 7)
pawn2 = Pawn('black', 3, 6)
pieces.append(pawn1)
pieces.append(pawn2)

result = GameRules.is_valid_she_move(pieces, 5, 5, 3, 7)
print(f'射从(5,5)到(3,7)的移动: {result} (应为False，因夹逼)')

# 测试左下方向 (1,-1) 移动：从(3,7)到(5,5)
print("\n测试左下方向移动 (3,7) -> (5,5):")
pieces = []
she = She('red', 3, 7)
pieces.append(she)
# 移动方向(1,-1)，step_row=1, step_col=-1
# 路径点(4,6)的夹逼方向：(0,-1)向下 和 (1,0)向右
# 所以夹逼点应为(4,5)和(5,6)
pawn1 = Pawn('black', 4, 5)
pawn2 = Pawn('black', 5, 6)
pieces.append(pawn1)
pieces.append(pawn2)

result = GameRules.is_valid_she_move(pieces, 3, 7, 5, 5)
print(f'射从(3,7)到(5,5)的移动: {result} (应为False，因夹逼)')

# 测试无夹逼情况
print("\n测试无夹逼情况:")
pieces = []
she = She('red', 0, 0)
pieces.append(she)
pawn1 = Pawn('black', 1, 3)  # 不在夹逼位置
pawn2 = Pawn('black', 3, 1)  # 不在夹逼位置
pieces.append(pawn1)
pieces.append(pawn2)

result = GameRules.is_valid_she_move(pieces, 0, 0, 2, 2)
print(f'射从(0,0)到(2,2)的移动: {result} (应为True，无夹逼)')