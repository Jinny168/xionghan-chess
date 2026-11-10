"""标定三档的目标参数（**只读表**，不改 `core.ai.CONFIGS`）。

为什么单独一份、而不是直接读 `CONFIGS`：
- `CONFIGS` 的数值属于 S4-2b，尚未改；标定/测量要测的是**目标档位**，
  不能拿旧值当新档；
- 参数显式写在这里，任何人改它都必须连测试/报告一起改，不会被"运行期替换"静默带偏。

字段与 `SearchConfig` 一一对应；`cap` 是墙钟兜底（同时是文案秒数），
`max_nodes` 是主搜索节点预算（`None` = 不启用；数值由
`scripts/measure_node_budget.py` 实测反解后回填）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from xionghan_chess.core.ai import CONFIGS, PUBLIC_DIFFICULTIES, SearchConfig

_UNSET = object()


@dataclass(frozen=True, slots=True)
class Tier:
    depth: int
    cap: float
    randomness: float
    quiescence_depth: int
    candidate_count: int
    branch_limit: int
    root_limit: int
    max_nodes: int | None

    def config(self, *, cap: float | None = None, max_nodes: int | None | object = _UNSET) -> SearchConfig:
        """生成注入用配置。默认沿用表内 `max_nodes`；显式传 `None` 表示"关闭预算"。"""
        resolved_max = self.max_nodes if max_nodes is _UNSET else cast(int | None, max_nodes)
        return SearchConfig(
            depth=self.depth,
            time_limit=self.cap if cap is None else cap,
            randomness=self.randomness,
            quiescence_depth=self.quiescence_depth,
            candidate_count=self.candidate_count,
            branch_limit=self.branch_limit,
            root_limit=self.root_limit,
            max_nodes=resolved_max,
        )


TARGETS: dict[str, Tier] = {
    # 入门：d1 结构上恒 10 节点（root_limit 10），max_nodes 设了也不会触发。
    # cap 3.0：40 手冒烟 max 2.0008 ×1.5；玩家等待仍由中位 0.35s 决定。
    "beginner": Tier(1, 3.0, 0.30, 1, 3, 6, 10, None),
    # 中级：cap 30（40 手冒烟 max 14.63 ×2.05）；max_nodes 暂 None（中局无可靠测量）。
    "medium": Tier(2, 30.0, 0.0, 4, 1, 10, 18, None),
    # 高级：cap 120（按 medium 比例留 4×，未实测）；max_nodes 暂 None。
    "hard": Tier(3, 120.0, 0.0, 6, 1, 18, 18, None),
}

LEVELS: tuple[str, ...] = tuple(TARGETS)


def _product_tier(config: SearchConfig) -> Tier:
    """`SearchConfig` → 标定表行；逐字段搬运，不做任何换算/默认值猜测。"""
    return Tier(
        depth=config.depth,
        cap=config.time_limit,
        randomness=config.randomness,
        quiescence_depth=config.quiescence_depth,
        candidate_count=config.candidate_count,
        branch_limit=config.branch_limit,
        root_limit=config.root_limit,
        max_nodes=config.max_nodes,
    )


# 发布三档（从 `core.ai.CONFIGS` 逐字段派生）。标定默认测这一张表；
# `TARGETS` 是 S4-2b 的提案表，只保留给 `--tiers target` 复现历史测量。
PRODUCT_TIERS: dict[str, Tier] = {
    difficulty.value: _product_tier(CONFIGS[difficulty]) for difficulty in PUBLIC_DIFFICULTIES
}
PRODUCT_LEVELS: tuple[str, ...] = tuple(PRODUCT_TIERS)
