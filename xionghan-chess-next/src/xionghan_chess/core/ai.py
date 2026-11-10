from __future__ import annotations

import math
import os
import random
import threading
import time
from dataclasses import dataclass, replace
from enum import StrEnum

from .ai_see import static_exchange_score
from .game import RESTORE_PAWN_LIMIT, Game
from .model import Color, GameState, Move, Piece, PieceType, Position

# `pool_signature` is re-exported here (rules.py owns the format) because the
# pool-blindness guardrail test imports it alongside `evaluation_key`.
from .rules import RulesEngine, pool_signature  # noqa: F401


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"
    MASTER = "master"


# 对外档位（产品口径，2026-11 并档）：只有三档。
# `EASY / EXPERT / MASTER` 三个枚举成员保留，只为旧配置/旧存档能载入；
# 它们的 `CONFIGS` 条目是 **同一对象别名**，不复制数值（复制会制造两份真相）。
PUBLIC_DIFFICULTIES: tuple[Difficulty, ...] = (
    Difficulty.BEGINNER,
    Difficulty.MEDIUM,
    Difficulty.HARD,
)

# 旧名 → 三档。`easy` 归 **beginner** 而不是 medium：easy 是 1.5s/d4/randomness 0.35，
# medium 是 5s/d6/randomness 0.05（近乎满强度）。把「初级」直接抬到中级 = 变强，
# 把 easy 留在入门侧才是「并档不坑人」的方向。
LEGACY_DIFFICULTY_ALIASES: dict[str, str] = {
    "beginner": "beginner",
    "easy": "beginner",
    "medium": "medium",
    "hard": "hard",
    "expert": "hard",
    "master": "hard",
}


def normalize_difficulty(value: str) -> str:
    """旧档位名 → 三档之一（只做 strip/lower + 查表；未知值原样返回给 `Difficulty` 报错）。

    并档后的口径：`easy→beginner`、`expert→hard`、`master→hard`。
    """
    key = value.strip().lower()
    return LEGACY_DIFFICULTY_ALIASES.get(key, key)


# 静态搜索（quiescence）单个**根着法**内的节点上限。
# 作用：吃子链偶发跑飞时不让它独吞整个思考预算；**正常局面应当一次都不触发**。
# 计数口径：单个**静态搜索**（一次 `_quiescence` 入口及其递归）的节点数，
#   不是"某根着法整棵树"的累计 —— 后者会随尝试深度线性上涨，不能当跑飞信号。
#
# 为什么是 80 而不是更小的 40 —— 有实测（medium / seed 12345 / 四个回归局面）：
#     局面        cap 80 的 trunc   cap 40 的 trunc
#     开局             0                 1
#     3 手后           0                 1
#     炮中路           0                 1
#     马炮对攻         0                 1
#   即 **cap 40 会把正常搜索切掉**，与"只截跑飞的链"的设计目标直接冲突；
#   40 那版"选点没变"是运气，不是设计保证。
#   （选点对照：cap 80/40 在这四个局面上都是 `11,9-8,9`。）
#
# 另有一条边界事实：上一个值调到 40 时，在一个自建的高密度吃子局面上选点发生了改变
#   （`6,1-1,1` → `7,6-6,6`）——因为"被截断的根着法不得成为 best"。这说明**上限一旦过紧
#   就会真的改棋**，是回到 80 的第二个理由。
#
# ⚠️ 80 本身仍缺"正常分布"的统计依据（此前引用的 qnodes 分布非实测、已作废），
#   所以只当作"有上限、且不切正常局面"的保守值。将来要用真实测量定值，需先给出
#   可复现的命令与原始输出（按 62 子 / 44 子 / 10×9 三种盘型分别标定）；
#   本轮靠 `quiescence_truncations` 埋点观察触发频率，不改逻辑。
QUIESCENCE_NODE_LIMIT = 80


@dataclass(frozen=True, slots=True)
class SearchConfig:
    depth: int
    time_limit: float
    randomness: float
    quiescence_depth: int
    candidate_count: int
    branch_limit: int
    root_limit: int
    # 取样窗口的分差上限（厘兵）。只对走"从名次 2..N 里抽样"的弱档有意义：
    # 90cp 在 13×13 上不足一个兵（120），窗口实际只剩 2–3 手，等于没弱化。
    sample_margin: int = 90
    # 主搜索节点上限（`_search` 调用次数；**不含** qnodes）。`None` = 不启用。
    # 到点抛 `SearchTimeout`，理由记 `"nodes"`；墙钟到点记 `"wall"`。
    # 2.0.0 暂不启用（中局节点数无可靠测量），字段与工具保留。
    max_nodes: int | None = None


def resolve_time_scale(instance: float | None, env: str | None) -> float:
    """时间缩放解析：实例参数 → 环境变量 `AI_TIME_SCALE` → 1.0。

    环境变量保留历史上限 `max(0.1, ...)`（0.05 实际按 0.1 跑，`bench_roots` 的
    provenance 依赖这条）；**实例参数按原值使用** —— 它是显式 API。
    """
    if instance is not None:
        return instance
    return max(0.1, float(env)) if env is not None else 1.0


CONFIGS = {
    # B1 陪练档：弱化靠"从第 2..N 名里按概率取样"，不靠降深度/降时间。
    #   · `randomness` 是主旋钮（概率），`sample_margin` 是水平下限（分差上限），
    #     `candidate_count` 只影响多样性 —— 三个旋钮别混着调；
    #   · **取样集合不含第 1 名**：包含它会让名义 0.35 的真实弱化率只剩约 28%，
    #     概率也就无法标定；
    #   · beginner 的分差放到 150（≈1.25 个兵）才够出窗口。
    Difficulty.BEGINNER: SearchConfig(1, 2.0, 0.55, 3, 4, 3, 5, sample_margin=150),
    # B′：depth 写 2（真能达到），root 18→7、branch 10→5，让 d2 装进 cap 5s。
    # 实测 d2@root18/b10 需 5.8–12.1s；节点≈root×branch，180→54 后中局约 3.3s。
    Difficulty.MEDIUM: SearchConfig(2, 5.0, 0.0, 4, 1, 5, 7),
    # B′：depth 3（真能达到），root 18→10、branch 18→10，让 d3 装进 cap 12s。
    Difficulty.HARD: SearchConfig(3, 12.0, 0.0, 6, 1, 10, 10),
}

# 旧枚举 → 三档别名。**同一对象**，不是 `replace()` 出来的副本。
CONFIGS[Difficulty.EASY] = CONFIGS[Difficulty.BEGINNER]
CONFIGS[Difficulty.EXPERT] = CONFIGS[Difficulty.HARD]
CONFIGS[Difficulty.MASTER] = CONFIGS[Difficulty.HARD]

# 读条分母：depth 诚实后会提前返回，median 明显低于 cap；用设计给的预估 median
# （0.7/3.0/7.0），首次实测后只回填这一处 + locale。
EXPECTED_MOVE_SECONDS: dict[Difficulty, float] = {
    Difficulty.BEGINNER: 0.7,
    Difficulty.EASY: 0.7,
    Difficulty.MEDIUM: 3.0,
    Difficulty.HARD: 7.0,
    Difficulty.EXPERT: 7.0,
    Difficulty.MASTER: 7.0,
}
# 搜索开始前有一段**不可中断前缀**（`legal_moves` + 两次 `_order`/`_root_bias` 全扫），
# 架构总监实测 p50≈0.30s、max=0.78s；看门狗必须把这段加上，否则 cap=2.0 时
# 2.3s 的旧公式会掐掉 p95≈2.5s 的合法长手，表现为"AI 走了个怪手"。
PREFIX_MAX = 0.78
WATCHDOG_SECONDS: dict[Difficulty, float] = {
    difficulty: round(PREFIX_MAX + CONFIGS[difficulty].time_limit * 1.15, 3) for difficulty in Difficulty
}

VALUES = {
    PieceType.KING: 50_000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 500,
    PieceType.HORSE: 450,
    PieceType.ELEPHANT: 260,
    PieceType.ADVISOR: 240,
    PieceType.PAWN: 120,
    PieceType.GUARD: 420,
    PieceType.ARCHER: 480,
    PieceType.THUNDER: 490,
    # 巡从 420 降到 300：`_patrol` 禁掉竖移后，它的可达格数腰斩（只剩横向 6 个空点），
    # 420 会让 AI 拿它当"半个车"去换，评估与走法彻底脱节。
    # **不要顺手降到 260 以下**：`_bias` 里 `VALUES[type] >= VALUES[PATROL]` 兼作
    # "是否值得跑一次 SEE" 的阈值，降到 260 会把象（260）新纳入 SEE，白拖慢搜索。
    PieceType.PATROL: 300,
}

MOBILE_PIECES = {
    PieceType.ROOK,
    PieceType.HORSE,
    PieceType.CANNON,
    PieceType.GUARD,
    PieceType.ARCHER,
    PieceType.THUNDER,
    PieceType.PATROL,
}

CENTRAL_WEIGHTS = {
    PieceType.KING: -1.0,
    PieceType.ROOK: 1.4,
    PieceType.CANNON: 1.8,
    PieceType.HORSE: 2.8,
    PieceType.ELEPHANT: 0.8,
    PieceType.ADVISOR: 0.5,
    PieceType.PAWN: 1.4,
    PieceType.GUARD: 1.7,
    PieceType.ARCHER: 1.8,
    PieceType.THUNDER: 2.4,
    PieceType.PATROL: 1.2,
}

# A pool ("captured") piece is not lost material: it parks in its owner's pool,
# where a pawn promoting on the last rank can become it (rules.py:96-104) and a
# dead pawn can be revived out of it (game.py:167-169). `_evaluate` used to sum
# the board only, so a capture read as -VALUE and a promotion as +VALUE, i.e.
# every pool-relevant move was over-rated by exactly one VALUE. Mirroring the
# pool half of that ledger at full weight is therefore the fix, not a tuning knob.
POOL_PROMOTION_TYPES = frozenset(VALUES) - {PieceType.PAWN, PieceType.KING}
# `RESTORE_PAWN_LIMIT` (the 7-pawn cap) is imported from `.game` above so the
# AI's pool valuation and `Game.resurrect_pawn` share one rule definition.


def evaluation_key(rules: RulesEngine, state: GameState) -> str:
    """Pool-aware cache key for every AI memo (TT, evaluation, SEE).

    This is exactly `RulesEngine.position_key`, which already carries the capture
    pool (see `rules.py::pool_signature`): the pool decides which promotion moves
    are legal, so two positions that differ only in the pool are not
    interchangeable and must not share a cached score. Kept as a named helper so
    the AI's intent -- "this key has to see the pool" -- stays greppable at the
    call sites instead of reading as a bare position key.
    """
    return rules.position_key(state)


class SearchTimeout(Exception):
    pass


class Bound(StrEnum):
    EXACT = "exact"
    LOWER = "lower"
    UPPER = "upper"


@dataclass(frozen=True, slots=True)
class TTEntry:
    depth: int
    score: float
    bound: Bound
    best_move: Move | None


class ChessAI:
    def __init__(
        self,
        difficulty: Difficulty | str = Difficulty.MEDIUM,
        seed: int | None = None,
        config: SearchConfig | None = None,
        time_scale: float | None = None,
    ):
        # `config` 是实例级搜索参数（标定/A-B 用），构造时解析一次；`time_scale` 是
        # 预算缩放（与搜索参数正交）。`self._config` 是唯一读取点 —— 任何一处回头读
        # `CONFIGS` 都会让注入半失效。
        self.difficulty = (
            difficulty if isinstance(difficulty, Difficulty) else Difficulty(normalize_difficulty(difficulty))
        )
        self._config: SearchConfig = config if config is not None else CONFIGS[self.difficulty]
        self.time_scale = time_scale
        self.random = random.Random(seed)
        self.transposition: dict[str, TTEntry] = {}
        self.history: dict[tuple[PieceType, int, int], int] = {}
        self.killers: dict[int, list[Move]] = {}
        self.evaluation_cache: dict[tuple[str, Color], float] = {}
        # `in_check` 记忆化：`_evaluate` 对同一局面会分别按红/黑求值（评估缓存按 color 分键，
        # 互相救不了），两次求值要问的是同两组「王是否被将」。实测一次 5s 搜索里
        # 21%（36/172）的 `in_check` 调用是重复的。
        # 键含 `evaluation_key`，不跨局面复用；容量与评估缓存一致，超限整表清空。
        self.in_check_memo: dict[tuple[str, Color], bool] = {}
        self.see_cache: dict[tuple[str, str], int] = {}
        self.principal_move: Move | None = None
        # (score, move, truncated)：第三项是「该根着法这一轮的分数是否残缺」，
        # 只用于告诉迭代加深「别拿它当窗口中心」，**不参与判罚**（判罚仍看候选是否为 None）。
        self.root_scores: list[tuple[float, Move, bool]] = []
        self.completed_depth = 0
        self.nodes = 0
        self.qnodes = 0
        self.see_calls = 0
        self.null_prunes = 0
        self.lmr_researches = 0
        self._active_deadline = math.inf
        self._active_cancel: threading.Event | None = None
        self.quiescence_depth = self._config.quiescence_depth
        # 被 QUIESCENCE_NODE_LIMIT 截断的次数（诊断/测试用，不进 UI）
        self.quiescence_truncations = 0
        self.no_candidate_fallbacks = 0
        # 截断归因：`bound_reason`（本手被截断，不论 depth）/ `zero_depth_reason`
        # （一手都没搜完）。benchmark 用它们分账"这批数据能不能引用"。
        self.bound_reason: str | None = None
        self.zero_depth_reason: str | None = None
        self._timeout_reason: str | None = None
        self.zero_depth_moves = 0
        self._qnode_base = 0
        self._qnode_truncated = False

    def choose_move(self, game: Game, cancel: threading.Event | None = None) -> Move | None:
        cfg = self._config
        time_scale = resolve_time_scale(self.time_scale, os.getenv("AI_TIME_SCALE"))
        self.bound_reason = None
        self.zero_depth_reason = None
        self._timeout_reason = None
        # 计数是**每次调用**的口径（benchmark 汇总时才累加），不能实例累计。
        self.zero_depth_moves = 0
        # MCTS 已从产品档位下线：`MASTER` 只是旧配置兼容名（`CONFIGS[MASTER]`
        # 指向 HARD，同一对象），这里不再分派到 `core/mcts.py`。代码与
        # `tests/test_mcts_integration.py` 保留，仅作研究/基准路径显式构造。
        deadline = time.monotonic() + cfg.time_limit * time_scale
        self._active_deadline = deadline
        self._active_cancel = cancel
        self.transposition.clear()
        self.history.clear()
        self.killers.clear()
        self.evaluation_cache.clear()
        self.in_check_memo.clear()
        self.see_cache.clear()
        self.principal_move = None
        self.root_scores = []
        self.completed_depth = 0
        self.nodes = self.qnodes = self.see_calls = 0
        self.null_prunes = self.lmr_researches = 0
        self.quiescence_truncations = 0
        self.no_candidate_fallbacks = 0
        self._prefix_calls = 0
        legal = game.rules.legal_moves(game.state)
        if not legal:
            return None
        best = legal[0]
        previous_score: float | None = None
        try:
            initial_order = self._order(game, legal, deadline=deadline, cancel=cancel)
            initial_order = self._partition_by_bias(game, initial_order, cfg.root_limit, deadline, cancel)
            best = initial_order[0]
            search_moves = initial_order[: cfg.root_limit]
            for depth in range(1, cfg.depth + 1):
                if previous_score is None:
                    score, candidate = self._root(game, search_moves, depth, deadline, cancel)
                else:
                    window = 70 + depth * 10
                    low, high = previous_score - window, previous_score + window
                    score, candidate = self._root(game, search_moves, depth, deadline, cancel, low, high)
                    if score <= low or score >= high:
                        score, candidate = self._root(game, search_moves, depth, deadline, cancel)
                if candidate is not None:
                    best = candidate
                    self.principal_move = candidate
                    self.completed_depth = depth
                    # 窗口中心只允许被**完整分**推动：残缺分只是下界，拿它当
                    # `previous_score` 会把 aspiration 窗口带偏 → 更多 re-search →
                    # 预算被吃 → 深度更低 → 更多残缺分（正反馈）。
                    complete = [item[0] for item in self.root_scores if not item[2]]
                    previous_score = max(complete) if complete else None
                    search_moves = [item[1] for item in self.root_scores[: cfg.root_limit]]
                if abs(score) >= VALUES[PieceType.KING]:
                    break
                if self.bound_reason is not None:
                    break
        except SearchTimeout:
            # 理由在抛点写入（`_guard` → wall/cancel、节点预算 → nodes）。
            self.bound_reason = self._timeout_reason or "wall"
        if self.completed_depth == 0:
            self.zero_depth_moves += 1
            self.zero_depth_reason = self.bound_reason
        self._active_deadline = math.inf
        self._active_cancel = None
        weaker = self._sample_weaker(game, cfg)
        return best if weaker is None else weaker

    def _sampling_blocked(self, game: Game, cfg: SearchConfig) -> bool:
        """五条「必须走最强着」的闸门 —— 任一成立就不许取样。

        这几条都是为了消除"明明能赢却故意不赢"的观感。被将军不走应着、一步制胜不杀、
        有子不吃，这三种是新手最先察觉的"AI 在放水"，比"走得弱"更容易被识破。
        """
        if not cfg.randomness or len(self.root_scores) < 2:
            return True
        if self.completed_depth == 0:
            # 本轮没算完，`best` 只是排序首着，分数不可信 → 不许拿它做比较
            return True
        if game.rules.in_check(game.state, game.state.turn):
            return True
        if self.root_scores[0][0] >= VALUES[PieceType.KING]:
            return True
        return self._best_is_clean_capture(game)

    def _best_is_clean_capture(self, game: Game) -> bool:
        """最佳着是"净赚一个兵以上"的吃子时不许换着。

        门槛**沿用设计定稿的一个兵（120）**，不改成炮：曾实测过"提高到 500 能让
        名义概率重新兑现"（中局约半数局面都有白吃一个兵，会挡掉约一半取样），
        但"有子不吃"是设计明确要避免的观感，这条属于产品口径，不在标定时擅自改。
        代价是实测弱化率会被稀释到名义值的一半左右，已记入已知限制。
        """
        best_move = self.root_scores[0][1]
        if game.state.piece_at(best_move.target) is None:
            return False
        return static_exchange_score(game, best_move, VALUES) >= VALUES[PieceType.PAWN]

    def _sample_weaker(self, game: Game, cfg: SearchConfig) -> Move | None:
        """按概率从"名次 2..N"里挑一手看似合理、但略差的着法。

        为什么不起选第 1 名：命中第 1 名等于没弱化，名义概率和实际弱化率会脱节。
        为什么吃子要过 SEE：弱档可以走次优，但不该白送子 —— 按着法粒度判，
        比"整局只在非吃子局面生效"更稳（后者会让弱档在乱战里突然满血，前后不一致本身更像机器）。
        """
        if self._sampling_blocked(game, cfg) or self.random.random() >= cfg.randomness:
            return None
        best_score = self.root_scores[0][0]
        pool: list[tuple[float, Move]] = []
        for score, move, truncated in self.root_scores[1 : cfg.candidate_count]:
            if truncated or best_score - score > cfg.sample_margin:
                continue
            if (
                game.state.piece_at(move.target) is not None
                and static_exchange_score(game, move, VALUES) < -VALUES[PieceType.PAWN]
            ):
                continue
            pool.append((score, move))
        if not pool:
            return None
        # **只在较差的那一半里挑**：候选窗口里同分等价着法经常占满（杀题局面尤甚），
        # 均匀取样会几乎总挑回等价着法 —— 名义概率兑现了，实际一步也没变弱。
        # 实测：均匀取样时平均分差只有 0–6cp，玩家体感等于没设这个档。
        pool.sort(key=lambda item: item[0])
        floor = max(1, len(pool) // 2)
        return self.random.choice([move for _, move in pool[:floor]])

    def _root(
        self,
        game: Game,
        moves: list[Move],
        depth: int,
        deadline: float,
        cancel: threading.Event | None,
        alpha: float = -math.inf,
        beta: float = math.inf,
    ) -> tuple[float, Move | None]:
        if self.principal_move is None:
            # M1：第一层迭代的 `moves` 已由 choose_move 排好（同 `_order` + 同稳定分区），
            # 再排一次是纯重复。沿用入参顺序；后续层才重排（principal 已产生）。
            ordered = list(moves)
        else:
            ordered = self._order(game, moves, self.principal_move, deadline=deadline, cancel=cancel)
            ordered = sorted(
                ordered,
                key=lambda move: self._root_bias(game, move, deadline, cancel) < -100,
            )
        best_score, best_move = -math.inf, None
        scores: list[tuple[float, Move, bool]] = []
        try:
            for move in ordered:
                self._guard(deadline, cancel)
                # `_qnode_truncated` 是**粘性**的：本根着法的任意一次静态搜索被截断，
                # 就把整个根着法标记为"分数不完整"，不参与夺标。
                self._qnode_truncated = False
                child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options, game.setup)
                score = -self._search(child, depth - 1, -beta, -alpha, deadline, cancel, 1)
                truncated = self._qnode_truncated
                scores.append((score, move, truncated))
                # 判罚逻辑**不动**：被截断的根着法只是"不能夺标"（见下），
                # 但它的分数也**不许**抬高 alpha / 触发 beta 截断 —— 否则一个偏高的
                # 残缺分会让后续更好的着法被提前切掉，而且从选点上看不出来。
                if truncated:
                    if score > best_score:
                        best_score = score
                else:
                    if score > best_score:
                        best_score, best_move = score, move
                    alpha = max(alpha, score)
                    if alpha >= beta:
                        break
        except SearchTimeout:
            # 修法 1：根循环**已完成的**根着法不许因为后续超时而全丢。
            # 只要至少一个根着法跑完，就沿用原规则（残缺根不夺标）返回当前最优；
            # 一个都没跑完才交给外层（此时 completed_depth 仍为 0）。
            # 只对 wall 保留局部结果：`max_nodes` 是显式节点预算，既有口径是
            # "预算耗尽 → 本层不算完成"（`test_ai_runtime_config` 钉住），不能顺手改。
            if not scores or self._timeout_reason != "wall":
                raise
            # 记下截断原因：外层据此停止继续加深（否则会用已过期的 deadline 再跑一层）。
            self.bound_reason = "wall"
            self.root_scores = sorted(scores, key=lambda item: item[0], reverse=True)
            if best_move is not None:
                return best_score, best_move
            self.no_candidate_fallbacks += 1
            return self.root_scores[0][0], ordered[0]
        self.root_scores = sorted(scores, key=lambda item: item[0], reverse=True)
        if best_move is None and ordered:
            # 全部根着法都被截断：退回排序首着（= 初始序的第一手），不拿残缺分数赌。
            # 这条兜底不该经常发生 —— 打点出来，事后才有线索（否则只表现为"某步下得怪"）。
            self.no_candidate_fallbacks += 1
            return self.root_scores[0][0] if self.root_scores else -math.inf, ordered[0]
        return best_score, best_move

    def _search(
        self,
        game: Game,
        depth: int,
        alpha: float,
        beta: float,
        deadline: float,
        cancel: threading.Event | None,
        ply: int,
        allow_null: bool = True,
    ) -> float:
        self._guard(deadline, cancel)
        self.nodes += 1
        # `max_nodes=N` 允许 N 个节点跑完；第 N+1 个进入时才截断。
        if self._config.max_nodes is not None and self.nodes > self._config.max_nodes:
            self._timeout_reason = "nodes"
            raise SearchTimeout
        key = evaluation_key(game.rules, game.state)
        original_alpha = alpha
        original_beta = beta
        entry = self.transposition.get(key)
        if entry and entry.depth >= depth:
            if entry.bound is Bound.EXACT:
                return entry.score
            if entry.bound is Bound.LOWER:
                alpha = max(alpha, entry.score)
            else:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score

        if depth <= 0:
            # 每次**一次静态搜索**开始时归位计数：cap 限制的是这一次静态搜索的节点数，
            # 不是该根着法整棵深度树的累计 —— 后者会随"尝试更深的深度"线性上涨，
            # 根本不能当"吃子链跑飞"的信号（medium 明明 depth=1 也会报 trunc=12 就是这个）。
            self._qnode_base = self.qnodes
            return self._quiescence(game, alpha, beta, deadline, cancel, ply, self.quiescence_depth)
        in_check = game.rules.in_check(game.state, game.state.turn)
        if allow_null and depth >= 4 and not in_check and math.isfinite(beta) and self._can_null_move(game):
            null_state = game.state.clone()
            null_state.turn = null_state.turn.opponent
            null_game = Game.from_state(null_state, game.options, game.setup)
            reduction = 2 + depth // 4
            score = -self._search(
                null_game, max(0, depth - 1 - reduction), -beta, -beta + 1, deadline, cancel, ply + 1, False
            )
            if score >= beta:
                self.null_prunes += 1
                return beta
        moves = game.rules.legal_moves(game.state)
        if not moves:
            return -VALUES[PieceType.KING] + ply

        value = -math.inf
        best_move = None
        ordered = self._order(game, moves, entry.best_move if entry else None, ply, deadline, cancel)
        if not in_check:
            base_limit = self._config.branch_limit
            ordered = ordered[: base_limit + max(0, 4 - depth) * 2]
        for index, move in enumerate(ordered):
            self._guard(deadline, cancel)
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options, game.setup)
            capture = self._capture_value(game, move)
            gives_check = game.rules.in_check(child.state, child.state.turn)
            reduction = 0
            if (
                index >= 4
                and depth >= 3
                and not in_check
                and not capture
                and move.promotion is None
                and not gives_check
                and math.isfinite(alpha)
            ):
                reduction = min(depth - 2, 1 + (index - 4) // 8)
            if reduction:
                score = -self._search(child, depth - 1 - reduction, -alpha - 1, -alpha, deadline, cancel, ply + 1)
                if score > alpha:
                    self.lmr_researches += 1
                    score = -self._search(child, depth - 1, -beta, -alpha, deadline, cancel, ply + 1)
            else:
                score = -self._search(child, depth - 1, -beta, -alpha, deadline, cancel, ply + 1)
            if score > value:
                value, best_move = score, move
            alpha = max(alpha, value)
            if alpha >= beta:
                moving = game.state.piece_at(move.source)
                if moving and game.state.piece_at(move.target) is None:
                    history_key = (moving.type, move.target.row, move.target.col)
                    self.history[history_key] = self.history.get(history_key, 0) + depth * depth
                    killers = self.killers.setdefault(ply, [])
                    if move not in killers:
                        killers.insert(0, move)
                        del killers[2:]
                break

        bound = Bound.EXACT
        if value <= original_alpha:
            bound = Bound.UPPER
        elif value >= original_beta:
            bound = Bound.LOWER
        previous = self.transposition.get(key)
        if previous is None or depth >= previous.depth:
            self.transposition[key] = TTEntry(depth, value, bound, best_move)
        return value

    def _quiescence(
        self,
        game: Game,
        alpha: float,
        beta: float,
        deadline: float,
        cancel: threading.Event | None,
        ply: int,
        remaining: int,
        legal: list[Move] | None = None,
    ) -> float:
        self._guard(deadline, cancel)
        self.qnodes += 1
        in_check = game.rules.in_check(game.state, game.state.turn)
        stand_pat = self._evaluate(game, game.state.turn)
        # 节点上限按**单次静态搜索**计（`_qnode_base` 在 `_search` 的叶子处归位，
        # 递归调用共享同一个基数）：到顶就退回静态分，并把**本根着法**标记为
        # "分数不完整"（粘性），上层据此不让它夺标。
        if self.qnodes - self._qnode_base > QUIESCENCE_NODE_LIMIT:
            self.quiescence_truncations += 1
            self._qnode_truncated = True
            return stand_pat
        if remaining <= 0:
            return stand_pat
        if not in_check:
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)

        moves = (
            legal
            if legal is not None
            else (game.rules.legal_moves(game.state) if in_check else self._tactical_moves(game, deadline, cancel))
        )
        if in_check and not moves:
            return -VALUES[PieceType.KING] + ply
        tactical = (
            moves
            if in_check
            else [
                move
                for move in moves
                if move.promotion is not None
                or (self._capture_value(game, move) > 0 and self._see_score(game, move) >= 0)
            ]
        )
        ordered = self._order(game, tactical, ply=ply, deadline=deadline, cancel=cancel)
        if not in_check:
            ordered = ordered[: max(6, self._config.branch_limit)]
        for move in ordered:
            self._guard(deadline, cancel)
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options, game.setup)
            score = -self._quiescence(child, -beta, -alpha, deadline, cancel, ply + 1, remaining - 1)
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _tactical_moves(self, game: Game, deadline: float, cancel: threading.Event | None) -> list[Move]:
        state = game.state
        enemies = [piece for piece in state.pieces if piece.color is state.turn.opponent]
        tactical: list[Move] = []
        seen: set[Move] = set()
        for moving in state.pieces:
            self._guard(deadline, cancel)
            if moving.color is not state.turn:
                continue
            for target in enemies:
                if not self._attack_geometry(moving, target):
                    continue
                move = Move(moving.position, target.position)
                if move not in seen and game.rules.is_legal(state, move):
                    tactical.append(move)
                    seen.add(move)
            if moving.type is PieceType.PAWN and game.options.pawn_promotion:
                final_row = 0 if moving.color is Color.RED else game.profile.rows - 1
                # Single source for the set (was hand-rolled here). It stays an
                # unordered set on purpose: this list feeds `_order`'s *stable*
                # sort and is then truncated, so switching to the sorted
                # `promotion_types` would silently reshuffle tied promotions and
                # change the search. Same elements, same insertion order => same
                # iteration order as before.
                promotion_types = game.rules.promotable_types(state, moving.color)
                for col in range(game.profile.cols):
                    for promotion in promotion_types:
                        move = Move(moving.position, Position(final_row, col), promotion)
                        if move not in seen and game.rules.is_legal(state, move):
                            tactical.append(move)
                            seen.add(move)
        return tactical

    def _evaluate(self, game: Game, color: Color) -> float:
        cache_key = (evaluation_key(game.rules, game.state), color)
        cached = self.evaluation_cache.get(cache_key)
        if cached is not None:
            return cached
        score = 0.0
        phase = self._game_phase(game)
        center_r, center_c = (game.profile.rows - 1) / 2, (game.profile.cols - 1) / 2
        for piece in game.state.pieces:
            sign = 1 if piece.color is color else -1
            central = max(
                0,
                min(game.profile.rows, game.profile.cols) / 2
                - abs(piece.position.row - center_r)
                - abs(piece.position.col - center_c),
            )
            positional = central * CENTRAL_WEIGHTS[piece.type] * (0.75 + phase * 0.25)
            if piece.type is PieceType.PAWN:
                advance = (
                    piece.position.row if piece.color is Color.BLACK else game.profile.rows - 1 - piece.position.row
                )
                positional += advance * (5 + (1 - phase) * 3)
                if advance > (game.profile.rows - 1) / 2:
                    positional += 22 + (1 - phase) * 18
            elif piece.type in MOBILE_PIECES and self._is_developed(game, piece):
                positional += 13
            if piece.type is PieceType.KING:
                if phase >= 0.45:
                    positional += 36 if game.rules.palace(piece.color, piece.position) else -24
                    positional += self._king_cover(game, piece.color) * 9
                else:
                    positional += central * 1.8
            score += sign * (VALUES[piece.type] + positional)

        # Material parked in each side's pool is a live conversion option, and the
        # board-only sum above silently priced it at zero (P0-F). The pool's owner
        # is the one who benefits, so its value is added and the opponent's
        # subtracted -- symmetric with the board term's `sign` above.
        score += self._pool_value(game, color) - self._pool_value(game, color.opponent)

        own_attacks, own_pressure = self._activity_score(game, color)
        enemy_attacks, enemy_pressure = self._activity_score(game, color.opponent)
        score += (own_attacks - enemy_attacks) * 5
        score += (own_pressure - enemy_pressure) * 0.18
        score += (self._mobility_score(game, color) - self._mobility_score(game, color.opponent)) * (0.8 + phase * 0.5)
        score += self._king_safety(game, color, phase)
        score -= self._king_safety(game, color.opponent, phase)
        evaluation = cache_key[0]
        if self._in_check(game, evaluation, color.opponent):
            score += 150
        if self._in_check(game, evaluation, color):
            score -= 210
        if len(self.evaluation_cache) >= 50_000:
            self.evaluation_cache.clear()
        self.evaluation_cache[cache_key] = score
        return score

    def _in_check(self, game: Game, evaluation: str, color: Color) -> bool:
        """`rules.in_check` 的记忆化版本；键 = (evaluation_key, color)，**不跨局面复用**。"""
        key = (evaluation, color)
        cached = self.in_check_memo.get(key)
        if cached is not None:
            return cached
        value = game.rules.in_check(game.state, color)
        if len(self.in_check_memo) >= 50_000:
            self.in_check_memo.clear()
        self.in_check_memo[key] = value
        return value

    def _pool_value(self, game: Game, color: Color) -> float:
        """Material `color` still holds in its own pool (`state.captured[color]`).

        Full `VALUES` weight, no phase weighting: this restores the half of the
        ledger `_evaluate` was missing, it is not a calibration knob. Both gates
        and the promotion filter mirror the rules exactly, so the term only counts
        conversions the ruleset actually allows.
        """
        pool = game.state.captured[color]
        enabled = game.rules.enabled_piece_types
        total = 0.0
        if game.options.pawn_promotion:
            # Same filter as rules.py:96-104: promotion targets exclude PAWN/KING
            # and must be enabled by the profile. (A captured KING can sit in the
            # pool; counting it would blow the score up by VALUES[KING].)
            total += sum(
                VALUES[piece.type] for piece in pool if piece.type in POOL_PROMOTION_TYPES and piece.type in enabled
            )
        if game.options.pawn_resurrection:
            # Only pawns can be revived (game.py:167-169), never above the 7-pawn
            # cap, so the dead pawns beyond that cap are worth nothing.
            dead_pawns = sum(1 for piece in pool if piece.type is PieceType.PAWN)
            fielded = sum(1 for piece in game.state.pieces if piece.type is PieceType.PAWN and piece.color is color)
            total += min(dead_pawns, max(0, RESTORE_PAWN_LIMIT - fielded)) * VALUES[PieceType.PAWN]
        return total

    def _game_phase(self, game: Game) -> float:
        current = sum(
            VALUES[piece.type] for piece in game.state.pieces if piece.type not in {PieceType.KING, PieceType.PAWN}
        )
        initial = sum(
            VALUES[spec.type]
            for spec in game.profile.pieces
            if spec.type not in {PieceType.KING, PieceType.PAWN} and game.options.piece_enabled(spec.type)
        )
        return min(1.0, current / max(1, initial))

    def _mobility_score(self, game: Game, color: Color) -> int:
        score = 0
        weights = {
            PieceType.ROOK: 2,
            PieceType.CANNON: 2,
            PieceType.HORSE: 3,
            PieceType.ARCHER: 2,
            PieceType.THUNDER: 2,
            PieceType.PAWN: 1,
        }
        for piece in game.state.pieces:
            if piece.color is not color:
                continue
            weight = weights.get(piece.type, 1)
            for target in self._mobility_targets(game, piece):
                occupant = game.state.piece_at(target)
                if occupant and occupant.color is color:
                    continue
                score += weight
        return score

    @staticmethod
    def _mobility_targets(game: Game, piece: Piece) -> list[Position]:
        row, col = piece.position.row, piece.position.col
        candidates: set[Position] = set()
        if piece.type in {PieceType.ROOK, PieceType.CANNON, PieceType.THUNDER}:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for delta in range(1, max(game.profile.rows, game.profile.cols)):
                    target = Position(row + dr * delta, col + dc * delta)
                    if not (0 <= target.row < game.profile.rows and 0 <= target.col < game.profile.cols):
                        break
                    candidates.add(target)
                    if game.state.piece_at(target):
                        break
        if piece.type in {PieceType.ARCHER, PieceType.THUNDER}:
            max_distance = (
                3
                if (piece.type is PieceType.ARCHER and game.options.archer_enhanced_mode)
                else max(game.profile.rows, game.profile.cols)
            )
            for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                for delta in range(1, max_distance + 1):
                    target = Position(row + dr * delta, col + dc * delta)
                    if not (0 <= target.row < game.profile.rows and 0 <= target.col < game.profile.cols):
                        break
                    candidates.add(target)
                    if game.state.piece_at(target):
                        break
        offsets = {
            PieceType.HORSE: (
                (2, 1),
                (2, -1),
                (-2, 1),
                (-2, -1),
                (1, 2),
                (1, -2),
                (-1, 2),
                (-1, -2),
                (3, 0),
                (-3, 0),
                (0, 3),
                (0, -3),
            ),
            PieceType.ELEPHANT: ((2, 2), (2, -2), (-2, 2), (-2, -2), (2, 0), (-2, 0), (0, 2), (0, -2)),
            PieceType.ADVISOR: ((1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)),
            PieceType.KING: ((1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)),
            PieceType.PAWN: ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (3, 0), (-3, 0)),
            PieceType.GUARD: (
                (2, 0),
                (-2, 0),
                (0, 2),
                (0, -2),
                (2, 2),
                (2, -2),
                (-2, 2),
                (-2, -2),
                (3, 0),
                (-3, 0),
                (0, 3),
                (0, -3),
                (3, 3),
                (3, -3),
                (-3, 3),
                (-3, -3),
            ),
            PieceType.PATROL: (
                (0, 2),
                (0, -2),
                (0, 4),
                (0, -4),
                (0, 6),
                (0, -6),
                (0, 8),
                (0, -8),
                (0, 10),
                (0, -10),
                (0, 12),
                (0, -12),
            ),
        }
        candidates.update(Position(row + dr, col + dc) for dr, dc in offsets.get(piece.type, ()))
        return [
            target
            for target in candidates
            if 0 <= target.row < game.profile.rows and 0 <= target.col < game.profile.cols
        ]

    def _king_safety(self, game: Game, color: Color, phase: float) -> float:
        king = next(
            (piece for piece in game.state.pieces if piece.color is color and piece.type is PieceType.KING), None
        )
        if king is None:
            return -VALUES[PieceType.KING]
        score: float = self._king_cover(game, color) * (12 if phase >= 0.45 else 5)
        if game.rules.palace(color, king.position):
            score += 25 * phase
        for enemy in game.state.pieces:
            if enemy.color is color:
                continue
            distance = max(abs(enemy.position.row - king.position.row), abs(enemy.position.col - king.position.col))
            if distance <= 3:
                score -= (4 - distance) * min(40, VALUES[enemy.type] / 20)
        return score

    def _can_null_move(self, game: Game) -> bool:
        if game.options.pawn_resurrection or self._game_phase(game) < 0.35:
            return False
        return (
            sum(piece.color is game.state.turn and piece.type is not PieceType.KING for piece in game.state.pieces) >= 4
        )

    def _activity_score(self, game: Game, color: Color) -> tuple[int, float]:
        probe = game.state if game.state.turn is color else replace(game.state, turn=color)
        attacks = 0
        pressure = 0.0
        allies = [piece for piece in probe.pieces if piece.color is color]
        enemies = [piece for piece in probe.pieces if piece.color is color.opponent]
        for moving in allies:
            for target in enemies:
                if not self._attack_geometry(moving, target):
                    continue
                if not game.rules.pseudo_legal(probe, Move(moving.position, target.position)):
                    continue
                attacks += 1
                capture = VALUES[target.type]
                attacker = VALUES[moving.type]
                pressure += capture + max(0, capture - attacker) * 0.35
        return attacks, pressure

    @staticmethod
    def _attack_geometry(moving: Piece, target: Piece) -> bool:
        dr = abs(target.position.row - moving.position.row)
        dc = abs(target.position.col - moving.position.col)
        if moving.type in {PieceType.ROOK, PieceType.CANNON}:
            return dr == 0 or dc == 0
        if moving.type is PieceType.HORSE:
            return (dr, dc) in {(2, 1), (1, 2), (3, 0), (0, 3)}
        if moving.type is PieceType.ELEPHANT:
            return (dr, dc) in {(2, 2), (2, 0), (0, 2)}
        if moving.type in {PieceType.ADVISOR, PieceType.KING}:
            return max(dr, dc) == 1
        if moving.type is PieceType.PAWN:
            return dr + dc == 1
        if moving.type is PieceType.ARCHER:
            return dr == dc
        if moving.type is PieceType.THUNDER:
            return dr == 0 or dc == 0 or dr == dc
        if moving.type is PieceType.PATROL:
            return dr == 0 and dc == 2
        if moving.type is PieceType.GUARD:
            return dr == 0 or dc == 0 or dr == dc
        return False

    def _is_developed(self, game: Game, piece: Piece) -> bool:
        return not any(
            spec.color is piece.color
            and spec.type is piece.type
            and spec.row == piece.position.row
            and spec.col == piece.position.col
            for spec in game.profile.pieces
        )

    @staticmethod
    def _king_cover(game: Game, color: Color) -> int:
        king = next(
            (piece for piece in game.state.pieces if piece.color is color and piece.type is PieceType.KING), None
        )
        if king is None:
            return 0
        return sum(
            piece.color is color
            and piece is not king
            and abs(piece.position.row - king.position.row) <= 1
            and abs(piece.position.col - king.position.col) <= 1
            for piece in game.state.pieces
        )

    def _partition_by_bias(
        self,
        game: Game,
        moves: list[Move],
        limit: int,
        deadline: float,
        cancel: threading.Event | None,
    ) -> list[Move]:
        """M2：稳定分区 + 按需截断；输出与「全扫后 sorted(key=bias<-100)」前缀一致。

        未降级（bias ≥ -100）按原序在前，降级在后；凑够 `limit` 个未降级即可停，
        不必扫完全部 90–115 个着法。
        """
        primary: list[Move] = []
        secondary: list[Move] = []
        for move in moves:
            if self._root_bias(game, move, deadline, cancel) < -100:
                secondary.append(move)
            else:
                primary.append(move)
                if len(primary) >= limit:
                    return primary
        return (primary + secondary)[:limit]

    def _root_bias(
        self,
        game: Game,
        move: Move,
        deadline: float | None = None,
        cancel: threading.Event | None = None,
    ) -> float:
        if deadline is not None:
            self._prefix_calls += 1
            if self._prefix_calls % 16 == 0:
                self._guard(deadline, cancel)
        bias = 0.0
        moving = game.state.piece_at(move.source)
        if moving is None:
            return bias
        previous = next((record for record in reversed(game.state.history) if record.color is moving.color), None)
        if previous and previous.move.source == move.target and previous.move.target == move.source:
            bias -= 150
            if not self._capture_value(game, move):
                bias -= 45
        if self._is_developed(game, moving):
            initial_target = any(
                spec.color is moving.color
                and spec.type is moving.type
                and spec.row == move.target.row
                and spec.col == move.target.col
                for spec in game.profile.pieces
            )
            if initial_target:
                bias -= 28
        if self._capture_value(game, move) or VALUES[moving.type] >= VALUES[PieceType.PATROL]:
            exchange = self._see_score(game, move)
            if exchange < 0:
                bias += exchange * 2 - 600
        return bias

    def _capture_value(self, game: Game, move: Move) -> int:
        return sum(VALUES[piece.type] for piece in game.rules.captured_by_move(game.state, move))

    def _see_score(self, game: Game, move: Move) -> int:
        key = (evaluation_key(game.rules, game.state), move.key())
        cached = self.see_cache.get(key)
        if cached is not None:
            return cached
        self.see_calls += 1
        guard = None
        if math.isfinite(self._active_deadline):

            def guard() -> None:
                return self._guard(self._active_deadline, self._active_cancel)

        score = static_exchange_score(game, move, VALUES, guard)
        if len(self.see_cache) >= 30_000:
            self.see_cache.clear()
        self.see_cache[key] = score
        return score

    def _order(
        self,
        game: Game,
        moves: list[Move],
        preferred: Move | None = None,
        ply: int = 0,
        deadline: float | None = None,
        cancel: threading.Event | None = None,
    ) -> list[Move]:
        calls = 0

        def score(move: Move) -> int:
            nonlocal calls
            calls += 1
            if deadline is not None and calls % 16 == 0:
                self._guard(deadline, cancel)
            if preferred == move:
                return 10_000_000
            moving = game.state.piece_at(move.source)
            capture = self._capture_value(game, move)
            value = capture * 16 - (VALUES[moving.type] if moving and capture else 0)
            if moving:
                if capture:
                    exchange = self._see_score(game, move)
                    if exchange < 0:
                        value += exchange * 18 - 6_000
                    elif capture:
                        value += exchange * 8 + 2_000
                value += self.history.get((moving.type, move.target.row, move.target.col), 0)
                center_r = (game.profile.rows - 1) / 2
                center_c = (game.profile.cols - 1) / 2
                source_distance = abs(move.source.row - center_r) + abs(move.source.col - center_c)
                target_distance = abs(move.target.row - center_r) + abs(move.target.col - center_c)
                value += int((source_distance - target_distance) * CENTRAL_WEIGHTS[moving.type] * 18)
                if moving.type is PieceType.PAWN:
                    forward = -1 if moving.color is Color.RED else 1
                    value += (move.target.row - move.source.row) * forward * 32
                if not self._is_developed(game, moving):
                    leaves_initial = not any(
                        spec.color is moving.color
                        and spec.type is moving.type
                        and spec.row == move.target.row
                        and spec.col == move.target.col
                        for spec in game.profile.pieces
                    )
                    if leaves_initial and moving.type in MOBILE_PIECES:
                        value += 180
            killers = self.killers.get(ply, [])
            if move in killers:
                value += 4_000 - killers.index(move) * 500
            # 「这一步是否将军」只影响排序权重，但直接算要 `apply_unchecked` +
            # `in_check`（实测 0.50 ms/着、108 着 = 54 ms/次排序）。这里先用几何筛
            # 掉**不可能**将军的着法 —— 判据见 `_may_give_check`，保守到只会多算、不会漏算。
            if self._may_give_check(game, move):
                child = game.rules.apply_unchecked(game.state, move)
                if game.rules.in_check(child, child.turn):
                    value += 900
            return value

        return sorted(moves, key=score, reverse=True)

    # 车/炮/檑/射/尉/巡 走的是直线或对角线：只要目标格与敌王不在同一条线上，
    # 落子后就**不可能**攻击到王（这些兵种没有"跳过去打"的走法）。
    _LINE_PIECES = frozenset(
        {
            PieceType.ROOK,
            PieceType.CANNON,
            PieceType.THUNDER,
            PieceType.ARCHER,
            PieceType.GUARD,
            PieceType.PATROL,
        }
    )
    # 近战兵种的最大切比雪夫距离：王/仕/兵 1 格，相 2 格（田），马 2 格（日）。
    _LOCAL_REACH = {
        PieceType.KING: 1,
        PieceType.ADVISOR: 1,
        PieceType.PAWN: 1,
        PieceType.ELEPHANT: 2,
        PieceType.HORSE: 2,
    }

    @staticmethod
    def _aligned(a: Position, b: Position) -> bool:
        """同行 / 同列 / 同对角线。"""
        dr, dc = abs(a.row - b.row), abs(a.col - b.col)
        return dr == 0 or dc == 0 or dr == dc

    def _may_give_check(self, game: Game, move: Move) -> bool:
        """这一步**是否可能**将军（保守判据，只用来省掉无谓的 `in_check`）。

        能将军只有三条路：
        1. **移动的子自己**打到王：直线兵种要求目标格与王共线（行/列/斜）；
           近战兵种要求切比雪夫距离在步长内。
        2. **移开后露出**别的子：只有"源格原本挡在某个子与王的连线上"才可能，
           即 `_aligned(source, king)`。
        3. **特殊机制**：甲/刺的走法会额外移除第三枚子（可露出非源格连线），
           升变会换成另一步法 —— 这两类一律按"可能将军"处理。

        判据错只会多算（慢一点），不会漏算（改变排序正确性）。
        """
        king = next(
            (
                piece
                for piece in game.state.pieces
                if piece.type is PieceType.KING and piece.color is game.state.turn.opponent
            ),
            None,
        )
        if king is None:
            return True
        mover = game.state.piece_at(move.source)
        if mover is None or move.promotion is not None:
            return True
        if self._aligned(move.source, king.position):
            return True
        if mover.type in self._LINE_PIECES:
            return self._aligned(move.target, king.position)
        reach = self._LOCAL_REACH.get(mover.type)
        if reach is None:
            return True
        return abs(move.target.row - king.position.row) <= reach and abs(move.target.col - king.position.col) <= reach

    def _guard(self, deadline: float, cancel: threading.Event | None) -> None:
        # 记理由再抛：`choose_move` 用它把本手归到 wall / cancel / nodes。
        if cancel is not None and cancel.is_set():
            self._timeout_reason = "cancel"
            raise SearchTimeout
        if time.monotonic() >= deadline:
            self._timeout_reason = "wall"
            raise SearchTimeout


# ── 提和判定（来自 master 线；纯新增，不参与搜索）────────────────────────────
# `service/rooms.py` 的 AI 房提和会调用它；阈值单位是 `VALUES`（兵=120），
# `-150` ≈ 落后 1.25 个兵才接受和棋。
DRAW_ACCEPT_THRESHOLD = -150.0


def should_accept_draw(game: Game, color: Color) -> bool:
    """`color` 一方是否应当接受和棋：自评 ≤ 阈值（闭区间）才接受。"""
    score = ChessAI(Difficulty.BEGINNER)._evaluate(game, color)
    return score <= DRAW_ACCEPT_THRESHOLD
