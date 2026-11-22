"""web 旧树：逐手档位文案必须走 i18n，不能硬编码中文。

用户报的问题：英文界面里 `renderAnalysis` 的五个档位仍是「最佳 / 良好 / 欠准 /
失误 / 严重失误」。档位名是**呈现文案**，语言包才是唯一源；写在函数里就等于
把中文钉死，切英文也治不了。

这条守卫两个方向都查：
1. `renderAnalysis` 里不得出现中文字面量，且必须按 `analysis.<quality>` 取词；
2. `locales/*.json` 里五个键齐全 —— 只改函数不改词表，`t()` 会原样返回 key，
   界面直接显示 `analysis.blunder` 这种裸键（比中文更糟）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITIES = ("best", "good", "inaccuracy", "mistake", "blunder")
CJK = re.compile(r"[\u4e00-\u9fff]")


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_render_analysis_has_no_hardcoded_chinese() -> None:
    body = _function_body(_read("web/js/app.js"), "renderAnalysis")
    assert not CJK.search(body), f"renderAnalysis 仍有中文字面量：{CJK.findall(body)}"


def test_render_analysis_takes_labels_from_catalog() -> None:
    body = _function_body(_read("web/js/app.js"), "renderAnalysis")
    for quality in QUALITIES:
        assert f"t('analysis.{quality}')" in body, f"renderAnalysis 未从词表取 analysis.{quality}"


def test_both_locales_carry_the_five_quality_labels() -> None:
    for locale in ("zh-CN.json", "en.json"):
        catalog = json.loads(_read(f"locales/{locale}"))
        section = catalog.get("analysis")
        assert isinstance(section, dict), f"{locale} 缺 analysis 词条组"
        for quality in QUALITIES:
            assert section.get(quality), f"{locale} 缺 analysis.{quality}"
    english = json.loads(_read("locales/en.json"))["analysis"]
    assert not any(CJK.search(value) for value in english.values()), (
        "en.json 的档位词条仍是中文：" + repr(english)
    )
