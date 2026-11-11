"""为历史标定基线回填「可比性元数据」sidecar（`<report>.meta.json`）。

## 为什么是 sidecar 而不是重跑

要回答「v3 相对 v2 强弱」，需要一份**同母体、同配置**的 v2 基线。重跑 64 局约 100 分钟；
而那份基线的产物（jsonl + report + 当时的开局书）都还在 —— 能算的量都能事后算出来，
所以只在旁边补一个 `meta.json`，**不改历史报告**（历史报告是不可变证据）。

## 四条硬约束（每条都对应一种"算得出来、看起来正常、结果全错"的失败）

1. **书从 git 对象读，不读工作树**：本轮工作树的书已被重生成成 v3。读磁盘会把 v3 指纹
   当 v2 基线的，digest 算得出、格式也对，**没有任何报错**。
2. **两条断言都要**：`rs2-` 管方向（不是 v3），`fpDigest == 4b8137b676b9327e` 管身份
   （是那一份书）。只留一条会漏一半。
3. **文件名显式白名单，不 glob**：`bm-final-n64.report.json` 有判定层，孪生文件
   `bm-final-n64.v1.report.json` 没有（`judgementVersion=None`）。按前缀挑会挑到 `.v1`，
   得到一个不可用基线**且不报错**（字段缺失会被当成"老报告"）。
4. **交叉验证 jsonl ↔ report**：由 jsonl 重算的 `wins/losses/draws/score` 必须等于**该报告
   自己声明的**值，否则说明拿错文件，立即中止。

   注意这里断言的是"与报告自身一致"，**不是与某个写死的数字一致**。写死数字的写法已经
   出过一次事：原规格里给的 `12/49/3` 是 **root18** 那份的数字，`bm-final-n64` 实际是
   `13/50/1`（两者 `score` 恰好都是 13.5，所以只对 score 会看不出来）。
   把别处的真值当本处的期望值，是这一类错误里最难查的一种 —— 断言自我一致性才挡得住。

## 用法

    python scripts/backfill_baseline_meta.py            # 生成 sidecar
    python scripts/backfill_baseline_meta.py --check     # 只校验已存在的 sidecar 是否仍然成立
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from calibrate_levels import CONTRACT_GATES, _book_digest, _config_digest  # noqa: E402
from level_targets import PRODUCT_TIERS  # noqa: E402

from xionghan_chess.core.benchmark import Opening  # noqa: E402

RUNS = ROOT / "benchmarks" / "calibration_runs"
BOOK_COMMIT = "33e8fab"
BOOK_PATH_IN_GIT = "xionghan-chess-next/benchmarks/openings/calibration_book.json"
# v2 旧书的 fpDigest（tech-architect 按规格算出）。身份断言用它，不用"看起来像 v2"。
V2_BOOK_DIGEST = "4b8137b676b9327e"

# **显式白名单**：只有产品定稿的那一份。不要写 glob/前缀匹配（见模块 docstring 第 3 条）。
TARGETS = ("2026-11-11-bm-final-n64",)


def _book_from_git() -> list[Opening]:
    raw = json.loads(
        subprocess.check_output(
            ["git", "show", f"{BOOK_COMMIT}:{BOOK_PATH_IN_GIT}"], cwd=str(ROOT), text=True, encoding="utf-8"
        )
    )
    entries = [
        Opening(profile=item["profile"], seed=item["seed"], plies=item["plies"], fp=item.get("fp"))
        for item in raw["openings"]
    ]
    # 断言 1：方向 —— 这必须是 v2 的书（工作树那份已经是 v3）
    assert all("rs2-" in (entry.fp or "") for entry in entries), (
        f"这不是 v2 的书：请用 git show {BOOK_COMMIT}:... 而不是工作树"
    )
    # 断言 2：身份 —— 必须是**那一份**，不只是"任何一份 v2 书"
    assert _book_digest(entries) == V2_BOOK_DIGEST, (
        f"不是这一份书：digest={_book_digest(entries)}，期望 {V2_BOOK_DIGEST}"
    )
    return entries


def _rows(stem: str) -> list[dict]:
    path = RUNS / f"{stem}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _report(stem: str) -> dict:
    path = RUNS / f"{stem}.report.json"  # 显式文件名；**不要** f"{stem}*.report.json"
    assert path.is_file(), f"缺报告：{path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("judgementVersion") is not None, (
        f"{path.name} 没有判定层（judgementVersion 缺键）—— 很可能是孪生的 .v1 文件，别用它"
    )
    return payload


def _blocks(rows: list[dict]) -> list[float]:
    """每 2 局一个开局块（同一开局红黑各一），块内取该侧得分均值。"""
    out: list[float] = []
    for start in range(0, len(rows), 2):
        pair = rows[start : start + 2]
        out.append(
            sum(
                1.0 if row["winner"] == row["master_color"] else 0.5 if row["winner"] is None else 0.0
                for row in pair
            )
            / len(pair)
        )
    return out


def _default_config(level: str):
    """`--cap-a auto` + `--max-nodes auto`（即不覆盖）时的生效配置。"""
    tier = PRODUCT_TIERS[level]
    return tier.config(cap=None, max_nodes=tier.max_nodes)


def backfill(stem: str, book: list[Opening]) -> dict:
    rows = _rows(stem)
    report = _report(stem)

    # ---- 交叉验证：jsonl ↔ report（断言自我一致性，不写死数字）----
    wins = sum(1 for row in rows if row["winner"] == row["master_color"])
    losses = sum(1 for row in rows if row["winner"] is not None and row["winner"] != row["master_color"])
    draws = sum(1 for row in rows if row["winner"] is None)
    score = wins + 0.5 * draws
    assert (wins, losses, draws) == (report["wins"], report["losses"], report["draws"]), (
        f"jsonl 与 report 不同源：jsonl={wins}/{losses}/{draws} report="
        f"{report['wins']}/{report['losses']}/{report['draws']}"
    )
    assert abs(score - report["score"]) < 1e-9, f"score 对不上：{score} vs {report['score']}"

    # ---- 三个独立交叉验证（维度不同，一个全绿不代表没问题）----
    adjudicated = [row for row in rows if row.get("adjudicated")]
    draws_no_result = sum(1 for row in rows if row["winner"] is None and row.get("adjudicated"))
    blocks = _blocks(rows)
    distribution = Counter(blocks)
    # ① 总分对窗口（`master_color` 是 A 侧颜色；用反会得到 1-score 那种"看起来合理"的数）
    # ② 截断块集对 adjudicatedGames（防串样本：本轮已有人在两份运行之间串过数字）
    # ③ 块分数分布对块划分（防 jsonl 或配对规则被改动）
    # 「含截断」与「整块都截断」是两件事，别混：前者决定剔除多少块（有效块数），
    # 后者才是 `blocksFullyAdjudicated`（两局都没下完，那一个开局块等于没有信息）。
    adj_block_ids = sorted(
        {index for index, start in enumerate(range(0, len(rows), 2))
         if any(row.get("adjudicated") for row in rows[start : start + 2])}
    )
    fully_adj_block_ids = sorted(
        {index for index, start in enumerate(range(0, len(rows), 2))
         if all(row.get("adjudicated") for row in rows[start : start + 2])}
    )

    score_excl = sum(
        1.0 for row in rows if not row.get("adjudicated") and row["winner"] == row["master_color"]
    ) + 0.5 * sum(1.0 for row in rows if not row.get("adjudicated") and row["winner"] is None)
    games_excl = len(rows) - len(adjudicated)

    return {
        "backfilled": True,
        "source": {
            "commit": BOOK_COMMIT,
            "book": BOOK_PATH_IN_GIT,
            "jsonl": f"benchmarks/calibration_runs/{stem}.jsonl",
            "report": f"benchmarks/calibration_runs/{stem}.report.json",
            "flags": "无运行时自证记录（该次运行早于这些字段的引入）",
        },
        "fields": {
            "fpDigest": _book_digest(book),
            "adjudicatedGames": len(adjudicated),
            "adjudicatedRatio": round(len(adjudicated) / len(rows), 4) if rows else 0.0,
            "scoreExclAdjudicated": score_excl,
            "gamesExclAdjudicated": games_excl,
            "drawsNoResult": draws_no_result,
            # `failedGates` 的历史义保留（含契约门），子集由 `CONTRACT_GATES` 单点定义。
            "failedMeasurementGates": [
                name for name in report.get("failedGates", []) if name not in CONTRACT_GATES
            ],
            # 这份历史报告缺哪些新字段（读取端按"缺失=不通"处理，且能人眼核对）。
            "missingFields": [key for key in ("gatesEvaluated",) if key not in report],
            # 历史报告**没有** `gatesEvaluated`（当时的脚本只有 5 个 gate）。按报告端规矩
            # 「永不出 null」：这里**不带这个键**（= 没评估/没记录），并在 `missingFields`
            # 里点名。写 `null` 会让"没记录"与"记录为空"看起来一样。
            "blocksTotal": len(blocks),
            "blocksWithAdjudication": len(adj_block_ids),
            "blocksFullyAdjudicated": len(fully_adj_block_ids),
            "blocksEffective": len(blocks) - len(adj_block_ids),
            "blockScoreDistribution": {str(key): count for key, count in sorted(distribution.items())},
        },
        "aiConfigDigest": {
            "a": _config_digest("beginner", _default_config("beginner")),
            "b": _config_digest("medium", _default_config("medium")),
            "method": "recomputed",
            # 输入可信度与计算方法**分开记**：能确定"配置就是 CONFIGS 默认值"才算 E1。
            # 实测可验的只有 depth / time_limit / max_nodes 三项（来自产物行为），
            # 其余 6 项（含 root_limit）没有任何产物能验，也没有机器写的 config 侧车。
            "provenance": "E2：depth/time_limit/max_nodes 由产物交叉验证与 CONFIGS 一致；"
            "root_limit 等 6 项无产物可验、无 --config-* 侧车，按默认值推断",
        },
        "verification": {
            "wins_losses_draws": [wins, losses, draws],
            "score": score,
            "adjudicatedBlockIds": adj_block_ids,
            "artifactConfigChecks": {
                "a_completed_depth_all_1": all(row.get("a_completed_depth") == 1.0 for row in rows),
                "a_clean_move_times_max": round(max(t for row in rows for t in row.get("a_clean_move_times") or [0]), 3),
                "bound_reason_nodes": sum(
                    (row.get(f"{side}_bound_reasons") or {}).get("nodes", 0) for row in rows for side in ("a", "b")
                ),
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="回填历史基线的可比性 sidecar（不改历史报告）")
    parser.add_argument("--check", action="store_true", help="只校验已存在的 sidecar 是否仍然成立")
    args = parser.parse_args(argv)

    book = _book_from_git()
    for stem in TARGETS:
        payload = backfill(stem, book)
        target = RUNS / f"{stem}.meta.json"
        if args.check:
            if not target.is_file():
                print(f"缺失：{target}")
                return 1
            stored = json.loads(target.read_text(encoding="utf-8"))
            if stored != payload:
                print(f"不一致：{target}（sidecar 与当前数据/代码算出的不符，需重新回填）")
                return 1
            print(f"一致：{target}")
            continue
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        fields = payload["fields"]
        print(
            f"写出：{target.name}  fpDigest={fields['fpDigest']}  "
            f"wins/losses/draws={payload['verification']['wins_losses_draws']}  "
            f"adjudicated={fields['adjudicatedGames']}  blocks={fields['blocksTotal']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
