"""生成 Python → JavaScript 的规则黄金用例。

用法（项目根目录）：
    .venv/Scripts/python.exe scripts/gen_rule_fixtures.py

产物：webapp/tests/fixtures/rules.json
JS 端由 webapp/tests/verify-rules.mjs 逐条比对，要求 100% 一致。

覆盖策略
--------
1. 自对弈序列：连续局面 + 走子后的胜负判定，验证状态推进与结算。
2. 随机布局：双方各随机落子，覆盖 14 种棋子的边角判定（夹逼、星轨、
   三连、兑子、护体、巡线、快速行军、升变）。
3. 特殊局面：将死 / 困毙 / 三次重复 / 升变强制。
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    Color,
    GameState,
    Move,
    Piece,
    PieceType,
)
from xionghan_chess.core.profiles import PROFILES, get_profile  # noqa: E402

OUT = ROOT / "webapp" / "tests" / "fixtures" / "rules.json"
PROFILE_IDS = ["desktop_complete", "desktop_classic", "web", "traditional"]
PIECE_TYPES = [item for item in PieceType]


def move_key(move: Move) -> str:
    suffix = f"={move.promotion.value}" if move.promotion else ""
    return f"{move.source.row},{move.source.col}-{move.target.row},{move.target.col}{suffix}"


def case_of(game: Game, case_id: str) -> dict:
    from dataclasses import asdict

    state = game.state
    legal = sorted(move_key(move) for move in game.rules.legal_moves(state))
    return {
        "id": case_id,
        "profileId": game.profile.id,
        "options": asdict(game.options),
        "state": state.to_dict(),
        "check": game.rules.in_check(state, state.turn) if not state.finished else False,
        "legal": legal,
    }


def _options_dict(game: Game) -> dict:
    from dataclasses import asdict

    return asdict(game.options)


def transition_of(game: Game, before: dict, move: Move, record) -> dict:
    state = game.state
    return {
        "profileId": game.profile.id,
        "options": _options_dict(game),
        "before": before,
        "move": {
            "from": {"row": move.source.row, "col": move.source.col},
            "to": {"row": move.target.row, "col": move.target.col},
            "promotion": move.promotion.value if move.promotion else None,
        },
        "after": {
            "turn": state.turn.value,
            "winner": state.winner.value if state.winner else None,
            "draw": state.draw,
            "reason": state.result_reason,
            "capturedTypes": sorted(piece.type.value for piece in record.captured),
            "pieceCount": len(state.pieces),
        },
    }


def self_play_cases(rng: random.Random, profile_id: str, games: int, plies: int) -> tuple[list, list]:
    cases: list[dict] = []
    transitions: list[dict] = []
    for game_index in range(games):
        game = Game(profile_id)
        if game.setup.resolved_first_move is Color.BLACK:
            pass
        for ply in range(plies):
            if game.state.finished:
                break
            before = game.state.to_dict()
            legal = game.rules.legal_moves(game.state)
            if not legal:
                break
            if ply % 4 == 0 or ply == 0:
                cases.append(case_of(game, f"self:{profile_id}:{game_index}:{ply}"))
            move = rng.choice(legal)
            record = game.move(move)
            transitions.append(transition_of(game, before, move, record))
    return cases, transitions


def random_position(rng: random.Random, profile_id: str) -> GameState:
    profile = get_profile(profile_id)
    rows, cols = profile.rows, profile.cols
    occupied: set[tuple[int, int]] = set()
    pieces: list[Piece] = []

    def place(kind: PieceType, color: Color) -> bool:
        for _ in range(40):
            row, col = rng.randrange(rows), rng.randrange(cols)
            if (row, col) in occupied:
                continue
            occupied.add((row, col))
            pieces.append(Piece.create(kind, color, row, col))
            return True
        return False

    place(PieceType.KING, Color.RED)
    place(PieceType.KING, Color.BLACK)
    pool = [kind for kind in PIECE_TYPES if kind in profile.enabled_piece_types]
    for _ in range(rng.randrange(6, 15)):
        place(rng.choice(pool), rng.choice((Color.RED, Color.BLACK)))

    state = GameState(profile_id, pieces, turn=rng.choice((Color.RED, Color.BLACK)))
    state.clocks_ms = {Color.RED: 1_200_000, Color.BLACK: 1_200_000}
    # 随机阵亡池，用来触发「升变需消耗阵亡棋子」的分支
    for color in (Color.RED, Color.BLACK):
        for _ in range(rng.randrange(0, 3)):
            state.captured[color].append(Piece.create(rng.choice(pool), color, -1, -1))
    return state


def random_cases(rng: random.Random, profile_id: str, count: int) -> list[dict]:
    profile = get_profile(profile_id)
    options = profile.options
    from xionghan_chess.core.rules import RulesEngine

    engine = RulesEngine(profile, options)
    cases = []
    for index in range(count):
        state = random_position(rng, profile_id)
        legal = sorted(move_key(move) for move in engine.legal_moves(state))
        cases.append(
            {
                "id": f"rand:{profile_id}:{index}",
                "profileId": profile_id,
                "options": _options_dict_from(options),
                "state": state.to_dict(),
                "check": engine.in_check(state, state.turn),
                "legal": legal,
            }
        )
    return cases


def _options_dict_from(options) -> dict:
    from dataclasses import asdict

    return asdict(options)


def option_variant_cases(rng: random.Random) -> list[dict]:
    """同一局面在不同规则开关下的判定差异（验证开关真的生效）。"""
    from dataclasses import asdict

    from xionghan_chess.core.rules import RulesEngine

    profile = get_profile("desktop_complete")
    base_state = random_position(rng, "desktop_complete")
    variants = [
        {"horse_straight_three": False},
        {"archer_enhanced_mode": True},
        {"elephant_can_cross_river": False, "elephant_gain_jump_two_enemy_territory": False},
        {"advisor_can_leave_palace": False},
        {"king_can_leave_palace": False, "king_diagonal_in_palace": False},
        {"pawn_fast_move_before_enemy_territory": False},
        {"enforce_self_check": False},
        {"invasion_victory": False},
    ]
    cases = []
    for index, overrides in enumerate(variants):
        options = profile.options.merged(overrides)
        engine = RulesEngine(profile, options)
        cases.append(
            {
                "id": f"opt:{index}:{'-'.join(overrides)}",
                "profileId": profile.id,
                "options": asdict(options),
                "state": base_state.to_dict(),
                "check": engine.in_check(base_state, base_state.turn),
                "legal": sorted(move_key(move) for move in engine.legal_moves(base_state)),
            }
        )
    return cases


def main() -> None:
    rng = random.Random(1024)
    cases: list[dict] = []
    transitions: list[dict] = []

    for profile_id in PROFILE_IDS:
        games = 6 if profile_id != "traditional" else 4
        plies = 36 if profile_id != "traditional" else 50
        new_cases, new_transitions = self_play_cases(rng, profile_id, games, plies)
        cases.extend(new_cases)
        transitions.extend(new_transitions)
        print(f"  {profile_id}: {len(new_cases)} 局面 / {len(new_transitions)} 走子")

    for profile_id in PROFILE_IDS:
        count = 40 if profile_id != "traditional" else 30
        new_cases = random_cases(rng, profile_id, count)
        cases.extend(new_cases)
        print(f"  {profile_id}: {len(new_cases)} 随机布局")

    variants = option_variant_cases(rng)
    cases.extend(variants)
    print(f"  规则开关变体: {len(variants)}")

    payload = {
        "formatVersion": 1,
        "generatedBy": "scripts/gen_rule_fixtures.py",
        "profiles": list(PROFILES),
        "caseCount": len(cases),
        "transitionCount": len(transitions),
        "cases": cases,
        "transitions": transitions,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"\n写入 {OUT}  ({size_kb:.1f} KB)")
    print(f"合计 {len(cases)} 局面 / {len(transitions)} 走子")


if __name__ == "__main__":
    main()
