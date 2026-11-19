"""历史基线 sidecar（`<report>.meta.json`）的守卫。

## 挡的是什么

回填脚本 `scripts/backfill_baseline_meta.py` 给无法重跑的历史基线补"可比性元数据"。
它算出来的每个数都**看起来正常**——包括算错的时候：

- 读工作树的书（已重生成成 v3）而不是 `git show 33e8fab:` → digest 算得出、格式对、**全错**；
- 读孪生文件 `....v1.report.json`（没有判定层）→ 字段缺失被当成"老报告"，**静默降级**；
- 把**别处**的真值当本处的期望值 → 断言通过、结论全错。

本文件钉三件：身份（fpDigest）、内容（jsonl ↔ report 自我一致）、以及 sidecar 与当前数据
仍能逐字段复算一致（`--check` 模式）。

## 一个必须记下来的更正

原规格里给的交叉验证值是 `wins/losses/draws = 12/49/3`、`drawsNoResult = 2` ——
那是 **`bm-root18-final-n64`** 的数字。`bm-final-n64` 实际是 **13/50/1**、`drawsNoResult = 1`。
两者 `score` 恰好都是 13.5，所以只对 `score` 完全看不出来。
这正是"把别处的真值当本处的期望值"的典型：断言自我一致性才挡得住，写死数字挡不住。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "benchmarks" / "calibration_runs"
STEM = "2026-11-11-bm-final-n64"
META = RUNS / f"{STEM}.meta.json"
BOOK_COMMIT = "33e8fab"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# git 二进制缺失属环境硬阻塞：可复现性守卫必须红灯暴露，不能混进「产物依赖跳过」。
GIT_NOT_FOUND_REASON = (
    "缺少 git 可执行文件：可复现性守卫未执行。请把 git 加入 PATH，或设置环境变量 "
    "GIT_EXECUTABLE 指向 git；本文件的 skip 只对应「产物缺失」或「git 对象缺失」，"
    "不包含 git 二进制缺失。"
)


def _resolve_git() -> str | None:
    """解析 git 可执行路径：优先 `GIT_EXECUTABLE`，否则在 `PATH` 里查；都没有返回 `None`。"""
    env = os.environ.get("GIT_EXECUTABLE")
    if env:
        return env
    return shutil.which("git")


def _require_git() -> str:
    """返回 git 路径；二进制找不到时硬失败（不静默 skip）。"""
    git = _resolve_git()
    if git is None:
        pytest.fail(GIT_NOT_FOUND_REASON)
    return git


def _object_present(git: str) -> bool:
    try:
        subprocess.run(
            [git, "cat-file", "-e", f"{BOOK_COMMIT}^{{commit}}"],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False
    return True


def _has_commit() -> bool:
    """git 在且记录对象存在 → True。git 本身缺失时返回 False，交由 `_require_git` 硬失败。"""
    git = _resolve_git()
    return git is not None and _object_present(git)


def _has_run_artifacts() -> bool:
    """标定产物是**本地运行输出**，仓库里不跟踪（`calibration_runs/` 全部 untracked）。

    所以全新克隆 / CI 上它们不存在 —— 那时本文件整体跳过。**不要**为了让它绿去
    提交 jsonl（475KB/份，且是运行输出，不是源码）。
    """
    return (RUNS / f"{STEM}.jsonl").is_file() and (RUNS / f"{STEM}.report.json").is_file()


# 两条正常 skip：git 在但对象缺失（浅克隆/历史改写）、本地产物缺失。
# git 二进制缺失不在此列 —— 由 `_require_git` fixture 硬失败，避免伪装成产物跳过。
pytestmark = [
    pytest.mark.skipif(
        not _has_commit(), reason=f"缺少 git 对象 {BOOK_COMMIT}（git 在但浅克隆或历史被改写）"
    ),
    pytest.mark.skipif(not _has_run_artifacts(), reason=f"缺少本地标定产物 {STEM}（运行输出不进仓库）"),
]


@pytest.fixture(autouse=True)
def _require_git_for_reproducibility() -> str:
    """每条守卫执行前确认 git 可用；缺失即硬失败。"""
    return _require_git()


def _meta() -> dict:
    assert META.is_file(), f"缺少 {META.name}：跑 python scripts/backfill_baseline_meta.py"
    return json.loads(META.read_text(encoding="utf-8"))


def test_backfilled_meta_reproduces_from_git_and_jsonl() -> None:
    """`--check` 会重算一遍并与磁盘 sidecar 逐字段比对（同源、可复现）。"""
    from backfill_baseline_meta import main

    assert main(["--check"]) == 0, "sidecar 与当前数据/代码算出的不符 —— 需重新回填，别手改"


def test_meta_pins_the_v2_book_identity() -> None:
    """身份断言：必须是**那一份** v2 书，不只是"任何一份 v2 书"。

    （脚本内部还有 `rs2-` 方向断言；这里从产物侧再核一次，防止将来有人放宽内部断言。）
    """
    assert _meta()["fields"]["fpDigest"] == "4b8137b676b9327e"


def test_meta_records_the_real_split_not_the_root18_numbers() -> None:
    """内容断言：`bm-final-n64` 是 13/50/1，不是 root18 的 12/49/3。

    `score` 两者都是 13.5 —— 只看分数永远发现不了串样本。
    """
    verification = _meta()["verification"]
    assert verification["wins_losses_draws"] == [13, 50, 1]
    assert verification["score"] == 13.5
    assert _meta()["fields"]["drawsNoResult"] == 1
    assert _meta()["fields"]["adjudicatedGames"] == 8


def test_meta_block_accounting_is_self_consistent() -> None:
    """块账要自洽：含截断的块 ≥ 整块都截断的块，有效块 = 总块 − 含截断块。

    `bm-final-n64` 实测 32 块、7 块含截断、1 块两局都截断 → 有效 25 块
    （与设计侧核算的 kept=25 一致；root18 才是 26）。
    """
    fields = _meta()["fields"]
    assert fields["blocksTotal"] == 32
    assert fields["blocksWithAdjudication"] >= fields["blocksFullyAdjudicated"]
    assert fields["blocksFullyAdjudicated"] <= 2, "设计口径：整块截断不得超过 2 块"
    assert fields["blocksEffective"] == fields["blocksTotal"] - fields["blocksWithAdjudication"] == 25


def test_meta_never_emits_null_for_unrecorded_fields() -> None:
    """历史报告缺的字段要**不带键**（= 没记录），不能写 `null`。

    `null` 会把"没评估"与"评估了但为空"混成同一个显示 —— 这正是 `winner=None`
    同时表示"真和棋"和"截断无胜负"那个坑的同款。
    """
    fields = _meta()["fields"]
    assert "gatesEvaluated" not in fields
    assert fields["missingFields"] == ["gatesEvaluated"]
    assert all(value is not None for value in fields.values()), "backfilled 字段里不该出现 null"


def test_ai_config_digest_declares_its_confidence() -> None:
    """计算方法与输入可信度必须分开记。

    这次运行早于可比性字段的引入，产物里只验得出 depth / time_limit / max_nodes 三项，
    `root_limit` 等 6 项无产物可验 —— 所以它只能是 **E2（事后推断）**，不能当运行时自证。
    """
    digest = _meta()["aiConfigDigest"]
    assert digest["method"] == "recomputed"
    assert digest["provenance"].startswith("E2")
    assert digest["a"] and digest["b"] and digest["a"] != digest["b"]


def test_digest_is_anchored_to_recorded_commit_and_keeps_legacy_label() -> None:
    """指纹必须锚定记录 commit 的旧口径，不能被当前 CONFIGS 漂移改写。

    历史教训：曾有人为让「回填脚本按当前 CONFIGS 复算」变绿，把 n=64 基线的 beginner
    指纹从 0.55 口径（`b014d8072e5a7c7d`）改成 0.18 口径 —— 等于把「当时跑的配置」抹成
    「现在的配置」，会让新口径基线被误判成与这份旧基线配置可比。这里钉住：锚定 commit、
    旧口径留痕说明、以及旧指纹本身，三者缺一即红。
    """
    meta = _meta()
    digest = meta["aiConfigDigest"]
    assert digest["anchorCommit"] == meta["source"]["commit"] == "33e8fab"
    note = digest["legacyNote"]
    assert "0.55" in note and "0.18" in note and "等价比较" in note
    # 0.55 两层串行口径的 beginner 指纹（锚定 33e8fab 派生，脚本 --check 复算一致）。
    assert digest["a"] == "b014d8072e5a7c7d"
    # medium 摘要未随 D4 改动。
    assert digest["b"] == "0004d697df110392"


def test_resolve_git_prefers_git_executable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`GIT_EXECUTABLE` 优先于 PATH（即便 PATH 里也能查到 git）。"""
    monkeypatch.setenv("GIT_EXECUTABLE", r"C:\fake\git.exe")
    assert _resolve_git() == r"C:\fake\git.exe"


def test_resolve_git_falls_back_to_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """未设 `GIT_EXECUTABLE` 时回退到 PATH 查询，与 `shutil.which` 结果一致。"""
    monkeypatch.delenv("GIT_EXECUTABLE", raising=False)
    assert _resolve_git() == shutil.which("git")


def test_missing_git_is_hard_fail_not_silent_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """git 二进制找不到：`_resolve_git()` 返回 None，`_require_git()` 硬失败（红灯），不静默 skip。"""
    monkeypatch.delenv("GIT_EXECUTABLE", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert _resolve_git() is None
    with pytest.raises(pytest.fail.Exception):
        _require_git()


def test_real_git_resolves_in_current_environment() -> None:
    """本机环境应能解析到真实 git（守卫正常执行的前置）。"""
    assert _resolve_git() is not None
