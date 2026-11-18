"""反馈层两棵树文案对齐守卫（P1-10 / B2）。

## 守什么

webapp（`webapp/js/i18n.js` 内嵌字典）与 web 旧树（`locales/*.json`）是两套
i18n 来源。对**同一用户可见事件**，两端文案必须逐字相同（中 / 英各一条）；
任一端改字而另一端没跟上，本用例点名到事件与两端键。

只钉两棵树都存在的共享事件；各自独有的提示不在本表内。

## 为什么不直接比对整份字典

两棵树的键命名空间本就不同（webapp `puzzle.success` vs web `toast.puzzle_solved`），
整表比对会把历史差异误判成回归。这里按「事件」配对，逐事件核对解析后文案。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEBAPP_I18N = ROOT / "webapp" / "js" / "i18n.js"
LOCALES = ROOT / "locales"
WEBAPP_APP = ROOT / "webapp" / "js" / "ui" / "app.js"
WEB_APP = ROOT / "web" / "js" / "app.js"

# 事件 → (webapp 键, web 旧树键)
PARITY: list[tuple[str, str, str]] = [
    ("room_copied", "online.copied", "toast.room_copied"),
    ("sound_on", "toast.soundOn", "toast.sound_on"),
    ("sound_off", "toast.soundOff", "toast.sound_off"),
    ("exported", "toast.exported", "toast.exported"),
    ("puzzle_wrong", "puzzle.wrong", "toast.puzzle_wrong"),
    ("puzzle_solved", "puzzle.success", "toast.puzzle_solved"),
    ("import_failed", "puzzle.importFailed", "toast.invalid_puzzle"),
]

ENTRY_RE = re.compile(r"'([^']+)':\s*'((?:[^'\\]|\\.)*)'")


def _webapp_dict(lang_block: str) -> dict[str, str]:
    block = WEBAPP_I18N.read_text(encoding="utf-8")
    marker = f"const {lang_block} = {{"
    start = block.index(marker) + len(marker)
    end = block.index("\n};", start)
    body = block[start:end]
    return {key: value for key, value in ENTRY_RE.findall(body)}


def _web_catalog(locale: str) -> dict[str, object]:
    return json.loads((LOCALES / f"{locale}.json").read_text(encoding="utf-8"))


def _lookup(catalog: dict[str, object], dotted: str) -> object:
    node: object = catalog
    for part in dotted.split("."):
        assert isinstance(node, dict), f"web 目录键 {dotted} 路径断裂于 {part}"
        node = node[part]
    return node


@pytest.fixture(scope="module")
def webapp_catalogs() -> dict[str, dict[str, str]]:
    return {"zh-CN": _webapp_dict("zh"), "en": _webapp_dict("en")}


@pytest.mark.parametrize("event,webapp_key,web_key", PARITY)
def test_shared_event_copy_parity(
    event: str,
    webapp_key: str,
    web_key: str,
    webapp_catalogs: dict[str, dict[str, str]],
) -> None:
    for locale in ("zh-CN", "en"):
        web_text = str(_lookup(_web_catalog(locale), web_key))
        app_text = webapp_catalogs[locale][webapp_key]
        assert app_text == web_text, (
            f"事件 {event}（{locale}）两端文案不一致：\n"
            f"  webapp [{webapp_key}] = {app_text!r}\n"
            f"  web    [{web_key}] = {web_text!r}"
        )


def test_toast_signature_accepts_level() -> None:
    """两棵树的 toast 都必须接受 level 语义参数（默认 info）。"""
    app_src = WEBAPP_APP.read_text(encoding="utf-8")
    web_src = WEB_APP.read_text(encoding="utf-8")
    assert re.search(r"function toast\(message,\s*level\s*=\s*'info'\)", app_src), (
        "webapp toast 签名未声明 level（默认 info）"
    )
    assert re.search(r"function toast\(message,\s*level\)", web_src), (
        "web 旧树 toast 签名未接受 level 参数"
    )
