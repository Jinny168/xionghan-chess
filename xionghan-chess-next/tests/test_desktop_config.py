"""桌面配置层单测（阶段1 S1-1「配置语义集中」）。

覆盖 `desktop/config.py` 里**不依赖 Qt**的部分：

1. `DEFAULTS` 覆盖了代码里读取的每一个键 —— 这条直接对应一个真实缺陷：
   `server_url` 被 app.py 读 3 次、被 SettingsDialog.value() 回填，
   却不在 DEFAULTS 里，首次运行只能靠调用点的硬编码字符串兜底。
2. `GAME_BREAKING_KEYS` / `settings_differ_in_game_breaking_keys()` ——
   S1-9「改主题不丢对局、改规则才重开」的判定逻辑，从 MainWindow 里挪出来后
   终于可以被单测直接覆盖（此前只有冒烟能验）。
3. `data_dir()` / `games_dir()` —— 此前 app.py 有 3 处、storage.py 有 3 处各自
   拼 `config_path().parent / "games"`，现在必须是同一个来源。

`config_path()` 依赖 `APPDATA` 环境变量，测试用 monkeypatch 指向 tmp_path，
避免污染真实的用户目录。
"""

from __future__ import annotations

import json

import pytest

from xionghan_chess.desktop import config as desktop_config


@pytest.fixture()
def isolated_appdata(tmp_path, monkeypatch):
    """把 APPDATA 指到临时目录，隔离真实用户配置。"""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


# --------------------------------------------------------------------------- #
# 默认值完整性
# --------------------------------------------------------------------------- #


def test_defaults_declares_server_url() -> None:
    """S1-1 修复的回归守卫：server_url 必须在 DEFAULTS 里。"""
    assert "server_url" in desktop_config.DEFAULTS
    assert desktop_config.DEFAULTS["server_url"] == desktop_config.DEFAULT_SERVER_URL


def test_defaults_covers_every_key_read_by_desktop_code() -> None:
    """扫 desktop 包里所有 `config.get("x")` / `config["x"]`，必须都在 DEFAULTS 中。

    漏声明的后果不是报错，而是**静默**用调用点的兜底值 —— 不同调用点写不同的
    兜底值时行为就会分叉。这个断言把「静默」变成「红」。
    """
    import re
    from pathlib import Path

    root = Path(desktop_config.__file__).parent
    pattern = re.compile(r'config(?:\.get\(|\[)"([a-z_]+)"')
    used: set[str] = set()
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        used |= set(pattern.findall(path.read_text(encoding="utf-8")))
    missing = sorted(used - set(desktop_config.DEFAULTS))
    assert not missing, f"代码读取但 DEFAULTS 未声明的配置键：{missing}"


def test_load_config_returns_defaults_when_file_absent(isolated_appdata) -> None:
    loaded = desktop_config.load_config()
    assert loaded["profile"] == desktop_config.DEFAULTS["profile"]
    assert loaded["server_url"] == desktop_config.DEFAULT_SERVER_URL


def test_load_config_merges_over_defaults(isolated_appdata) -> None:
    path = desktop_config.config_path()
    path.write_text(json.dumps({"theme": "dark", "extra": 1}), encoding="utf-8")
    loaded = desktop_config.load_config()
    assert loaded["theme"] == "dark"
    assert loaded["extra"] == 1
    # 未写进文件的键仍回到默认值（升级后新增配置项不会 KeyError）
    assert loaded["difficulty"] == desktop_config.DEFAULTS["difficulty"]


def test_load_config_survives_corrupt_json(isolated_appdata) -> None:
    """配置文件被手改坏时不能让桌面端起不来 —— 回落到默认值。"""
    desktop_config.config_path().write_text("{oops", encoding="utf-8")
    assert desktop_config.load_config() == desktop_config.DEFAULTS


def test_load_config_survives_non_dict_json(isolated_appdata) -> None:
    """`[]` 是合法 JSON 但不是 dict，`{**DEFAULTS, **[]}` 会 TypeError。"""
    desktop_config.config_path().write_text("[]", encoding="utf-8")
    assert desktop_config.load_config() == desktop_config.DEFAULTS


def test_save_then_load_roundtrip(isolated_appdata) -> None:
    data = dict(desktop_config.DEFAULTS, theme="purple", sound_volume=12)
    desktop_config.save_config(data)
    assert desktop_config.load_config() == data


def test_save_config_keeps_chinese_readable(isolated_appdata) -> None:
    """`ensure_ascii=False` —— 否则用户手翻配置文件会看到一堆 \\uXXXX。"""
    desktop_config.save_config(dict(desktop_config.DEFAULTS, account_display_name="张三"))
    raw = desktop_config.config_path().read_text(encoding="utf-8")
    assert "张三" in raw


# --------------------------------------------------------------------------- #
# 目录来源一致性
# --------------------------------------------------------------------------- #


def test_data_dir_is_config_dir(isolated_appdata) -> None:
    assert desktop_config.data_dir() == desktop_config.config_path().parent


def test_games_dir_exists_after_call(isolated_appdata) -> None:
    folder = desktop_config.games_dir()
    assert folder.is_dir()
    assert folder == desktop_config.data_dir() / "games"


def test_storage_uses_shared_dirs(isolated_appdata) -> None:
    """storage 的统计文件必须落在 data_dir 下，不能是另一套拼法。"""
    from xionghan_chess.desktop import storage

    assert storage.statistics_path() == desktop_config.data_dir() / "statistics.json"


# --------------------------------------------------------------------------- #
# S1-9：哪些设置会重开对局
# --------------------------------------------------------------------------- #


def test_game_breaking_keys_are_the_expected_three() -> None:
    assert set(desktop_config.GAME_BREAKING_KEYS) == {"profile", "rule_options", "initial_minutes"}


@pytest.mark.parametrize("key", ["theme", "font", "language", "sound_volume", "flipped", "animations"])
def test_cosmetic_changes_do_not_restart_game(key: str) -> None:
    """S1-9 的核心承诺：改外观不该丢掉正在下的一局。"""
    old = dict(desktop_config.DEFAULTS)
    new = dict(old, **{key: "__changed__"})
    assert desktop_config.settings_differ_in_game_breaking_keys(old, new) is False


@pytest.mark.parametrize("key", list(desktop_config.GAME_BREAKING_KEYS))
def test_rule_changes_do_restart_game(key: str) -> None:
    old = dict(desktop_config.DEFAULTS)
    new = dict(old, **{key: "__changed__"})
    assert desktop_config.settings_differ_in_game_breaking_keys(old, new) is True


def test_identical_configs_do_not_restart() -> None:
    same = dict(desktop_config.DEFAULTS)
    assert desktop_config.settings_differ_in_game_breaking_keys(same, dict(same)) is False


def test_missing_key_on_both_sides_does_not_count_as_change() -> None:
    """两边都缺同一键（老配置文件）不应误判为「规则变了」而重开对局。"""
    old = {key: value for key, value in desktop_config.DEFAULTS.items() if key != "rule_options"}
    new = dict(old)
    assert desktop_config.settings_differ_in_game_breaking_keys(old, new) is False


def test_mainwindow_alias_points_to_shared_tuple() -> None:
    """MainWindow._GAME_BREAKING_KEYS 保留为兼容别名，但必须是同一份来源。"""
    pytest.importorskip("PySide6", reason="MainWindow 需要 PySide6")
    from xionghan_chess.desktop.app import MainWindow

    assert MainWindow._GAME_BREAKING_KEYS is desktop_config.GAME_BREAKING_KEYS
