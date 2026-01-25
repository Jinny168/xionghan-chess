from program.core.game_rules import GameRules
from program.core.chess_pieces import She, Pawn

# 重现问题
pieces = []
she = She('red', 5, 5)
pieces.append(she)
pawn3 = Pawn('black', 4, 3)
pawn4 = Pawn('black', 3, 4)
pieces.append(pawn3)
pieces.append(pawn4)

result = GameRules.is_valid_she_move(pieces, 5, 5, 4, 4)
print(f'射从(5,5)到(4,4)的移动: {result}')

# 检查棋盘布局
print('棋盘布局:')
for piece in pieces:
    print(f'{piece.name} at ({piece.row}, {piece.col})')