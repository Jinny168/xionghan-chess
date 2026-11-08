"""桌面端用到的 i18n key 必须存在于 locale（阶段1 S1-8，验收策略 A5）。

背景（可验证性审计 P1-I）：`test_i18n.py::test_locale_keys_are_paired` 只保证
zh/en **键成对**，不保证「代码实际用到的 key 存在」—— 两边同时缺同一个 key 时
没人发现。这个用例补上那一半：扫桌面端源码里 `t("...")` 的字面量 key，
断言全部能在 `locales/zh-CN.json` 里找到。

它是**纯文本扫描**（不 import PySide6），所以能在 CI 的 pytest job 里跑。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SRC = ROOT / "src" / "xionghan_chess" / "desktop"
ZH_CN = ROOT / "locales" / "zh-CN.json"

# 匹配模块级 `t("key")` / `t('key')` 的第一个字面量参数。
# key 形态为点分小写（desktop.training_title / status.turn / common.red ...）。
_KEY_CALL = re.compile(r"(?<![\w])t\(\s*[\"']([a-z][a-z0-9_.]*)[\"']")


def _flatten(node, prefix: str = "") -> set[str]:
    """把嵌套 locale JSON 压成点分键集合。"""
    keys: set[str] = set()
    if isinstance(node, dict):
        for name, value in node.items():
            keys |= _flatten(value, f"{prefix}.{name}" if prefix else name)
    else:
        keys.add(prefix)
    return keys


def _used_keys() -> set[str]:
    used: set[str] = set()
    for path in sorted(DESKTOP_SRC.rglob("*.py")):
        used |= set(_KEY_CALL.findall(path.read_text(encoding="utf-8")))
    return used


def test_desktop_t_keys_all_exist_in_locale():
    """桌面端 `t("...")` 用到的每个 key 都必须存在于 zh-CN.json。"""
    zh_keys = _flatten(json.loads(ZH_CN.read_text(encoding="utf-8")))
    used = _used_keys()
    assert used, "没扫到任何 t() 调用 —— 正则或路径可能坏了，这条断言会变成空转"
    missing = sorted(key for key in used if key not in zh_keys)
    assert not missing, (
        f"桌面端用了 locale 里不存在的 key（用户会看到裸 key 或回退文本）：{missing}"
    )


def test_desktop_scan_is_not_vacuous():
    """防止上面那条退化成空转：扫到的 key 数必须达到一个下限。"""
    used = _used_keys()
    # 若桌面端大幅重构导致 t() 调用骤减，这里会先失败，提示复核阈值。
    assert len(used) >= 40, f"只扫到 {len(used)} 个 key，疑似扫描失效"


@pytest.mark.parametrize("key", sorted(_used_keys()))
def test_key_is_non_empty_string_in_both_locales(key):
    """每个被用到的 key 在 zh 与 en 里都必须是非空字符串（防漏译/空值）。"""
    en = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads(ZH_CN.read_text(encoding="utf-8"))

    def lookup(doc):
        node = doc
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    for name, doc in (("zh-CN", zh), ("en", en)):
        value = lookup(doc)
        assert isinstance(value, str) and value.strip(), f"{name} 的 {key} 不是非空字符串"
