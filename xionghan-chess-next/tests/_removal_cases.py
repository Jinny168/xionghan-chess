"""移除集合指纹的**局面构造器**（纯函数，测试与生成脚本共用）。

## 为什么不用随机种子

随机生成的局面有两个毛病，都会让门禁慢慢烂掉：

1. **不可 review**：`seed=20260807` 生成的 200 个局面，没人能一眼看出"覆盖了什么"；
2. **覆盖是碰出来的**：第一版正是如此 —— 200 例随机稀疏局面里，「可吃格」摘要**全是空串**，
   门禁绿着，但三连吃子的语义怎么改它都不会动。

所以这里改成**按维度显式枚举**：case id 由维度拼成（`F1/L4/d2/L2/D1/vP`），局面由 id
**唯一**重建。加一个维度 → id 集合变化 → 门禁立刻红，逼你显式更新基线，而不是悄悄漏覆盖。

## 轴只取 3 个（h / ↘ / ↗）

竖线由横线**转置棋盘**得到，而转置是合法双射、「落点在第 1/2/3 格」在转置下不变 ——
所以竖线与横线结构同构，再测一遍是重复覆盖。3 轴 78 例；若将来要 4 轴是 104 例，
仍在上限内，但那一路要在 `GENERATOR_VERSION` 注释里写明"此轴为冗余覆盖"。

## 为什么不做全交叉（别把组合加回来）

`_three_line_mover(piece, move)` 是**硬闸门**：不满足就直接 `return False`，
`_three_line_removals` 根本不会被调用。所以「位移 > 1」与「线多长」在结构上无关 ——
F2（位移族）固定线长 = 3 是**充分**的，不是省预算。全交叉那 620 条里绝大多数已被
同一处闸门覆盖，加了只会让基线变大、变慢、变难读。
"""

from __future__ import annotations

from xionghan_chess.core.model import Color, Piece, PieceType

# 构造规则变了（加族 / 改坐标算法）就 +1；**规则语义变化不要动它**，
# 语义变化由基线里的 `ruleVersion` 与摘要内容体现。两者管的不是一件事。
GENERATOR_VERSION = 1

# 只这三个轴：h=横、d1=↘、d2=↗。竖线是 h 的转置，同构（见模块 docstring）。
AXES: dict[str, tuple[int, int]] = {"h": (0, 1), "d1": (1, 1), "d2": (1, -1)}

# 落点固定在 (5,4)：红兵从下方纵向进入，`distance_to_enemy_territory = 5-6+1` 这种口径下
# 落点必须是「快速行军最远能到的那一行」，所以 5 与 D 无关地恒成立（mover 起点 = 5+D 行，
# 上限 = (5+D)-6+1 = D，正好够）。三条轴各取 L=5 / slot=3 时最远伸到 row 3 / col 2，不出界。
LANDING = (5, 4)
# 双方王放在远处，避免照面/将军把着法表压空 —— 那会让很多例子的 perft1 变成 0，
# 而"0 着法"是另一种退化，不是我们想钉的东西。
RED_KING = (12, 0)
BLACK_KING = (0, 12)


def _piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def _cell(offset: int, axis: str) -> tuple[int, int]:
    """沿 `axis` 从**落点**走 `offset` 步（可为负）后的格子。

    参数是「相对落点的偏移」，不是「线内下标」—— 线内下标到偏移的换算是
    `index - (slot - 1)`，由 `_line_board` 负责。第一版把两者混了：`index == 0`
    恒等于落点，于是 slot=2/3 的"落点"其实落在别的格子上，9 例里只 3 例命中。
    """
    dr, dc = AXES[axis]
    return LANDING[0] + dr * offset, LANDING[1] + dc * offset


def _line_board(
    *,
    axis: str,
    length: int,
    slot: int,
    victim: PieceType,
    mover_offset: int,
) -> list[tuple[PieceType, Color, int, int]]:
    """一条线上摆 `length` 枚子，落点位于线内第 `slot` 格（1-based）。

    **走法方向与"线"的方向是两件事**，必须解耦：兵只能前进 / （过河后）横走，永远不能斜走；
    而三连看的是**落点所在的那条线**，线可以斜着铺。所以移动兵一律摆在落点**正下方**
    `mover_offset` 格处，纵向走上来；线则沿 `axis` 铺开。

    （第一版把两者混在一起 —— 让兵沿斜线走进落点，结果所有着法都非法，78 例里三连命中 0，
    门禁照样绿。这类"构造错误伪装成覆盖"只有真的数一遍 cases 才能发现。）

    线内角色：落点留空（移动兵从线外走进来），紧邻一格放另一枚我方，再下一格放敌方受害子，
    其余格补我方 —— 于是线长 3 时窗口「两我一敌」必然成立，线长 4/5 时每个 3 格窗口
    两端都挨着子（「恰好三子」判据生效）。

    **补位的我方一律用车，不用兵**：三连要求"至少一枚我方是兵"，而全盘唯一的兵是移动兵 ——
    这样每一例只演示它 id 里标注的那条性质。第一版补的都是兵，结果"四子线"的用例里，
    补位兵自己走进落点又凑出一条三连，id 写 `L4` 却照样命中，基线可读性直接毁掉。
    """
    landing_index = slot - 1
    others = [index for index in range(length) if index != landing_index]
    ally_index = others[0] if landing_index == 0 else landing_index - 1
    enemy_index = others[1] if landing_index == 0 else (landing_index + 1 if landing_index + 1 < length else others[0])
    if enemy_index == ally_index:
        enemy_index = others[-1]

    pieces: list[tuple[PieceType, Color, int, int]] = []
    for index in range(length):
        row, col = _cell(index - landing_index, axis)
        if index == landing_index:
            continue  # 落点由移动兵占，但它从线外走进来，见下面的 `_mover()`
        if index == enemy_index:
            pieces.append((victim, Color.BLACK, row, col))
        else:
            pieces.append((PieceType.ROOK, Color.RED, row, col))
    return pieces


def _mover(mover_offset: int) -> tuple[PieceType, Color, int, int]:
    """移动兵：落点正下方 `mover_offset` 行，纵向走上来（红兵向前 = 行号减小）。"""
    return (PieceType.PAWN, Color.RED, LANDING[0] + mover_offset, LANDING[1])


def _with_kings(pieces: list[tuple[PieceType, Color, int, int]], *, black_king_in_line: bool = False):
    board = list(pieces)
    board.append((PieceType.KING, Color.RED, *RED_KING))
    if not black_king_in_line:
        board.append((PieceType.KING, Color.BLACK, *BLACK_KING))
    return board


def _case(case_id: str, pieces, *, three_line: bool = True, turn: Color = Color.RED) -> dict:
    return {
        "id": case_id,
        "profileId": "web",
        "options": {"pawn_three_line_capture": three_line},
        "turn": turn.value,
        "pieces": [[color.value, kind.value, row, col] for kind, color, row, col in pieces],
    }


def build_cases() -> list[dict]:
    """确定性枚举，返回的 id 集合就是基线的键集合。"""
    cases: list[dict] = []

    # F0 开关：同一局面关掉三连 → 什么都不该结算（钉住"关掉即不走"这条路径）。
    for axis in AXES:
        cases.append(
            _case(
                f"F0/L3/A{axis}/S1/D1/vP/off",
                _with_kings(
                    [_mover(1), *_line_board(axis=axis, length=3, slot=1, victim=PieceType.ADVISOR, mover_offset=1)]
                ),
                three_line=False,
            )
        )

    # F1 线长：3 触发 / 4、5 不触发；落点在线内第 1/2/3 格。
    for length in (3, 4, 5):
        for axis in AXES:
            for slot in (1, 2, 3):
                if slot > length:
                    continue
                cases.append(
                    _case(
                        f"F1/L{length}/A{axis}/S{slot}/D1/vP",
                        _with_kings(
                            [
                                _mover(1),
                                *_line_board(
                                    axis=axis, length=length, slot=slot, victim=PieceType.ADVISOR, mover_offset=1
                                ),
                            ]
                        ),
                    )
                )

    # F2 位移：2/3/5/7 格快速行军，落点线恰好三子 → 不结算（硬闸门，与线长无关）。
    for steps in (2, 3, 5, 7):
        for axis in AXES:
            cases.append(
                _case(
                    f"F2/L3/A{axis}/S1/D{steps}/vP",
                    _with_kings(
                        [
                            _mover(steps),
                            *_line_board(
                                axis=axis, length=3, slot=1, victim=PieceType.ADVISOR, mover_offset=steps
                            ),
                        ]
                    ),
                )
            )

    # F3 王：受害子是王 → 不结算（线长 3 与 4 都测，4 用来证明这是两层独立过滤）。
    for length in (3, 4):
        for axis in AXES:
            for slot in (1, 2, 3):
                if slot > length:
                    continue
                cases.append(
                    _case(
                        f"F3/L{length}/A{axis}/S{slot}/D1/vK",
                        _with_kings(
                            [
                                _mover(1),
                                *_line_board(
                                    axis=axis, length=length, slot=slot, victim=PieceType.KING, mover_offset=1
                                ),
                            ],
                            black_king_in_line=True,
                        ),
                    )
                )

    # F4 并行：主轴恰好三子（该吃），另一条轴 4 子（不该吃）→ 必须只结算主轴那一条。
    for length in (3, 4):
        for axis in AXES:
            for slot in (1, 2, 3):
                if slot > length:
                    continue
                main = _line_board(axis=axis, length=3, slot=slot, victim=PieceType.ADVISOR, mover_offset=1)
                secondary_axis = next(name for name in AXES if name != axis)
                secondary = _line_board(
                    axis=secondary_axis, length=length, slot=slot, victim=PieceType.ROOK, mover_offset=1
                )
                merged = [_mover(1)]
                for entry in [*main, *secondary]:
                    if entry not in merged:
                        merged.append(entry)
                cases.append(_case(f"F4/L{length}/A{axis}/S{slot}/D1/P2", _with_kings(merged)))

    return cases
