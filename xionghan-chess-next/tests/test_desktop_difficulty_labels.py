"""难度下拉文案里的时长必须与 `CONFIGS` 一致。

## 为什么需要这条

文案里的「每手约 5 秒」是**玩家对等待时间的承诺**，而真实预算在
`core/ai.py` 的 `CONFIGS[difficulty].time_limit`。两处一旦分叉，就会出现
"写着约 5 秒、实测 12 秒"这类无法解释的现象——而且没人会想到去查语言文件。

所以这里**从 locale 里把秒数解析出来**，与 `CONFIGS` 逐档比对；同时禁止出现
"更强/更深"这类暗示——实测中档与高档同为 depth 2、选点相同，写"更强"就是假承诺。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from xionghan_chess.core.ai import CONFIGS, Difficulty

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"zh-CN": ROOT / "locales" / "zh-CN.json", "en": ROOT / "locales" / "en.json"}
NUMBER = re.compile(r"\d+(?:\.\d+)?")
# 明确禁止的措辞：两档同深度、同选点，写"更强/更深"是与实测冲突的假承诺。
FORBIDDEN = ("更强", "更深", "更慢", "stronger", "deeper")


def load(locale: str) -> dict:
    return json.loads(LOCALES[locale].read_text(encoding="utf-8"))["difficulty"]


@pytest.mark.parametrize("locale", list(LOCALES))
@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_label_seconds_match_config(locale: str, difficulty: Difficulty) -> None:
    label = load(locale)[difficulty.value]
    numbers = NUMBER.findall(label)
    assert numbers, f"{locale}/{difficulty.value} 文案里没有秒数：{label!r}"
    listed, actual = float(numbers[0]), CONFIGS[difficulty].time_limit
    # **严格对齐，不放宽**：文案对应的是**配置值**，不是实测值 —— "约 12 秒"与实测 12.2s
    # 并不冲突（差 1.7%），但"配置 6 秒、文案 5 秒"这种错配必须红。
    assert listed == pytest.approx(actual), (
        f"{locale}/{difficulty.value} 文案写 {listed} 秒，"
        f"CONFIGS 实际 {actual} 秒 —— 改预算时忘了改文案？")


@pytest.mark.parametrize("locale", list(LOCALES))
def test_labels_do_not_claim_more_strength(locale: str) -> None:
    for difficulty in Difficulty:
        label = load(locale)[difficulty.value]
        for word in FORBIDDEN:
            assert word not in label, f"{locale}/{difficulty.value} 含禁用措辞「{word}」：{label!r}"


def test_master_and_hard_share_the_budget_at_config_level() -> None:
    """配置层：大师与高级预算相同（大师换的是 MCTS，不是预算）。"""
    assert (CONFIGS[Difficulty.MASTER].time_limit
            == CONFIGS[Difficulty.HARD].time_limit), "预算一旦分叉，这条与文案都要改"


@pytest.mark.parametrize("locale", list(LOCALES))
def test_labels_do_not_compare_budgets_across_levels(locale: str) -> None:
    """文案里不得出现「同预算 / same budget」这类跨档比较字样。

    我们主动放弃了那个说法：下一版"提前返回"落地后，高级通常 ~5s 就返回、大师仍 12s，
    "同预算"会让玩家困惑"预算一样为什么慢一倍"。**文案层不再承诺档间预算关系。**
    """
    banned = ("同预算", "同一预算", "same budget")
    for difficulty in Difficulty:
        label = load(locale)[difficulty.value]
        for word in banned:
            assert word not in label, f"{locale}/{difficulty.value} 含跨档比较措辞「{word}」：{label!r}"
