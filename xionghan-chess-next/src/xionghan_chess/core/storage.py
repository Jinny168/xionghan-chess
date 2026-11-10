from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .game import Game
from .legacy import migrate_legacy_game
from .model import Color, GameState, Piece, PieceType, UnsupportedSaveError
from .profiles import RULE_VERSION, RuleProfile, get_profile
from .rules import POSITION_KEY_VERSION
from .setup import slot_id

FORMAT_VERSION = 1

# ── F1-a 旧档迁移 ───────────────────────────────────────────────────────────
# `95c2784` 把尉/仕对调了开局位，但只有 `desktop_complete` 启用尉；`desktop_classic`
# 与 `web` 当时被连带换成了一枚"走不动、不显示、却会挡子"的尉。F1-a 已把那两档的
# roster 改回仕，于是**F1-a 之前保存的这两档棋谱**里，`setup.redSlots/blackSlots`
# 仍写着 `red:guard:11:5` / `black:guard:1:5` —— 直接加载会被 `GameSetup.build` 的
# `unavailable piece slots` 拒掉，老用户升级后打不开自己的棋谱。
#
# 这里只做**这一对类型**的显式映射，且坐标限定在旧对调位，**不**泛化成"任意同坐标
# 替换"：后者会把"槽位里写着一个已删除/未启用的兵种"这类真损坏一起静默吞掉，
# 而那正是我们想继续报错的（见 `test_removed_pieces_are_gone` 与下面两条反向用例）。
F1A_LEGACY_GUARD_SQUARES: frozenset[tuple[int, int]] = frozenset({(1, 5), (11, 5)})


def _f1a_migrate_slot(slot: object) -> object:
    """`red:guard:11:5` → `red:advisor:11:5`；其它槽位原样返回。

    形状不认识（段数不对、颜色/坐标不是字面量）时原样返回，让 `GameSetup.build`
    继续用它那条 `unavailable piece slots` 报错 —— 迁移不该顺手把解析失败也吃掉。
    """
    if not isinstance(slot, str):
        return slot
    parts = slot.split(":")
    if len(parts) != 4 or parts[1] != PieceType.GUARD.value:
        return slot
    try:
        color = Color(parts[0])
        square = (int(parts[2]), int(parts[3]))
    except ValueError:
        return slot
    if square not in F1A_LEGACY_GUARD_SQUARES:
        return slot
    return slot_id(color, PieceType.ADVISOR, square[0], square[1])


def _f1a_migrate_setup(setup: Any, profile: RuleProfile) -> Any:
    """把旧文档 `setup` 里的旧对调位尉槽位映射成仕。

    只在"该档不启用尉"时生效（`desktop_complete` 的尉是对调后正确的，不能动）。
    `setup` 形状不认识时原样返回，交给 `GameSetup.from_dict` 自己判断 —— 迁移不该
    顺手把"存档结构是坏的"也一起吃掉。
    """
    if not isinstance(setup, dict) or PieceType.GUARD in profile.enabled_piece_types:
        return setup
    migrated: dict[str, Any] = dict(setup)
    for key in ("redSlots", "blackSlots"):
        slots = migrated.get(key)
        if isinstance(slots, list):
            migrated[key] = [_f1a_migrate_slot(slot) for slot in slots]
    return migrated


def _f1a_migrate_opening_pieces(state: GameState, profile: RuleProfile) -> bool:
    """把**开局存档**盘面上的旧对调位尉升级成仕；返回是否真的改过。

    只对 `history` 为空的存档生效。**有历史的对局一律原样保留**：改了就会与
    `history[].pieceType` 对不上（复盘里出现"走过尉、盘上没有尉"），而且对进行中的
    对局做追溯性棋子变更，可能让那枚子凭空变得能动。进行中的档里那枚尉保持原语义：
    `enabled_piece_types` 把它挡在伪合法着之外（自己 0 着），但它**仍然是合法的吃子
    目标** —— 别把它写成"这枚子彻底无效"。
    """
    if PieceType.GUARD in profile.enabled_piece_types or state.history:
        return False
    stale = [
        piece
        for piece in state.pieces
        if piece.type is PieceType.GUARD and (piece.position.row, piece.position.col) in F1A_LEGACY_GUARD_SQUARES
    ]
    if not stale:
        return False
    upgrading = {(piece.color, piece.position.row, piece.position.col) for piece in stale}
    state.pieces = [
        Piece.create(PieceType.ADVISOR, piece.color, piece.position.row, piece.position.col)
        if (piece.color, piece.position.row, piece.position.col) in upgrading
        else piece
        for piece in state.pieces
    ]
    return True


def game_document(game: Game) -> dict[str, Any]:
    return {
        "formatVersion": FORMAT_VERSION,
        # Which `position_key` format the `state.positionCounts` ledger is in, so
        # a load can re-derive it instead of trusting keys it can no longer
        # reproduce (see `_rebuild_position_counts`).
        "positionKeyVersion": POSITION_KEY_VERSION,
        # 走法语义的版本（与上面两个维度正交，见 `core/profiles.RULE_VERSION`）。
        # 旧档没有这个字段 → 读作 1。它不阻止**本机**载入旧棋谱：局面是局面，
        # 引擎用今天的规则重算合法着法；它只用于三件事——提示"这份棋谱来自哪套口径"、
        # 拒绝来自**更新**版本的棋谱（读不懂就别硬读）、以及联机对齐（rooms.py）。
        "ruleVersion": RULE_VERSION,
        "profileId": game.profile.id,
        "options": asdict(game.options),
        "setup": game.setup.to_dict(),
        "state": game.state.to_dict(),
        "snapshots": list(game._snapshots),
        "savedAt": datetime.now().isoformat(timespec="seconds"),
    }


def _rebuild_position_counts(game: Game) -> dict[str, int]:
    """Re-derive the repetition ledger in the *current* key format.

    A document saved before `POSITION_KEY_VERSION` 2 carries a ledger keyed by
    the old pool-blind `position_key`. Those keys can never be produced again, so
    keeping them would silently drop every pre-load occurrence: a position seen
    twice before the load and once after would sit at 2 and the threefold draw
    would never fire (漏判). Replaying the document's own snapshots through
    today's `position_key` rebuilds the exact ledger, so the count carries across
    the version change instead of either side of it mis-judging (误判).

    The snapshot list is the pre-move state of every ply and the live state is
    the last one, which is exactly the set `Game._record_position` counted.

    ⚠️ **只在"盘面被迁移过"或"键格式换代"时调用，不要为了"统一"对所有文档重算。**
    F1-a 迁移只升级**开局档**（`history` 为空）的盘面；进行中的档（`history` 非空）
    盘面原样保留，它的 `snapshots` 里本来就有那枚旧子，`position_key(state)` 就在
    原台账里 —— **保留原键是对的、自洽的**。若把它也一起重算，等于把 mid 档的守卫
    键抹掉、计数从 0 重新开始，那正是 L-06 当初修的错判方向的反向错误。
    """
    counts: dict[str, int] = {}
    for snapshot in game._snapshots:
        key = game.rules.position_key(GameState.from_dict(snapshot))
        counts[key] = counts.get(key, 0) + 1
    key = game.rules.position_key(game.state)
    counts[key] = counts.get(key, 0) + 1
    return counts


def _assert_in_bounds(profile: RuleProfile, state: GameState, where: str) -> None:
    """按 `profile.rows/cols` 校验坐标上界。

    `Position` 只管非负；上界依赖棋盘尺寸，所以在这里查。
    越界会让 `piece_at` 静默取不到，最后变成"无王可吃"的僵尸局。
    """
    for piece in state.pieces:
        row, col = piece.position.row, piece.position.col
        # 上下界都查：`Position` 本身允许负值（引擎用它探测越界格），
        # 所以"存档里出现负坐标"只能在这里拦。
        if row < 0 or col < 0 or row >= profile.rows or col >= profile.cols:
            raise UnsupportedSaveError(f"{where}坐标越界：row={row}, col={col}（棋盘 {profile.rows}×{profile.cols}）")


def game_from_document(data: dict[str, Any]) -> Game:
    if not isinstance(data, dict):
        raise ValueError("棋谱文件内容无效")
    if int(data.get("formatVersion", 0)) != FORMAT_VERSION:
        raise ValueError("不支持的棋谱文件版本")
    # 旧档（≤1）照常载入：局面本身没变，变的是"哪些着法合法"，而合法着法是**算**出来的。
    # 但来自**更新**版本的棋谱不能硬读 —— 那套走法这个引擎不认识，读进来的局面
    # 会在下一步被自己判成非法着法，比直接拒绝更糟。
    rule_version = int(data.get("ruleVersion", 1))
    if rule_version > RULE_VERSION:
        raise ValueError(
            f"棋谱来自更新的规则版本（ruleVersion={rule_version}），当前程序支持到 {RULE_VERSION}，请升级后再打开"
        )
    raw_state = data.get("state")
    if not isinstance(raw_state, dict):
        raise ValueError("棋谱缺少有效的当前局面")
    state = GameState.from_dict(raw_state)
    profile_id = str(data.get("profileId", state.profile_id))
    if profile_id != state.profile_id:
        raise ValueError("棋谱规则档案与局面不一致")
    _profile = get_profile(profile_id)
    _assert_in_bounds(_profile, state, "当前局面")
    # F1-a：句柄在文档加载边界（见 F1A_LEGACY_GUARD_SQUARES 注释）。
    migrated_pieces = _f1a_migrate_opening_pieces(state, _profile)
    raw_snapshots = data.get("snapshots", [])
    if not isinstance(raw_snapshots, list):
        raise ValueError("棋谱复盘数据无效")
    snapshots: list[dict[str, Any]] = []
    for item in raw_snapshots:
        if not isinstance(item, dict):
            raise ValueError("棋谱复盘数据无效")
        snapshot = GameState.from_dict(item)
        if snapshot.profile_id != profile_id:
            raise ValueError("棋谱包含不同规则档案的局面")
        _assert_in_bounds(_profile, snapshot, f"复盘第 {len(snapshots) + 1} 步")
        snapshots.append(snapshot.to_dict())
    if snapshots and len(snapshots) != len(state.history):
        raise ValueError("棋谱步数与复盘数据不一致")
    game = Game.from_state(state, data.get("options", {}), _f1a_migrate_setup(data.get("setup"), _profile))
    game._snapshots = snapshots
    # A document written before the pool entered the key cannot be trusted as-is;
    # anything carrying today's marker is loaded verbatim.
    if migrated_pieces or int(data.get("positionKeyVersion", 1)) < POSITION_KEY_VERSION:
        # 开局档被迁移过时也要重建：旧台账里的键带 `guard`，升级后再也产生不出来，
        # 留着就是一串永远不会再命中、也永远清不掉的幽灵键。
        game.state.position_counts = _rebuild_position_counts(game)
    game.state.turn_started_at = time.monotonic()
    return game


def game_from_content(value: str | dict[str, Any]) -> Game:
    """Load a current document or migrate legacy .fen content."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        data = parsed if isinstance(parsed, dict) else migrate_legacy_game(value)
    else:
        data = value
    if int(data.get("formatVersion", 0)) != FORMAT_VERSION:
        data = migrate_legacy_game(data)
    return game_from_document(data)
