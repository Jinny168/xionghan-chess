"""夹具局面快照的加载校验（**不跑搜索**）。

## 为什么只做"能加载 + 指纹对"

`tests/fixtures/positions/` 里放的是**负对照/正对照**用的冻结局面。它们的用途是
"判断加预算有没有用"，不是"必须通过"——所以这里只验两件最基础的事：

1. 快照能被反序列化成一个可用的 `Game`；
2. 实际 `pieces / legal` 与文件里声明的指纹一致。

**不跑搜索**：一次 medium 搜索 5s，把搜索放进单元测试会拖垮整个套件，也不是这条测试的职责。

**夹具必须确定性生成**，不要靠「自对弈 + seed」——搜索是时间受限的，同一 seed 换机器/换负载
就会走出不同局面（同名 L6 曾出现 62/129、62/85、62/105 三种指纹）。

目录为空时**跳过**（并用 `reason` 说明原因），这样在只有 README 的机器上套件仍然全绿；
一旦有人把 `dense_62_85.json` 之类的快照放进去，校验立刻生效。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import GameState

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "positions"
SNAPSHOTS = sorted(FIXTURES.glob("*.json")) if FIXTURES.is_dir() else []


def _load(path: Path) -> tuple[Game, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "state" in payload, f"{path.name} 缺少 state 字段"
    assert "fingerprint" in payload, f"{path.name} 缺少 fingerprint 字段（pieces/legal）"
    game = Game.from_state(GameState.from_dict(payload["state"]), None, None)
    return game, payload["fingerprint"]


@pytest.mark.skipif(not SNAPSHOTS, reason="tests/fixtures/positions/ 为空（尚无冻结局面）")
@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_snapshot_loads_and_matches_fingerprint(path: Path) -> None:
    game, fingerprint = _load(path)
    assert len(game.state.pieces) == fingerprint["pieces"], (
        f"{path.name} 的 pieces 与指纹不符：文件声明 {fingerprint['pieces']}，"
        f"实际 {len(game.state.pieces)}")
    assert len(game.rules.legal_moves(game.state)) == fingerprint["legal"], (
        f"{path.name} 的 legal 与指纹不符：文件声明 {fingerprint['legal']}，"
        f"实际 {len(game.rules.legal_moves(game.state))}")
