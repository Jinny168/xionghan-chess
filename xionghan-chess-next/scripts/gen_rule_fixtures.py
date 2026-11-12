"""生成 Python → JavaScript 的规则黄金用例。

用法（项目根目录）：
    python scripts/gen_rule_fixtures.py            # 重生成（默认，等价 --write）
    python scripts/gen_rule_fixtures.py --write   # 重生成两份产物
    python scripts/gen_rule_fixtures.py --check   # 重生成后逐字节比对，漂移 exit 1（55s+，放 slow job）

产物（两份，逐字节相同）：
    webapp/tests/fixtures/rules.json
    webapp/.edgeone/assets/tests/fixtures/rules.json

JS 端由 webapp/tests/verify-rules.mjs 逐条比对，要求 100% 一致。

覆盖策略
--------
1. 自对弈序列：连续局面 + 走子后的胜负判定，验证状态推进与结算。
2. 随机布局：双方各随机落子，覆盖棋子的边角判定。
3. 特殊局面：将死 / 困毙 / 三次重复 / 升变强制。
4. 规则开关变体：同一局面在不同开关下的判定差异。
5. 三连吃子定向局面（`rem:tl:*`，固定坐标、不消耗 rng）：把「只改移除集合、
   不改合法着法集合」的语义钉进 fixtures，让 removals 护栏真的能验出差异。

## 为什么 `removals` 是本轮的核心

`legal` 比对只看「着法集合」，`check` 只看「是否被将」。三连吃子**两者都不改**：
开关 on/off 时 legal 相同、check 相同，唯 `removals` 是 `[advisor,black,6,5]` vs `[]`。
所以每个 case 的 `removals` 键集合恒等于 `set(legal)`，值取
`RulesEngine.board_removals`（**全色** id 差集），按 (type,color,row,col) 字典序排序。
`captured_by_move`（只敌方）/ `capturable_squares`（语义相反）都不能拿来替代。

## Step2 启动前置断言（硬依赖，任一不满足 exit 1、不写盘）

`profiles.js::mergeOptions` 的 `key in result` 会过滤未知键。不先跑 Step1 重建档案，
fixtures 的 `p3l: true` 会被 `verify-rules.mjs` 的 `buildEngine → mergeOptions` 静默丢弃，
整个 removals 护栏必然空跑。故此处校验 Step1 产物的 ruleVersion / hash / 关键开关。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import random
import re
import sys
import uuid as _uuid
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core import model as _model  # noqa: E402
from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    Color,
    GameState,
    Move,
    Piece,
    PieceType,
    Position,
)
from xionghan_chess.core.profiles import PROFILES, RULE_VERSION, RuleOptions, get_profile  # noqa: E402
from xionghan_chess.core.rules import RulesEngine  # noqa: E402

OUT = ROOT / "webapp" / "tests" / "fixtures" / "rules.json"
OUT_EDGEONE = ROOT / "webapp" / ".edgeone" / "assets" / "tests" / "fixtures" / "rules.json"
PROFILES_JS = ROOT / "webapp" / "js" / "core" / "profiles.js"
RULES_JS = ROOT / "webapp" / "js" / "core" / "rules.js"
PROFILES_MANIFEST = ROOT / "webapp" / "js" / "core" / "profiles.manifest.json"
OUTPUTS = (OUT, OUT_EDGEONE)
GENERATED_BY = "scripts/gen_rule_fixtures.py"
PROFILE_IDS = ["desktop_complete", "desktop_classic", "web", "traditional"]
PIECE_TYPES = [item for item in PieceType]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# S1–S6 顺序护栏：sourceDigest 把「bundle 产物」也纳入哈希，故 bundle（S3/S4）
# 必须先于 fixtures（S5）。按此**固定顺序拼接字节**（顺序不得改变，否则 JS 侧
# 重算值不同）。verify-rules.mjs 启动时从磁盘重算，不等即 fail('build-order')。
SOURCE_DIGEST_FILES: tuple[tuple[str, Path], ...] = (
    ("webapp/js/core/profiles.js", ROOT / "webapp" / "js" / "core" / "profiles.js"),
    ("webapp/js/core/rules.js", ROOT / "webapp" / "js" / "core" / "rules.js"),
    ("online/core/profiles.js", ROOT / "online" / "core" / "profiles.js"),
    ("online/core/rules.js", ROOT / "online" / "core" / "rules.js"),
    ("online/public/index.html", ROOT / "online" / "public" / "index.html"),
)


def source_digest_parts() -> dict[str, str]:
    """逐文件 sha256（供 verify-rules 打印 changed 明细）。"""
    return {name: _sha256(path) for name, path in SOURCE_DIGEST_FILES}


def source_digest() -> str:
    h = hashlib.sha256()
    for _name, path in SOURCE_DIGEST_FILES:
        h.update(path.read_bytes())
    h.update(str(RULE_VERSION).encode("utf-8"))
    return h.hexdigest()


def option_keys() -> list[str]:
    """规范键集，与 `gen_web_profiles.py::option_keys()` 同一口径。"""
    return sorted(asdict(RuleOptions()))


def options_digest() -> str:
    return hashlib.sha256(json.dumps(option_keys(), separators=(",", ":")).encode("utf-8")).hexdigest()


def move_key(move: Move) -> str:
    suffix = f"={move.promotion.value}" if move.promotion else ""
    return f"{move.source.row},{move.source.col}-{move.target.row},{move.target.col}{suffix}"


def settlement_of(engine: RulesEngine, state: GameState, moves: list[Move]) -> dict:
    """一次算出 `removals` 与 `threeLineMoves`（同一个 board_removals 遍历）。

    - `removals`：每个合法着法实际移除的子（**全色**四元组）。键 = `move_key(move)`，
      键集合恒等于 `set(legal)`；无吃子 → `[]`（不省略键、不用 null）。值取
      `RulesEngine.board_removals`（before/after id 差集），按
      `(type, color, row, col)` 字典序排序、按 `piece.id` 去重。
      JS 比较器（verify-rules.mjs）必须与此处完全一致。
    - `threeLineMoves`：存在「受害子位置 ≠ 落点」的移除的着法。
      `rules.py:276-300` 的 `_apply_move` 只有 DIRECT（受害子在 move.target）与
      THREE_LINE（受害子在别处）两种，升变只动 captured 池不动棋盘 → 充要，
      无需给四元组加 `kind` 字段（严过关 M31）。
    """
    removals: dict[str, list[list]] = {}
    three_line_moves: list[str] = []
    for move in moves:
        seen: set[str] = set()
        quads: list[list] = []
        board = engine.board_removals(state, move)
        for piece in board:
            if piece.id in seen:
                continue
            seen.add(piece.id)
            quads.append([piece.type.value, piece.color.value, piece.position.row, piece.position.col])
        quads.sort(key=lambda q: (q[0], q[1], q[2], q[3]))
        key = move_key(move)
        removals[key] = quads
        if any(piece.position != move.target for piece in board):
            three_line_moves.append(key)
    return {"removals": removals, "threeLineMoves": sorted(three_line_moves)}


def removals_of(engine: RulesEngine, state: GameState, moves: list[Move]) -> dict[str, list[list]]:
    """保留一处实现的对外入口（供外部引用/文档口径）；构造点统一走 settlement_of。"""
    return settlement_of(engine, state, moves)["removals"]


def case_of(game: Game, case_id: str) -> dict:
    state = game.state
    moves = game.rules.legal_moves(state)
    settlement = settlement_of(game.rules, state, moves)
    return {
        "id": case_id,
        "profileId": game.profile.id,
        "options": asdict(game.options),
        "state": state.to_dict(),
        "check": game.rules.in_check(state, state.turn) if not state.finished else False,
        "legal": sorted(move_key(move) for move in moves),
        "removals": settlement["removals"],
        "threeLineMoves": settlement["threeLineMoves"],
    }


def _options_dict(game: Game) -> dict:
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
    engine = RulesEngine(profile, options)
    cases = []
    for index in range(count):
        state = random_position(rng, profile_id)
        moves = engine.legal_moves(state)
        settlement = settlement_of(engine, state, moves)
        cases.append(
            {
                "id": f"rand:{profile_id}:{index}",
                "profileId": profile_id,
                "options": asdict(options),
                "state": state.to_dict(),
                "check": engine.in_check(state, state.turn),
                "legal": sorted(move_key(move) for move in moves),
                "removals": settlement["removals"],
                "threeLineMoves": settlement["threeLineMoves"],
            }
        )
    return cases


def option_variant_cases(rng: random.Random) -> list[dict]:
    """同一局面在不同规则开关下的判定差异（验证开关真的生效）。"""
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
        # 第 9 条：三连吃子开关。A≠B 走法的关键变体 —— legal/check 与默认相同，
        # 唯 removals 不同（若该局面恰好有兵可成线）。
        {"pawn_three_line_capture": True},
    ]
    cases = []
    for index, overrides in enumerate(variants):
        options = profile.options.merged(overrides)
        engine = RulesEngine(profile, options)
        moves = engine.legal_moves(base_state)
        settlement = settlement_of(engine, base_state, moves)
        cases.append(
            {
                "id": f"opt:{index}:{'-'.join(overrides)}",
                "profileId": profile.id,
                "options": asdict(options),
                "state": base_state.to_dict(),
                "check": engine.in_check(base_state, base_state.turn),
                "legal": sorted(move_key(move) for move in moves),
                "removals": settlement["removals"],
                "threeLineMoves": settlement["threeLineMoves"],
            }
        )
    return cases


# ---------------------------------------------------------------------------
# 三连吃子定向局面（QA 复算过的 13 条，坐标/期望值逐字来自 §4，禁止改写）
#
# 记法：P=红兵 A=黑士 R=红车 BR=黑车 E=红象
# 固定双王 (12,0)/(0,12)（不同行不同列，避开 kingsFacing）；
# `king-in-window` 用红王(12,0)/黑王(2,4)。
# 每条 case 的 options 显式带 `pawn_three_line_capture: true`。
# 期望值在生成时**断言**（不是照抄进 fixtures）：用 Python v3 真算一遍，
# 与 QA 给的期望逐字比对，实现退化会在 Step2 就红，而不是等 verify-rules。
# ---------------------------------------------------------------------------
_THREE_LINE_CASES: list[tuple[str, list[tuple[str, str, int, int]], str, list[list], bool]] = [
    # (case_id, 摆子, move_key, 期望 removals, 是否窗口内放黑王)
    ("rem:tl:axis-h", [("P", "red", 7, 3), ("P", "red", 6, 4), ("A", "black", 6, 5)],
     "7,3-6,3", [["advisor", "black", 6, 5]], False),
    ("rem:tl:axis-v", [("P", "red", 7, 3), ("P", "red", 5, 3), ("A", "black", 4, 3)],
     "7,3-6,3", [["advisor", "black", 4, 3]], False),
    ("rem:tl:axis-d1", [("P", "red", 7, 3), ("P", "red", 7, 4), ("A", "black", 8, 5)],
     "7,3-6,3", [["advisor", "black", 8, 5]], False),
    ("rem:tl:axis-d2", [("P", "red", 7, 3), ("P", "red", 7, 2), ("A", "black", 8, 1)],
     "7,3-6,3", [["advisor", "black", 8, 1]], False),
    ("rem:tl:multiline",
     [("P", "red", 6, 6), ("P", "red", 5, 5), ("A", "black", 5, 4),
      ("A", "black", 4, 6), ("R", "red", 3, 6), ("R", "red", 2, 6)],
     "6,6-5,6", [["advisor", "black", 5, 4]], False),
    ("rem:tl:outer-near",
     [("P", "red", 6, 4), ("P", "red", 5, 5), ("A", "black", 5, 6), ("A", "black", 5, 7)],
     "6,4-5,4", [], False),
    ("rem:tl:outer-far",
     [("P", "red", 9, 1), ("P", "red", 7, 2), ("A", "black", 6, 3), ("R", "red", 5, 4)],
     "9,1-8,1", [], False),
    ("rem:tl:outer-both",
     [("P", "red", 6, 3), ("P", "red", 4, 3), ("A", "black", 3, 3),
      ("BR", "black", 2, 3), ("R", "red", 1, 3)],
     "6,3-5,3", [], False),
    ("rem:tl:disp-2", [("P", "red", 7, 6), ("P", "red", 5, 5), ("A", "black", 5, 4)],
     "7,6-5,6", [], False),
    ("rem:tl:disp-5", [("P", "red", 10, 6), ("P", "red", 5, 5), ("A", "black", 5, 4)],
     "10,6-5,6", [], False),
    ("rem:tl:king-in-window",
     [("P", "red", 3, 3), ("E", "red", 2, 5), ("BK", "black", 2, 4)],
     "3,3-2,3", [], True),
    ("rem:tl:king-replaced-rook",
     [("P", "red", 3, 3), ("E", "red", 2, 5), ("BR", "black", 2, 4)],
     "3,3-2,3", [["rook", "black", 2, 4]], False),
    ("rem:tl:far-line",
     [("P", "red", 8, 4), ("P", "red", 2, 8), ("P", "red", 2, 9), ("A", "black", 2, 10)],
     "8,4-7,4", [], False),
]

_TYPE_MAP = {
    "P": (PieceType.PAWN, Color.RED),
    "A": (PieceType.ADVISOR, Color.BLACK),
    "R": (PieceType.ROOK, Color.RED),
    "BR": (PieceType.ROOK, Color.BLACK),
    "E": (PieceType.ELEPHANT, Color.RED),
    "BK": (PieceType.KING, Color.BLACK),
}


def three_line_cases() -> list[dict]:
    """13 条确定性 case：完全不用 rng、固定坐标、id 前缀 `rem:tl:*`。"""
    profile_id = "web"
    profile = get_profile(profile_id)
    options = profile.options.merged({"pawn_three_line_capture": True})
    engine = RulesEngine(profile, options)
    cases: list[dict] = []
    for case_id, placement, probe_key, expected, king_in_window in _THREE_LINE_CASES:
        pieces: list[Piece] = [Piece(f"{case_id}:rk", PieceType.KING, Color.RED, Position(12, 0))]
        if not king_in_window:
            pieces.append(Piece(f"{case_id}:bk", PieceType.KING, Color.BLACK, Position(0, 12)))
        for index, (tag, _tag_color, row, col) in enumerate(placement):
            kind, color = _TYPE_MAP[tag]
            pieces.append(Piece(f"{case_id}:p{index}", kind, color, Position(row, col)))
        state = GameState(
            profile_id, pieces, turn=Color.RED,
            captured={Color.RED: [], Color.BLACK: []},
        )
        moves = engine.legal_moves(state)
        legal = sorted(move_key(move) for move in moves)
        settlement = settlement_of(engine, state, moves)
        removals = settlement["removals"]
        # 着法合法性前置：board_removals/applyUnchecked 都不校验着法合法性，
        # 不先断言会写出「跑绿但无意义」的用例。
        assert probe_key in legal, f"{case_id}: 探针着法 {probe_key} 不在合法着法集合里"
        got = removals.get(probe_key)
        assert got == expected, (
            f"{case_id}@{probe_key}: 期望 {expected}，Python v3 实算 {got} "
            "—— 上游给的期望值不允许改写，实现退化必须在此暴露"
        )
        cases.append(
            {
                "id": case_id,
                "profileId": profile_id,
                "options": asdict(options),
                "state": state.to_dict(),
                "check": engine.in_check(state, state.turn),
                "legal": legal,
                "removals": removals,
                "threeLineMoves": settlement["threeLineMoves"],
                # 供 verify-rules.mjs 的覆盖度/定位断言使用
                "probe": probe_key,
                "expectedRemovals": expected,
            }
        )
    return cases


def exact3_variant_cases() -> list[dict]:
    """两条确定性开关变体（严过关 M31）：同一「两我一敌 + 两端皆空」局面，只翻 p3l。

    `option_variant_cases` 的 `base_state = random_position(...)` 是随机局面，
    只翻开关不保证出现三连形状 → 护栏会 0 条比对、空跑全绿。这两条钉住
    「开关 on → 有 threeLineMoves / off → 无」，且**不消耗 rng**（固定坐标）。
    """
    profile_id = "web"
    profile = get_profile(profile_id)
    placement = [
        ("P", "red", 7, 3), ("P", "red", 6, 4), ("A", "black", 6, 5),
    ]
    probe_key = "7,3-6,3"
    cases: list[dict] = []
    for case_id, p3l, expected in (
        ("opt:tl:exact3", True, [["advisor", "black", 6, 5]]),
        ("opt:tl:exact3:off", False, []),
    ):
        options = profile.options.merged({"pawn_three_line_capture": p3l})
        assert options.pawn_three_line_capture is p3l, f"{case_id} 开关未显式生效"
        engine = RulesEngine(profile, options)
        pieces = [
            Piece(f"{case_id}:rk", PieceType.KING, Color.RED, Position(12, 0)),
            Piece(f"{case_id}:bk", PieceType.KING, Color.BLACK, Position(0, 12)),
        ]
        for index, (tag, _tag_color, row, col) in enumerate(placement):
            kind, color = _TYPE_MAP[tag]
            pieces.append(Piece(f"{case_id}:p{index}", kind, color, Position(row, col)))
        state = GameState(
            profile_id, pieces, turn=Color.RED,
            captured={Color.RED: [], Color.BLACK: []},
        )
        moves = engine.legal_moves(state)
        legal = sorted(move_key(move) for move in moves)
        settlement = settlement_of(engine, state, moves)
        assert probe_key in legal, f"{case_id}: 探针着法 {probe_key} 不在合法着法集合里"
        got = settlement["removals"].get(probe_key)
        assert got == expected, (
            f"{case_id}@{probe_key}: 期望 {expected}，实算 {got}"
        )
        want_tl = [probe_key] if p3l else []
        assert settlement["threeLineMoves"] == want_tl, (
            f"{case_id}: threeLineMoves 期望 {want_tl}，实算 {settlement['threeLineMoves']}"
        )
        cases.append(
            {
                "id": case_id,
                "profileId": profile_id,
                "options": asdict(options),
                "state": state.to_dict(),
                "check": engine.in_check(state, state.turn),
                "legal": legal,
                "removals": settlement["removals"],
                "threeLineMoves": settlement["threeLineMoves"],
                "probe": probe_key,
                "expectedRemovals": expected,
            }
        )
    return cases


def preflight() -> None:
    """Step2 启动前置断言：任一不满足 exit 1、不写盘（顺序错要能 fail）。"""
    problems: list[str] = []
    if not PROFILES_MANIFEST.exists():
        print("[preflight] profiles.manifest.json 缺失 —— 先跑 Step1: "
              "python scripts/gen_web_profiles.py --write", file=sys.stderr)
        raise SystemExit(1)
    manifest = json.loads(PROFILES_MANIFEST.read_text(encoding="utf-8"))

    # ① manifest.ruleVersion == RULE_VERSION
    if manifest.get("ruleVersion") != RULE_VERSION:
        problems.append(f"[rule-version] manifest.ruleVersion={manifest.get('ruleVersion')} != {RULE_VERSION}")

    # ② sha256(profiles.js) == profilesHash
    if not PROFILES_JS.exists() or _sha256(PROFILES_JS) != manifest.get("profilesHash"):
        problems.append("[profiles-hash] sha256(profiles.js) != manifest.profilesHash —— 先跑 Step1")

    # ③ JS DEFAULT_OPTIONS 含 pawn_three_line_capture / pawn_charge
    default: dict[str, object] = {}
    if PROFILES_JS.exists():
        text = PROFILES_JS.read_text(encoding="utf-8")
        match = re.search(r"^export const DEFAULT_OPTIONS = (.+);$", text, re.MULTILINE)
        if match:
            try:
                default = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    for key in ("pawn_three_line_capture", "pawn_charge"):
        if key not in default:
            problems.append(f"[options-key] JS DEFAULT_OPTIONS 缺 {key} —— 护栏会空跑")

    # 附加：rulesHash / optionsDigest 一致性（manifest 链完整，Step3/Step4 依赖）
    if not RULES_JS.exists() or _sha256(RULES_JS) != manifest.get("rulesHash"):
        problems.append("[rules-hash] sha256(rules.js) != manifest.rulesHash —— rules.js 在 Step1 后漂移")
    if manifest.get("optionsDigest") != options_digest():
        problems.append("[options-digest] 与当前 RuleOptions 键集不一致 —— 先跑 Step1")

    # S3/S4 已执行的证据：sourceDigest 把 bundle 产物纳入哈希，先于 S5 必须存在且新鲜
    for name, path in SOURCE_DIGEST_FILES:
        if not path.exists():
            problems.append(f"[build-order] 缺 {name} —— 先跑 S3: python scripts/build_webapp_bundle.py")
    online_html = ROOT / "online" / "public" / "index.html"
    if online_html.exists():
        raw = online_html.read_text(encoding="utf-8")
        if "threeLineCaptures" not in raw:
            problems.append("[build-order] online/public/index.html 仍是旧引擎 —— 先跑 S3/S4")

    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        print("\n[preflight] Step2 前置断言失败，未写盘。下一步命令：", file=sys.stderr)
        print("  python scripts/gen_web_profiles.py --write", file=sys.stderr)
        print(f"  python {GENERATED_BY} --write", file=sys.stderr)
        raise SystemExit(1)
    print("[preflight] OK: ruleVersion / profilesHash / rulesHash / optionsDigest / p3l+pawn_charge")


@contextlib.contextmanager
def deterministic_piece_ids():
    """`--write`/`--check` 逐字节比对的必要前提之一：固定 `Piece.create()` 的 uuid。

    严过关 M32 实测 `build_webapp_bundle.py` 无 Date/random/uuid/time/performance，
    但**本脚本**会经 `Piece.create()` 拿 `uuid.uuid4()` 随机 id，两次生成的
    `state.to_dict()` 逐字节不同。这里换成独立固定种子流，**不消费 `rng(1024)`**，
    故局面坐标、着法序列与修订前逐字一致。
    时间类噪声（timestamp / elapsedMs / clocksMs）不能靠固定 `time.monotonic` 解决：
    `GameState.turn_started_at` 的 dataclass default_factory 在类定义时已绑定真实
    函数，固定时钟会让 `elapsed` 恒为负/超大而触发假的 turn_timeout。故统一在
    `_normalize_time_fields()` 里规范化，见该函数注释。
    """
    id_rng = random.Random(20261112)
    original = _model.uuid.uuid4

    def fixed_uuid4():
        return _uuid.UUID(int=id_rng.getrandbits(128), version=4)

    _model.uuid.uuid4 = fixed_uuid4
    try:
        yield
    finally:
        _model.uuid.uuid4 = original


def build_payload() -> dict:
    rng = random.Random(1024)
    cases: list[dict] = []
    transitions: list[dict] = []
    # 整个生成过程（含 exact3 / 变体 / transitions）都在确定性 id 作用域内
    with deterministic_piece_ids():
        return _build_payload_inner(rng, cases, transitions)


def _build_payload_inner(rng: random.Random, cases: list[dict], transitions: list[dict]) -> dict:

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

    # 定向局面完全不用 rng（放在 option_variant_cases(rng) 之前，不影响随机序列）
    tl_cases = three_line_cases()
    cases.extend(tl_cases)
    print(f"  三连吃子定向局面: {len(tl_cases)}")

    exact3 = exact3_variant_cases()
    cases.extend(exact3)
    print(f"  exact3 确定性开关变体: {len(exact3)}")

    variants = option_variant_cases(rng)
    cases.extend(variants)
    print(f"  规则开关变体: {len(variants)}")

    manifest = json.loads(PROFILES_MANIFEST.read_text(encoding="utf-8"))
    return {
        "formatVersion": 1,
        "generatedBy": GENERATED_BY,
        "ruleVersion": RULE_VERSION,
        "optionsDigest": options_digest(),
        "optionsKeys": option_keys(),
        "profilesHash": manifest["profilesHash"],
        "rulesHash": manifest["rulesHash"],
        # S1–S6 顺序护栏：bundle 先于 fixtures，sourceDigest 才能录到正确的
        # online/public/index.html。verify-rules.mjs 启动时从磁盘重算。
        "sourceDigest": source_digest(),
        "sourceDigestFiles": source_digest_parts(),
        "caseCount": len(cases),
        "transitionCount": len(transitions),
        "profiles": list(PROFILES),
        "cases": cases,
        "transitions": transitions,
    }


# 时间类噪声字段：这些字段不参与任何跨端比对（verify-rules.mjs 的 settle 只比
# turn/winner/draw/reason/capturedTypes/pieceCount/historyLength），但 `time.time()`
# / `time.monotonic()` 会让两次生成的 JSON 逐字节不同。规范化成固定值，使
# `--write` 与 `--check` 可逐字节比对。**不改局面坐标/着法/移除集合**。
_TIME_KEYS = {"timestamp": 0.0, "elapsedMs": 0, "turnStartedAt": 0.0}


def _normalize_time_fields(value):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == "clocksMs" and isinstance(item, dict):
                # 双方时钟都归一到固定初值；tick 的差异不影响任何被比对的结算字段
                out[key] = {"red": 1_200_000, "black": 1_200_000}
            elif key in _TIME_KEYS:
                out[key] = _TIME_KEYS[key]
            else:
                out[key] = _normalize_time_fields(item)
        return out
    if isinstance(value, list):
        return [_normalize_time_fields(item) for item in value]
    return value


def _serialize(payload: dict) -> str:
    return json.dumps(_normalize_time_fields(payload), ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    # 无参数保持向后兼容 = 重生成（T01 直接跑 `python scripts/gen_rule_fixtures.py`）
    preflight()
    text = _serialize(build_payload())
    size_kb = len(text.encode("utf-8")) / 1024
    print(f"\n生成 {size_kb:.1f} KB / {json.loads(text)['caseCount']} 局面 / "
          f"{json.loads(text)['transitionCount']} 走子")

    if args.check:
        drift = []
        for path in OUTPUTS:
            if not path.exists():
                drift.append(str(path))
            elif path.read_text(encoding="utf-8") != text:
                drift.append(str(path))
        if drift:
            for item in drift:
                print(f"fixtures drift: {item}", file=sys.stderr)
            print(f"\n下一步：python {GENERATED_BY} --write", file=sys.stderr)
            return 1
        print(f"fixtures ok: {len(OUTPUTS)} 份逐字节一致")
        return 0

    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"写入 {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
