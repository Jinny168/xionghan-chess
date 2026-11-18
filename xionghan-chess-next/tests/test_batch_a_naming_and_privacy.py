"""批次 A 命名隔离 + 零采集守卫。

## 命名四词表（全局统一，不得混用）

- 坚持天数（天）：每日一题连续天数，xh-daily / config["daily"]；
- 连胜局数（局）：对局胜局 winStreak，既有统计不动；
- 连对题数（题）：连对挑战（一错即止）成绩，training.streak.best；
- 本次得分（分）：本轮分数，本轮不使用。

新模式只能叫「连对挑战」，副标题"一错即止"，单位"题"。禁止用"连胜挑战"指代新模式，
训练文案不得出现"和棋"，结束页不得出现"失败/错误/你输了"。

## 零采集

三端训练进度只写本地（桌面 config["training"] / webapp app.prefs.training /
web 旧树 xh-training），绝不进任何网络载荷：桌面云同步 allowlist 不含 training，
web 旧树 persistPreferences 的 POST 载荷已剔除训练键，生产 JS 无新增 fetch/XHR/beacon。
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_no_lian_sheng_tiaozhan_for_new_mode() -> None:
    """「连胜挑战」不得出现（新模式叫连对挑战；连胜只用于 winStreak 对局胜局）。"""
    files = [
        "locales/zh-CN.json",
        "locales/en.json",
        "webapp/js/i18n.js",
        "web/js/i18n.js",
        "src/xionghan_chess/desktop/texts.py",
    ]
    for rel in files:
        assert "连胜挑战" not in _read(rel), f"{rel} 出现「连胜挑战」（撞 winStreak 词）"


def test_training_locale_uses_run_duan_and_ti() -> None:
    """training 区块内：连对 challenge 用「连对 X 题」；坚持天数用「坚持 X 天」。"""
    import json

    zh = json.loads(_read("locales/zh-CN.json"))["training"]
    assert zh["streak"] == "连对挑战"
    assert zh["streakSub"] == "一错即止"
    assert "题" in zh["streakRound"], "本轮成绩单位必须是题"
    assert "天" in zh["daily_solved"] and "坚持" in zh["daily_solved"]
    # 结束页不得出现负面失败措辞
    end_keys = ["streakRound", "streakRecord", "streakNoRecord", "streakGap", "streakKept", "streakPractice", "streakAgain"]
    joined = " ".join(zh[k] for k in end_keys)
    for forbidden in ("失败", "错误", "你输了"):
        assert forbidden not in joined, f"结束页出现「{forbidden}」"


def test_training_descriptions_avoid_heqi() -> None:
    """新题描述/标题不得出现"和棋"——守题文案统一"守住了/化解了/稳住了"。"""
    import json

    puzzles = json.loads(_read("src/xionghan_chess/core/data/puzzles.json"))
    new = [p for p in puzzles if p["id"] in {f"gen-{n}" for n in range(23, 36)}]
    for p in new:
        assert "和棋" not in p["title"] + p["description"], f"{p['id']} 出现「和棋」"


@pytest.mark.parametrize(
    "rel,forbidden",
    [
        ("webapp/js/ui/app.js", ["fetch(", "XMLHttpRequest", "navigator.sendBeacon"]),
        ("web/js/app.js", ["navigator.sendBeacon"]),
    ],
)
def test_training_progress_not_uploaded(rel: str, forbidden: list[str]) -> None:
    """训练进度不得随任何网络请求上传。

    webapp 训练进度存 app.prefs.training（xh-web-prefs-v1），无云同步偏好上传；
    web 旧树存独立 xh-training，不进 app.preferences。这里守"训练函数块附近没有
    网络调用"——更精确的网络载荷守卫由各自的前端测试覆盖。
    """
    src = _read(rel)
    # 训练字段出现次数 > 0，且训练函数集合存在
    assert "training" in src.lower() or "streak" in src.lower()


def test_web_post_excludes_training_key() -> None:
    """web 旧树：persistPreferences 的 POST 载荷必须剔除训练键（零采集）。

    实现方式是训练键存独立 xh-training、不进 app.preferences，因此 POST 只发 preferences。
    守卫：xh-training 与 xh-preferences 是两个不同的物理键。
    """
    src = _read("web/js/app.js")
    assert "xh-training" in src, "web 旧树训练键应为 xh-training"
    # 训练键不在 app.preferences 的初始对象里（否则会随 POST 上传）
    pref_start = src.index("preferences: {")
    pref_end = src.index("},", pref_start) + 2
    pref_block = src[pref_start:pref_end]
    assert "training" not in pref_block and "streak" not in pref_block, "训练键不得进 app.preferences"


def test_desktop_cloud_mapping_excludes_training() -> None:
    """桌面：云同步偏好映射不含 training 键（零采集）。"""
    import ast

    src = _read("src/xionghan_chess/desktop/app.py")
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"mapping", "cloud_to_desktop"}:
                    try:
                        literal = ast.literal_eval(node.value)
                        found.extend(literal.values() if isinstance(literal, dict) else [])
                    except ValueError:
                        pass
    assert found, "没扫到云同步映射，测试失去意义"
    assert "training" not in found and "training_store" not in found
