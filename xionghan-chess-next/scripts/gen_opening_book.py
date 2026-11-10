"""生成**标定开局书** —— 64 条确定性局面，落盘可逐字节重建。

## 为什么需要它

旧对局函数每局都 `Game(profile)`：50 局只有 25 个起点，而且全是初始局面。
同一开局被两档各下一遍，胜率里混着"谁更会走这一个开局"，n=50 的有效样本远小于 50。
开局书把"起点"变成显式输入：同一批局面、同一批颜色，换档位重跑才可比较。

## 口径（全部冻结，重跑逐字节相同）

- 生成器：`scripts/bench_roots.py::build_position`（确定性走子，不依赖时间受限搜索）；
- 范围：`profile=desktop_complete`，`seed ∈ [700, 731]` × `plies ∈ {6, 10}` = **64 条**；
- 指纹：`fp` 用 `RulesEngine.position_key`（`bench_roots.position_fingerprint` 的
  同一口径）—— `pieces/legal` 子数/合法着数相同也可能是不同局面，所以它们只作为
  **辅助显示**字段一起存，不能当唯一键；`fp` 只用于核对重建，对局时不消费；
- 写盘：`json.dumps(..., sort_keys=True, indent=2)` + 结尾一个 `\\n`，**无时间戳、
  无环境信息**，`newline="\\n"` 固定换行。`.gitattributes` 里对
  `benchmarks/openings/*.json` 标了 `-text`，避免 autocrlf 在检出时改写字节。

## 用法

    python scripts/gen_opening_book.py              # 生成/覆盖 calibration_book.json
    python scripts/gen_opening_book.py --check      # 只校验：与磁盘文件逐字节一致则 0

`--check` 会重建全部 64 条（本机约 30s），适合改动 `bench_roots` / 规则后跑一次。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_roots import build_position, position_fingerprint  # noqa: E402

from xionghan_chess.core.benchmark import Opening  # noqa: E402
from xionghan_chess.core.game import Game  # noqa: E402

FORMAT_VERSION = 1
DEFAULT_PROFILE = "desktop_complete"
DEFAULT_SEEDS = tuple(range(700, 732))
DEFAULT_PLIES = (6, 10)
DEFAULT_OUT = ROOT / "benchmarks" / "openings" / "calibration_book.json"
POLICY = "scripts/bench_roots.py::build_position"


def build_entries(
    profile: str = DEFAULT_PROFILE, seeds: tuple[int, ...] = DEFAULT_SEEDS, plies_list: tuple[int, ...] = DEFAULT_PLIES
) -> list[dict[str, object]]:
    """按 `(seed, plies)` 字典序生成条目 —— 顺序确定，不依赖遍历集合。"""
    entries: list[dict[str, object]] = []
    for seed in seeds:
        for plies in plies_list:
            game, _played = build_position(profile, seed, plies)
            entries.append(
                {
                    "profile": profile,
                    "seed": seed,
                    "plies": plies,
                    # 唯一键：position_key（含轮次/子力/阵亡池）。对局时不消费。
                    "fp": position_fingerprint(game),
                    # 辅助显示（人读快照用）：子数 / 合法着数。**不是**唯一指纹。
                    "pieces": len(game.state.pieces),
                    "legal": len(game.rules.legal_moves(game.state)),
                }
            )
    return entries


def generate_text(
    profile: str = DEFAULT_PROFILE, seeds: tuple[int, ...] = DEFAULT_SEEDS, plies_list: tuple[int, ...] = DEFAULT_PLIES
) -> str:
    """整份文件的文本（纯函数：同参同字节，无时间戳/无环境）。"""
    entries = build_entries(profile, seeds, plies_list)
    payload = {
        "format": FORMAT_VERSION,
        "policy": POLICY,
        "profile": profile,
        "seeds": [min(seeds), max(seeds)],
        "plies": list(plies_list),
        "count": len(entries),
        "openings": entries,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_book(
    path: Path = DEFAULT_OUT,
    profile: str = DEFAULT_PROFILE,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    plies_list: tuple[int, ...] = DEFAULT_PLIES,
) -> Path:
    """写盘：显式 `newline="\\n"`，Windows 上也不变成 CRLF。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_text(profile, seeds, plies_list), encoding="utf-8", newline="\n")
    return path


def load_book(path: Path = DEFAULT_OUT) -> list[Opening]:
    """读回开局书。`fp` 一并保留，调用方可自行核对。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        Opening(profile=item["profile"], seed=item["seed"], plies=item["plies"], fp=item.get("fp"))
        for item in payload["openings"]
    ]


def build_game(profile: str, seed: int, plies: int) -> Game:
    """`benchmark_match(position_builder=build_game)` 用的 Game 版生成器。"""
    return build_position(profile, seed, plies)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成标定开局书（确定性、可逐字节重建）")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--check", action="store_true", help="不写盘，只校验磁盘文件与重建结果逐字节一致（不一致返回 1）"
    )
    args = parser.parse_args(argv)

    target = Path(args.out)
    if args.check:
        if not target.exists():
            print(f"缺失：{target}")
            return 1
        # 按字节读，不做换行归一化 —— 判据就是"逐字节"。
        actual = target.read_bytes()
        expected = generate_text().encode("utf-8")
        if actual != expected:
            print(f"不一致：{target}（disk {len(actual)} B / rebuilt {len(expected)} B）")
            return 1
        print(f"一致：{target}（{len(actual)} B）")
        return 0

    written = write_book(target)
    text = written.read_text(encoding="utf-8")
    payload = json.loads(text)
    print(f"写出：{written}（{payload['count']} 条，{len(text.encode('utf-8'))} B）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
