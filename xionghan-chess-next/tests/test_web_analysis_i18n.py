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


SET_TEXT_RE = re.compile(
    r"""setText\(\s*(['"])(?P<selector>.+?)\1\s*,\s*'(?P<key>[^']+)'\s*\)"""
)


def _balanced_body(source: str, signature: str) -> str:
    """从 `signature` 起按花括号配平截取函数体（比找 `\\nfunction ` 稳，不受 export 影响）。"""
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"函数 {signature} 的花括号未配平")


def _lookup(catalog: object, dotted: str) -> object | None:
    node = catalog
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def test_apply_static_i18n_keys_all_exist_in_both_locales() -> None:
    """`applyStaticI18n` 里登记的每个 setText key，必须在 zh / en 两份语言包里查得到。

    背景：`#analysisDialog .dialog-title h2` 曾登记成 `dialog.analysis_title`，而该键
    只存在于 `desktop` 分组下。`t()` 的兜底是 `?? key`，于是标题直接渲染成裸键
    `dialog.analysis_title`；`applyStaticI18n()` 每次 boot 都跑，连中文界面也从
    「AI 棋局分析」退化成裸键。三个既有测试全绿却行为错误 —— 根因是「登记了不存在
    的 key」这类错误当时零门禁。
    """
    body = _balanced_body(_read("web/js/i18n.js"), "function applyStaticI18n(")
    matched = list(SET_TEXT_RE.finditer(body))
    keys = [match.group("key") for match in matched]

    # 防呆：正则一旦失效（改写法、换引号），keys 会退化成空列表而测试假绿。
    assert len(matched) >= 45, (
        f"只从 applyStaticI18n 里解析出 {len(matched)} 条 setText 字面量，远少于预期"
        "（应 >= 45）—— 正则可能失效了，先修 SET_TEXT_RE"
    )

    catalogs = {name: json.loads(_read(f"locales/{name}")) for name in ("zh-CN.json", "en.json")}
    missing_zh: list[str] = []
    missing_en: list[str] = []
    for key in keys:
        if _lookup(catalogs["zh-CN.json"], key) is None:
            missing_zh.append(key)
        if _lookup(catalogs["en.json"], key) is None:
            missing_en.append(key)

    only_zh = set(missing_zh) - set(missing_en)
    only_en = set(missing_en) - set(missing_zh)
    both = set(missing_zh) & set(missing_en)
    assert not only_zh and not only_en and not both, (
        "applyStaticI18n 登记的语言包 key 不存在（界面会显示裸键）："
        f"仅 zh-CN 缺={sorted(only_zh)}；仅 en 缺={sorted(only_en)}；"
        f"两边都缺={sorted(both)}"
    )


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
