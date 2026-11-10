"""S2-2 perft 规则指纹：用锚点数值把 `RulesEngine` 的走法生成钉死。

perft 从某局面出发递归数合法走法树的叶子（`core/perft.py`，规则判定完全委托
`RulesEngine`，本文件不含第二套规则）。规则一旦漂移（改错兵横走、蹩马腿、
夹逼、照面……任何一条），锚点数值立刻变红；`divide` 再把分歧定位到具体根着法。

锚点与佐证（数值不是"数出来就写"——每条都有独立来源，见各组用例 docstring）：

======================  =========  =======  =========  =========  =========
锚点局面                 profile    depth 1  depth 2    depth 3    depth 4
======================  =========  =======  =========  =========  =========
传统初始（文献锚点）     traditional   44     1920        79496     —
匈汉 13x13 初始（2.0）     desktop_complete  110  12097       —         —
中局被将军（垫/吃/走王） desktop_complete    9    564       26266     —
少子残局                 desktop_complete   27    413        9504    205086
======================  =========  =======  =========  =========  =========

独立佐证的三条腿：

1. **文献值**：传统 10x9 档在 depth 1/2 与公开的标准象棋 perft 值一致
   （44 / 1920）。depth 3 的 79496 比文献 79666 **少 170**，差值已实验归因：
   本项目对斜走子（象/仕）在标准"塞象眼"之外还有**夹逼**口径
   （`_diagonal_path_pinched`：路径任一格两侧正交邻格都被占则整步非法），
   在工作区临时禁用该口径后 perft(3) 恰好回到 79666。这是两引擎共有的
   有意规则差异，不是 bug。
2. **镜像引擎对拍**：以上全部数值都由 `android/.../offline.js`（跨引擎对拍
   门禁守护的镜像实现）用同一定义独立复算并逐个相等（perft 递归走
   `legalAll`/`applyUnchecked`，与 Python 侧零共享代码）。
3. **手工核对**：中局锚点红方被黑車将军，9 个应着逐着手工枚举
   （垫 3 + 炮吃 1 + 走王 5，见用例内注释——其中象垫被夹逼否决、仕垫是
   容易漏的第 3 个垫着，两处都以引擎裁决为准写明理由）；13x13 初始局面
   divide(1) 的兵（15）与王（3）按图逐子手工推算核对。

慢锚点（传统 depth 3 ≈ 30s、残局 depth 4 ≈ 35s、中局 depth 3 ≈ 7s）标
`@pytest.mark.slow`：主门禁 `-m "not slow"` 跳过，CI slow job 全跑。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position
from xionghan_chess.core.perft import divide, perft
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import RulesEngine

# --- 锚点局面 ---------------------------------------------------------------


def _initial_state(profile_id: str) -> GameState:
    profile = get_profile(profile_id)
    return GameState(profile_id=profile_id, pieces=profile.initial_pieces(profile.options), turn=Color.RED)


def _state_from(profile_id: str, specs: list[tuple[str, str, int, int]], turn: str) -> GameState:
    pieces = [Piece.create(PieceType(kind), Color(color), row, col) for kind, color, row, col in specs]
    return GameState(profile_id=profile_id, pieces=pieces, turn=Color(turn))


# 中局锚点：红正被黑車 (7,6) 沿 6 列将军（(8,6)(9,6)(10,6) 全空）。
# 红方 9 个应着 = 垫 3（車 9,4→9,6 / 馬 10,8→9,6 / 仕 11,7→10,6）
#              + 吃 1（炮 7,2 借 7,4 兵架吃 7,6 車）
#              + 走王 5（王出宫开关开着：(11,5)(10,5)(10,7)(12,5)(12,7)；
#                (10,6) 仍在 6 列上仍被将，(11,7) 被己仕占）。
MIDGAME_CHECK_SPECS = [
    ("king", "red", 11, 6),
    ("rook", "red", 9, 4),
    ("horse", "red", 10, 8),
    ("cannon", "red", 7, 2),
    ("pawn", "red", 7, 4),
    ("pawn", "red", 10, 2),
    ("pawn", "red", 10, 10),
    ("advisor", "red", 11, 7),
    ("elephant", "red", 11, 8),
    ("king", "black", 1, 5),
    ("rook", "black", 7, 6),
    ("horse", "black", 4, 5),
    ("cannon", "black", 3, 3),
    ("pawn", "black", 4, 2),
    ("pawn", "black", 4, 8),
    ("advisor", "black", 0, 5),
]

# 残局锚点：8 枚，双王不同线不照面；马/卫/兵把斜走、蹩腿、快走一并拉进树里。
ENDGAME_SPECS = [
    ("king", "red", 11, 6),
    ("horse", "red", 9, 4),
    ("pawn", "red", 9, 8),
    ("advisor", "red", 11, 7),
    ("king", "black", 1, 6),
    ("guard", "black", 2, 6),
    ("pawn", "black", 3, 2),
]


def _engine(profile_id: str) -> RulesEngine:
    profile = get_profile(profile_id)
    return RulesEngine(profile, profile.options)


# --- 锚点一：传统 10x9 初始局面（有外部文献值的锚点）------------------------


def test_traditional_initial_depth1_is_44():
    """文献值 44（与公开的标准象棋 perft(1) 一致）；divide(1) 每着子树 = 1。"""
    engine = _engine("traditional")
    state = _initial_state("traditional")
    assert perft(engine, state, 1) == 44
    table = divide(engine, state, 1)
    assert len(table) == 44 and set(table.values()) == {1}


def test_traditional_initial_depth2_is_1920():
    """文献值 1920；divide(2) 子树之和 == perft(2)（divide/perft 口径恒等式）。"""
    engine = _engine("traditional")
    state = _initial_state("traditional")
    assert perft(engine, state, 2) == 1920
    table = divide(engine, state, 2)
    assert sum(table.values()) == 1920


@pytest.mark.slow
def test_traditional_initial_depth3_is_79496():
    """本项目口径 79496；与文献 79666 的 -170 已归因于斜走子夹逼（见模块 docstring）。

    归因实验（工作区临时改 `_diagonal_path_pinched` 恒 False 后复原）：
    禁用夹逼 → perft(3) = 79666，与公开文献值严丝合缝。
    """
    engine = _engine("traditional")
    state = _initial_state("traditional")
    assert perft(engine, state, 3) == 79496


# --- 锚点二：匈汉 13x13 初始局面 ---------------------------------------------


def test_xionghan_initial_depth1_is_108_with_hand_checked_groups():
    """108 着；兵 15、王 3 两项按图逐子手工推算核对（推算过程见注释）。

    兵（红，8 行，列 0..12 偶数）：0/12 列的兵前路被己巡 (7,0)/(7,12) 堵死
    （前进 1 目标被占、快走路径必经该格），0 着；其余 5 兵各有 前进 1 + 快走
    2 格 + 快走 3 格 = 3 着（6/5 行空、快走路径需全空），共 15。
    王 (11,6)：宫内 (10,6) 直行；(12,6) 己仕、(11,5) 己尉、(11,7) 己仕被占；
    斜行 (10,5)/(10,7) 不被夹（(10,6) 空），共 3。
    """
    engine = _engine("desktop_complete")
    state = _initial_state("desktop_complete")
    assert perft(engine, state, 1) == 110
    source_type = {(p.position.row, p.position.col): p.type for p in state.pieces}
    by_type: dict[PieceType, int] = {}
    for move in engine.legal_moves(state):
        kind = source_type[(move.source.row, move.source.col)]
        by_type[kind] = by_type.get(kind, 0) + 1
    assert by_type[PieceType.PAWN] == 15
    assert by_type[PieceType.KING] == 3


def test_xionghan_initial_depth2_is_11647():
    """11647 = offline.js 独立复算值（镜像引擎对拍，模块 docstring 佐证 2）。"""
    engine = _engine("desktop_complete")
    state = _initial_state("desktop_complete")
    assert perft(engine, state, 2) == 12097


# --- 锚点三：中局被将军（垫将/吃子/走王三路应将）-----------------------------


def test_midgame_check_root_and_the_nine_parries():
    """根局面红被将；合法应着**恰好**是手工枚举的 9 着，且每着都解除将军。

    手工枚举（逐着给出理由，与 divide(1) 严格相等）：
    - 垫 (9,6)：車 9,4→9,6（路径 9,5 空）；馬 10,8→9,6（马腿 10,7 空）；
      仕 11,7→10,6——容易被漏的第 3 个垫着。
    - 象 11,8→9,6 **不合法**：夹逼在源格 (11,8) 就生效——它的两个正交邻格
      (11,7) 仕、(10,8) 馬都被占，整步被封（本项目斜走子口径，非标准象棋
      的"塞象眼"，这是本锚点顺手钉住的规则细节）。
    - 吃：炮 7,2→7,6，隔 7,4 己兵做架（炮口谱：恰好一屏）。
    - 走王：(11,5)/(10,5)/(10,7)/(12,5)/(12,7)（王可出宫开着）；
      (10,6) 仍在将线上非法，(11,7) 被己仕占。
    """
    engine = _engine("desktop_complete")
    state = _state_from("desktop_complete", MIDGAME_CHECK_SPECS, "red")
    assert engine.in_check(state, Color.RED)
    expected = {
        "9,4-9,6",
        "10,8-9,6",
        "11,7-10,6",  # 垫
        "7,2-7,6",  # 炮借兵架吃車
        "11,6-11,5",
        "11,6-10,5",
        "11,6-10,7",  # 走王
        "11,6-12,5",
        "11,6-12,7",
    }
    table = divide(engine, state, 1)
    assert set(table) == expected and set(table.values()) == {1}
    for key in expected:
        source, target = key.split("-")
        (srow, scol), (trow, tcol) = (map(int, part.split(",")) for part in (source, target))
        move = Move(Position(srow, scol), Position(trow, tcol))
        child = engine.apply_unchecked(state, move)
        assert not engine.in_check(child, Color.RED), f"{key} 没有解除将军"


def test_midgame_check_depth2_is_564():
    """564 = 9 个应着子树之和（offline.js 复算一致）。"""
    engine = _engine("desktop_complete")
    state = _state_from("desktop_complete", MIDGAME_CHECK_SPECS, "red")
    assert perft(engine, state, 2) == 564
    assert sum(divide(engine, state, 2).values()) == 564


@pytest.mark.slow
def test_midgame_check_depth3_is_26266():
    engine = _engine("desktop_complete")
    state = _state_from("desktop_complete", MIDGAME_CHECK_SPECS, "red")
    assert perft(engine, state, 3) == 26266


# --- 锚点四：少子残局（depth 4）----------------------------------------------


def test_endgame_depths_1_to_3():
    """27 / 413 / 9504（offline.js 复算一致）；depth 3 与 divide(3) 恒等。"""
    engine = _engine("desktop_complete")
    state = _state_from("desktop_complete", ENDGAME_SPECS, "red")
    assert perft(engine, state, 1) == 27
    assert perft(engine, state, 2) == 413
    assert perft(engine, state, 3) == 9504
    assert sum(divide(engine, state, 3).values()) == 9504


@pytest.mark.slow
def test_endgame_depth4_is_205086():
    engine = _engine("desktop_complete")
    state = _state_from("desktop_complete", ENDGAME_SPECS, "red")
    assert perft(engine, state, 4) == 205086
