"""webapp：本地存储写失败不得静默。

隐私模式、Cookie 被禁、配额耗尽时 `localStorage.setItem` 会抛。原先五处
（偏好 / 战绩 / 已解习题 / 存档 / 棋谱库）都是裸 `catch {}` 直接吞掉，最刺眼的
是棋谱库：`writeLibrary` 静默失败后 `saveToLibrary` 照样弹「本局已存入棋谱库」，
用户以为存上了，重开才发现没了 —— 假成功比报错更糟。

口径：
1. 五个写点全部走 `safeSet`，且函数体内不得再出现裸 `localStorage.setItem`；
2. `safeSet` 必须 toast（warn）并按 key 去重（设置页滑块会连续触发 savePrefs）；
3. 只有真写成功才允许弹「已存入棋谱库」。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"
I18N = ROOT / "webapp" / "js" / "i18n.js"

# 写点 → 所在函数（都是「写失败 = 数据丢了」的地方；读取点的 catch 不在本口径内）
WRITE_SITES = ("savePrefs", "saveStats", "markSolved", "saveSession", "writeLibrary")


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_safe_set_warns_once_per_key_and_reports_failure() -> None:
    body = _function_body(_source(), "safeSet")
    assert "localStorage.setItem(key, value)" in body
    assert "toast(t('toast.storageFailed'), 'warn')" in body, "写失败必须 toast warn"
    assert "storageWarned.has(key)" in body and "storageWarned.add(key)" in body, (
        "同一 session、同一个键只能提示一次"
    )
    assert "return false" in body, "safeSet 必须让调用方知道写失败了"


def test_all_storage_writes_go_through_safe_set() -> None:
    source = _source()
    missing = [name for name in WRITE_SITES if "safeSet(" not in _function_body(source, name)]
    assert not missing, "这些写点仍绕过 safeSet：" + ", ".join(missing)
    raw = [name for name in WRITE_SITES if "localStorage.setItem" in _function_body(source, name)]
    assert not raw, "这些写点仍有裸 setItem：" + ", ".join(raw)


def test_library_success_toast_only_after_a_real_write() -> None:
    body = _function_body(_source(), "saveToLibrary")
    assert "if (writeLibrary(list)) toast(t('library.saved'), 'success')" in body, (
        "写失败时不能弹「已存入棋谱库」"
    )


def test_storage_failure_copy_exists_in_both_languages() -> None:
    source = I18N.read_text(encoding="utf-8")
    zh = source[source.index("const zh = {"):source.index("const en = {")]
    en = source[source.index("const en = {"):]
    for block, name in ((zh, "zh"), (en, "en")):
        assert "'toast.storageFailed':" in block, f"i18n {name} 块缺 toast.storageFailed"
    assert "本地存储" in zh, "中文文案缺失"
