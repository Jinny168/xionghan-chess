from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable

from xionghan_chess.i18n import t

from .model import Color, Piece, PieceType


# The 13x13 "Xion Xiangqi" board. Red is the mirror image of Black, so Red's
# back rank 0 corresponds to Black's back rank 12.
XIONGHAN_ROWS = 13
XIONGHAN_COLS = 13
# Home rank of the patrol ("巡") before mirroring. Black starts on this rank and
# Red starts on its mirror image, so the patrol may only ever move along one of
# those two ranks. Only profiles that enable PieceType.PATROL place it.
PATROL_HOME_ROW = 5


@dataclass(frozen=True, slots=True)
class RuleOptions:
    king_can_leave_palace: bool = True
    king_diagonal_in_palace: bool = True
    king_lose_diagonal_outside_palace: bool = True
    invasion_victory: bool = True
    advisor_can_leave_palace: bool = True
    advisor_gain_straight_outside_palace: bool = True
    elephant_can_cross_river: bool = True
    elephant_gain_jump_two_enemy_territory: bool = True
    horse_straight_three: bool = True
    horse_blocked_by_leg: bool = True          # 别马腿；关闭后日字走法同国际象棋
    horse_straight_three_move_only: bool = False  # 直走三格仅可移动、不可吃子（依赖 horse_straight_three）
    archer_enhanced_mode: bool = False
    pawn_fast_move_before_enemy_territory: bool = True
    pawn_backward_at_base: bool = True
    pawn_full_movement_at_base: bool = True
    pawn_resurrection: bool = True
    pawn_promotion: bool = True
    pawn_charge: bool = False                 # 敌阵冲锋（过阴山后直线多格，不吃子）
    pawn_three_line_capture: bool = False     # 兵参与"三连吃子"（与甲同构）
    enforce_self_check: bool = True
    threefold_draw: bool = True
    no_progress_draw_plies: int = 120

    rook_appear: bool = True
    horse_appear: bool = True
    elephant_appear: bool = True
    advisor_appear: bool = True
    king_appear: bool = True
    cannon_appear: bool = True
    pawn_appear: bool = True
    guard_appear: bool = True
    archer_appear: bool = True
    thunder_appear: bool = True
    patrol_appear: bool = True

    def merged(self, values: dict[str, object] | None) -> "RuleOptions":
        if not values:
            return self
        aliases = {
            "king_can_diagonal_in_palace": "king_diagonal_in_palace",
            "shi_can_leave_palace": "advisor_can_leave_palace",
            "shi_gain_straight_outside_palace": "advisor_gain_straight_outside_palace",
            "xiang_can_cross_river": "elephant_can_cross_river",
            "xiang_gain_jump_two_outside_river": "elephant_gain_jump_two_enemy_territory",
            "ma_can_straight_three": "horse_straight_three",
            "ma_blocked_by_leg": "horse_blocked_by_leg",
            "horse_blocked_by_leg_enabled": "horse_blocked_by_leg",
            "ma_straight_three_move_only": "horse_straight_three_move_only",
            "horse_straight_three_move_only_enabled": "horse_straight_three_move_only",
            "pawn_fast_move": "pawn_fast_move_before_enemy_territory",
            "pawn_fast_move_enabled": "pawn_fast_move_before_enemy_territory",
            "pawn_fast_move_before_enemy_territory_enabled": "pawn_fast_move_before_enemy_territory",
            "pawn_resurrection_enabled": "pawn_resurrection",
            "pawn_promotion_enabled": "pawn_promotion",
            "pawn_backward_at_base_enabled": "pawn_backward_at_base",
            "pawn_full_movement_at_base_enabled": "pawn_full_movement_at_base",
            "pawn_charge_enabled": "pawn_charge",
            "pawn_three_line_capture_enabled": "pawn_three_line_capture",
            "ju_appear": "rook_appear", "ma_appear": "horse_appear",
            "xiang_appear": "elephant_appear", "shi_appear": "advisor_appear",
            "pao_appear": "cannon_appear", "wei_appear": "guard_appear",
            "she_appear": "archer_appear", "lei_appear": "thunder_appear",
            "xun_appear": "patrol_appear",
        }
        normalized = {aliases.get(key, key): value for key, value in values.items()
                      if key not in {"archer_weak_mode", "sheWeakMode", "she_weak_mode"}}
        if "archer_enhanced_mode" not in normalized:
            for legacy_key in ("archer_weak_mode", "sheWeakMode", "she_weak_mode"):
                if legacy_key in values:
                    normalized["archer_enhanced_mode"] = not bool(values[legacy_key])
                    break
        normalized["king_appear"] = True
        allowed = asdict(self)
        allowed.update({k: v for k, v in normalized.items() if k in allowed})
        return replace(self, **allowed)

    def piece_enabled(self, piece_type: PieceType) -> bool:
        if piece_type is PieceType.KING:
            return True
        return bool(getattr(self, f"{piece_type.value}_appear"))


# 规则之间的**单向依赖**：值 = 该选项要成立，必须先开启的上游选项。
#
# 只登记"关掉上游后，下游必然无意义"的边 —— 判据是**在引擎里下游已被上游 `and` 住**
# （`rules.py` 里能指出 `X and Y` 的地方），不是"感觉相关"。
# 例：`advisor_gain_straight_outside_palace` 在 `_advisor` 里写成
# `straight and advisor_can_leave_palace and advisor_gain_straight_outside_palace`，
# 所以出宫关掉后它必然是死开关，UI 该置灰而不是让用户以为设了有用。
OPTION_DEPENDS_ON: dict[str, tuple[str, ...]] = {
    "king_lose_diagonal_outside_palace": ("king_can_leave_palace",),
    "advisor_gain_straight_outside_palace": ("advisor_can_leave_palace",),
    "elephant_gain_jump_two_enemy_territory": ("elephant_can_cross_river",),
    "horse_straight_three_move_only": ("horse_straight_three",),
}


def option_enabled_by(options: "RuleOptions", key: str) -> bool:
    """该选项的上游是否全部开启；没有依赖项时恒为 True。"""
    return all(bool(getattr(options, parent, True)) for parent in OPTION_DEPENDS_ON.get(key, ()))


def option_dependencies() -> dict[str, list[str]]:
    """给三端 UI 用的依赖表（JSON 友好：list 而不是 tuple）。"""
    return {child: list(parents) for child, parents in OPTION_DEPENDS_ON.items()}


@dataclass(frozen=True, slots=True)
class PieceSpec:
    type: PieceType
    color: Color
    row: int
    col: int


@dataclass(frozen=True, slots=True)
class RuleProfile:
    id: str
    title: str
    rows: int
    cols: int
    pieces: tuple[PieceSpec, ...]
    enabled_piece_types: frozenset[PieceType]
    options: RuleOptions
    red_names: dict[PieceType, str]
    black_names: dict[PieceType, str]

    def initial_pieces(self, options: RuleOptions | None = None) -> list[Piece]:
        active = options or self.options
        return [Piece.create(p.type, p.color, p.row, p.col)
                for p in self.pieces if active.piece_enabled(p.type)]

    def name_of(self, piece: Piece) -> str:
        names = self.red_names if piece.color is Color.RED else self.black_names
        return names[piece.type]

    def display_name_of(self, piece: Piece, language: str = "zh-CN") -> str:
        if language == "en":
            return t(f"piece_name.{piece.type.value}", language)
        return self.name_of(piece)


RED_NAMES = {
    PieceType.KING: "漢", PieceType.ROOK: "俥", PieceType.HORSE: "傌",
    PieceType.ELEPHANT: "相", PieceType.ADVISOR: "仕", PieceType.CANNON: "炮",
    PieceType.PAWN: "兵", PieceType.GUARD: "尉", PieceType.ARCHER: "射",
    PieceType.THUNDER: "檑", PieceType.PATROL: "巡",
}
BLACK_NAMES = {
    PieceType.KING: "汗", PieceType.ROOK: "車", PieceType.HORSE: "馬",
    PieceType.ELEPHANT: "象", PieceType.ADVISOR: "士", PieceType.CANNON: "砲",
    PieceType.PAWN: "卒", PieceType.GUARD: "衛", PieceType.ARCHER: "䠶",
    PieceType.THUNDER: "礌", PieceType.PATROL: "廵",
}


def specs(color: Color, items: Iterable[tuple[PieceType, int, int]]) -> list[PieceSpec]:
    return [PieceSpec(kind, color, row, col) for kind, row, col in items]


def xionghan_side(color: Color, complete: bool, web: bool = False) -> list[PieceSpec]:
    flip = (lambda row: XIONGHAN_ROWS - 1 - row) if color is Color.RED else (lambda row: row)
    items: list[tuple[PieceType, int, int]] = []
    if complete:
        # 软删甲/楯/刺：后排只保留射、尉、檑。
        # 尉固定压在将/帅**正后方**（红 (12,6) / 黑 (0,6)，主教的斜线正好被两只士占住
        # → 首着 0）。这是刻意的平衡约束：尉是最强子，开局不许它自己先动，
        # 必须先腾士位才能出动。别再"顺手优化"成首着 4，那会把这个限制抹掉。
        items += [
            (PieceType.ARCHER, 0, 0), (PieceType.THUNDER, 0, 4),
            (PieceType.GUARD, 0, 6), (PieceType.THUNDER, 0, 8),
            (PieceType.ARCHER, 0, 12),
        ]
    elif web:
        items += [
            (PieceType.ARCHER, 0, 0), (PieceType.THUNDER, 0, 4),
            (PieceType.THUNDER, 0, 8), (PieceType.ARCHER, 0, 12),
        ]
    else:
        items += [
            (PieceType.ARCHER, 0, 0), (PieceType.THUNDER, 0, 4),
            (PieceType.THUNDER, 0, 8), (PieceType.ARCHER, 0, 12),
        ]
    # 士按传统象棋对称布在将/帅两侧（红 (11,5)/(11,7)、黑 (1,5)/(1,7)），共 2 枚。
    items += [
        (PieceType.ROOK, 1, 2), (PieceType.HORSE, 1, 3),
        (PieceType.ELEPHANT, 1, 4), (PieceType.ADVISOR, 1, 5),
        (PieceType.KING, 1, 6), (PieceType.ADVISOR, 1, 7),
        (PieceType.ELEPHANT, 1, 8), (PieceType.HORSE, 1, 9),
        (PieceType.ROOK, 1, 10), (PieceType.CANNON, 3, 1),
        (PieceType.CANNON, 3, 11),
    ]
    items += [(PieceType.PAWN, 4, col) for col in range(0, 13, 2)]
    if complete or not web:
        items += [(PieceType.PATROL, PATROL_HOME_ROW, 0),
                  (PieceType.PATROL, PATROL_HOME_ROW, XIONGHAN_COLS - 1)]
    return specs(color, [(kind, flip(row), col) for kind, row, col in items])


def traditional_side(color: Color) -> list[PieceSpec]:
    flip = (lambda row: 9 - row) if color is Color.RED else (lambda row: row)
    base = [
        (PieceType.ROOK, 0, 0), (PieceType.HORSE, 0, 1),
        (PieceType.ELEPHANT, 0, 2), (PieceType.ADVISOR, 0, 3),
        (PieceType.KING, 0, 4), (PieceType.ADVISOR, 0, 5),
        (PieceType.ELEPHANT, 0, 6), (PieceType.HORSE, 0, 7),
        (PieceType.ROOK, 0, 8), (PieceType.CANNON, 2, 1),
        (PieceType.CANNON, 2, 7),
    ] + [(PieceType.PAWN, 3, col) for col in range(0, 9, 2)]
    return specs(color, [(kind, flip(row), col) for kind, row, col in base])


STANDARD = frozenset({PieceType.KING, PieceType.ROOK, PieceType.HORSE, PieceType.ELEPHANT,
                      PieceType.ADVISOR, PieceType.CANNON, PieceType.PAWN})
ALL = frozenset(PieceType)
WEB = STANDARD | {PieceType.ARCHER, PieceType.THUNDER}
CLASSIC = WEB | {PieceType.PATROL}

# ---------------------------------------------------------------------------
# 三种对弈模式的规则基线（定义见 `docs/GAME_MODES.md`）
#
# 设计原则：**两个正交维度** —— 棋子构成（全子 / 减子）与规则强度（全加强 / 传统）。
#   完整 = 全子 + 全加强
#   经典 = 全子 + 传统棋子回退经典规则（特色棋子保留自身规则）
#   精简 = 减子 + 全加强（差异只来自棋子构成，规则与完整完全一致）
# 这样"少了几枚子"和"规则变不变"互不纠缠，用户换模式时只需理解一个变量。
# ---------------------------------------------------------------------------

# 完整模式：所有自定义规则开启、所有棋子加强。
# 显式写出与默认值不同的四项 —— 只看这一处就知道"加强"加了什么。
COMPLETE_OPTIONS = RuleOptions(
    horse_blocked_by_leg=False,        # 加强：不别马腿（日字走法同国际象棋）
    archer_enhanced_mode=True,         # 加强：射/䠶 自由斜走三格
    pawn_charge=True,                  # 敌阵冲锋：过阴山后沿直线多格（不吃子）
    pawn_three_line_capture=True,      # 兵参与三连吃子
    # 其余项默认已是加强值：出宫/宫内斜走、仕出宫直走、相过河+敌境跳两格、
    # 马直走三格、兵快速行军/底线后退/四向/复活/升变。
)

# 经典模式：**同样全子**，但士/象/马/兵/将回退到最经典的中国象棋走法。
# 特色棋子（尉/射/檑/巡）没有"经典原型"，保留自身规则，故只关传统棋子的加强项。
CLASSIC_OPTIONS = RuleOptions(
    king_can_leave_palace=False,
    king_diagonal_in_palace=False,
    advisor_can_leave_palace=False,
    advisor_gain_straight_outside_palace=False,
    elephant_can_cross_river=False,
    elephant_gain_jump_two_enemy_territory=False,
    horse_blocked_by_leg=True,          # 经典：必别马腿
    horse_straight_three=False,
    horse_straight_three_move_only=False,
    archer_enhanced_mode=False,
    pawn_fast_move_before_enemy_territory=False,
    pawn_backward_at_base=False,
    pawn_full_movement_at_base=False,
    pawn_resurrection=False,
    pawn_promotion=False,
    pawn_charge=False,
    pawn_three_line_capture=False,
    # 出宫关闭后 `king_lose_diagonal_outside_palace` / `advisor_gain_straight...` /
    # `elephant_gain_jump_two...` 都成了无效项（引擎里本就被 `and` 住），
    # 设置界面会按依赖表把它们置灰。
)

# 精简模式：棋子减到 9 型，规则**与完整模式完全一致**。
WEB_OPTIONS = COMPLETE_OPTIONS

PROFILES: dict[str, RuleProfile] = {
    "desktop_complete": RuleProfile(
        "desktop_complete", "完整模式", 13, 13,
        tuple(xionghan_side(Color.BLACK, True) + xionghan_side(Color.RED, True)), ALL,
        COMPLETE_OPTIONS, RED_NAMES, BLACK_NAMES,
    ),
    "desktop_classic": RuleProfile(
        "desktop_classic", "经典模式", 13, 13,
        # 与完整模式同一套布局、同一批兵种，只有规则不同
        tuple(xionghan_side(Color.BLACK, True) + xionghan_side(Color.RED, True)), ALL,
        CLASSIC_OPTIONS, RED_NAMES, BLACK_NAMES,
    ),
    "web": RuleProfile(
        "web", "精简模式", 13, 13,
        tuple(xionghan_side(Color.BLACK, False, True) + xionghan_side(Color.RED, False, True)), WEB,
        WEB_OPTIONS, RED_NAMES, BLACK_NAMES,
    ),
    "traditional": RuleProfile(
        "traditional", "传统象棋", 10, 9,
        tuple(traditional_side(Color.BLACK) + traditional_side(Color.RED)), STANDARD,
        RuleOptions(king_can_leave_palace=False, king_diagonal_in_palace=False,
                    king_lose_diagonal_outside_palace=True, invasion_victory=False,
                    advisor_can_leave_palace=False, advisor_gain_straight_outside_palace=False,
                    elephant_can_cross_river=False, elephant_gain_jump_two_enemy_territory=False,
                    horse_straight_three=False,
                    pawn_fast_move_before_enemy_territory=False,
                    pawn_backward_at_base=False, pawn_full_movement_at_base=False,
                    pawn_resurrection=False, pawn_promotion=False), RED_NAMES, BLACK_NAMES,
    ),
}


def get_profile(profile_id: str) -> RuleProfile:
    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(t("error.unknown_profile", profile=profile_id)) from exc


def profile_rule_values(profile_id: str, overrides: dict[str, object] | None = None) -> dict[str, object]:
    """Return rule values scoped to one profile without leaking disabled pieces."""
    profile = get_profile(profile_id)
    values = asdict(profile.options.merged(overrides))
    for kind in PieceType:
        if kind not in profile.enabled_piece_types:
            values[f"{kind.value}_appear"] = False
    values["king_appear"] = True
    return values
