from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable

from xionghan_chess.i18n import t

from .model import Color, Piece, PieceType


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
    archer_enhanced_mode: bool = False
    pawn_fast_move_before_enemy_territory: bool = True
    pawn_backward_at_base: bool = True
    pawn_full_movement_at_base: bool = True
    pawn_resurrection: bool = True
    pawn_promotion: bool = True
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
    armor_appear: bool = True
    assassin_appear: bool = True
    shield_appear: bool = True
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
            "pawn_fast_move": "pawn_fast_move_before_enemy_territory",
            "pawn_fast_move_enabled": "pawn_fast_move_before_enemy_territory",
            "pawn_fast_move_before_enemy_territory_enabled": "pawn_fast_move_before_enemy_territory",
            "pawn_resurrection_enabled": "pawn_resurrection",
            "pawn_promotion_enabled": "pawn_promotion",
            "pawn_backward_at_base_enabled": "pawn_backward_at_base",
            "pawn_full_movement_at_base_enabled": "pawn_full_movement_at_base",
            "ju_appear": "rook_appear", "ma_appear": "horse_appear",
            "xiang_appear": "elephant_appear", "shi_appear": "advisor_appear",
            "pao_appear": "cannon_appear", "wei_appear": "guard_appear",
            "she_appear": "archer_appear", "lei_appear": "thunder_appear",
            "jia_appear": "armor_appear", "ci_appear": "assassin_appear",
            "dun_appear": "shield_appear", "xun_appear": "patrol_appear",
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
    PieceType.THUNDER: "檑", PieceType.ARMOR: "甲", PieceType.ASSASSIN: "刺",
    PieceType.SHIELD: "楯", PieceType.PATROL: "巡",
}
BLACK_NAMES = {
    PieceType.KING: "汗", PieceType.ROOK: "車", PieceType.HORSE: "馬",
    PieceType.ELEPHANT: "象", PieceType.ADVISOR: "士", PieceType.CANNON: "砲",
    PieceType.PAWN: "卒", PieceType.GUARD: "衛", PieceType.ARCHER: "䠶",
    PieceType.THUNDER: "礌", PieceType.ARMOR: "胄", PieceType.ASSASSIN: "伺",
    PieceType.SHIELD: "碷", PieceType.PATROL: "廵",
}


def specs(color: Color, items: Iterable[tuple[PieceType, int, int]]) -> list[PieceSpec]:
    return [PieceSpec(kind, color, row, col) for kind, row, col in items]


def xionghan_side(color: Color, complete: bool, web: bool = False) -> list[PieceSpec]:
    flip = (lambda row: 12 - row) if color is Color.RED else (lambda row: row)
    items: list[tuple[PieceType, int, int]] = []
    if complete:
        items += [
            (PieceType.ARCHER, 0, 0), (PieceType.SHIELD, 0, 1),
            (PieceType.ARMOR, 0, 2), (PieceType.ASSASSIN, 0, 3),
            (PieceType.THUNDER, 0, 4), (PieceType.GUARD, 0, 6),
            (PieceType.THUNDER, 0, 8), (PieceType.ASSASSIN, 0, 9),
            (PieceType.ARMOR, 0, 10), (PieceType.SHIELD, 0, 11),
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
        items += [(PieceType.PATROL, 5, 0), (PieceType.PATROL, 5, 12)]
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

PROFILES: dict[str, RuleProfile] = {
    "desktop_complete": RuleProfile(
        "desktop_complete", "完整模式", 13, 13,
        tuple(xionghan_side(Color.BLACK, True) + xionghan_side(Color.RED, True)), ALL,
        RuleOptions(), RED_NAMES, BLACK_NAMES,
    ),
    "desktop_classic": RuleProfile(
        "desktop_classic", "经典模式", 13, 13,
        tuple(xionghan_side(Color.BLACK, False) + xionghan_side(Color.RED, False)), CLASSIC,
        RuleOptions(), RED_NAMES, BLACK_NAMES,
    ),
    "web": RuleProfile(
        "web", "精简模式", 13, 13,
        tuple(xionghan_side(Color.BLACK, False, True) + xionghan_side(Color.RED, False, True)), WEB,
        RuleOptions(pawn_resurrection=False, pawn_promotion=False), RED_NAMES, BLACK_NAMES,
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
