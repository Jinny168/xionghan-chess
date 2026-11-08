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
from pathlib import Path

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


# --------------------------------------------------------------------------- #
# P1-R：schema 版本与迁移
# --------------------------------------------------------------------------- #
def test_defaults_declare_current_schema_version() -> None:
    assert desktop_config.DEFAULTS["schema_version"] == desktop_config.CONFIG_VERSION


def test_legacy_file_without_version_is_migrated_and_rewritten(isolated_appdata) -> None:
    """旧配置没有 `schema_version`：读一次之后应当被补上并回写。"""
    path = desktop_config.config_path()
    path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
    loaded = desktop_config.load_config()
    assert loaded["schema_version"] == desktop_config.CONFIG_VERSION
    assert loaded["theme"] == "dark"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == desktop_config.CONFIG_VERSION, "迁移结果应回写一次"


def test_migration_only_runs_once(isolated_appdata) -> None:
    """第一次读会迁移并回写；第二次读到的是已迁移文件，内容不该再变。"""
    path = desktop_config.config_path()
    path.write_text(json.dumps({"initial_minutes": "oops"}), encoding="utf-8")

    first = desktop_config.load_config()
    after_first = path.read_text(encoding="utf-8")
    assert json.loads(after_first)["initial_minutes"] == 20, "迁移应把坏值收敛成默认值"

    second = desktop_config.load_config()
    assert first == second
    assert path.read_text(encoding="utf-8") == after_first, "第二次读取不该再改文件"


@pytest.mark.parametrize(
    "key,raw,expected",
    [
        ("initial_minutes", 999, 180),
        ("initial_minutes", 0, 1),
        ("initial_minutes", "abc", 20),
        ("sound_volume", -5, 0),
        ("sound_volume", 101, 100),
        ("music_volume", "40", 40),
        ("countdown_seconds", -1, 0),
    ],
)
def test_migration_clamps_numeric_values(isolated_appdata, key: str, raw: object, expected: int) -> None:
    """手改配置或旧版本写坏的值，读一次就收敛到合法范围。"""
    desktop_config.config_path().write_text(json.dumps({key: raw}), encoding="utf-8")
    assert desktop_config.load_config()[key] == expected


def test_migration_repairs_wrong_container_types(isolated_appdata) -> None:
    path = desktop_config.config_path()
    path.write_text(json.dumps({"rule_options": "oops", "setup_slots": [1, 2]}), encoding="utf-8")
    loaded = desktop_config.load_config()
    assert loaded["rule_options"] == {}
    assert loaded["setup_slots"] == {}


def test_migration_repairs_unknown_language(isolated_appdata) -> None:
    desktop_config.config_path().write_text(json.dumps({"language": "fr"}), encoding="utf-8")
    assert desktop_config.load_config()["language"] == desktop_config.DEFAULTS["language"]


def test_migration_keeps_unknown_keys(isolated_appdata) -> None:
    """未知键可能是新版本写入的，迁移不能把它丢掉。"""
    desktop_config.config_path().write_text(
        json.dumps({"theme": "dark", "future_feature": {"a": 1}}), encoding="utf-8")
    loaded = desktop_config.load_config()
    assert loaded["future_feature"] == {"a": 1}


def test_newer_schema_version_is_left_alone(isolated_appdata) -> None:
    """文件来自更新版本：不认识的配置按原样用，不回写、不改值。"""
    path = desktop_config.config_path()
    original = {"schema_version": desktop_config.CONFIG_VERSION + 99,
                "initial_minutes": 999, "future_feature": True}
    path.write_text(json.dumps(original), encoding="utf-8")
    loaded = desktop_config.load_config()
    assert loaded["initial_minutes"] == 999, "更高版本的值不该被旧版本擅自夹紧"
    assert loaded["future_feature"] is True
    assert json.loads(path.read_text(encoding="utf-8")) == original, "不该回写"


def test_migrate_is_pure_and_reports_change() -> None:
    """`migrate()` 不写盘、不改入参，只用返回值表达结果。"""
    source = {"initial_minutes": 999}
    result, changed = desktop_config.migrate(source)
    assert changed is True
    assert source == {"initial_minutes": 999}, "入参不应被修改"
    assert result["initial_minutes"] == 180
    again, changed_again = desktop_config.migrate(result)
    assert changed_again is False and again == result


# --------------------------------------------------------------------------- #
# P1-F：配置目录按平台约定
# --------------------------------------------------------------------------- #
def test_config_root_windows_keeps_existing_location() -> None:
    """Windows 分支必须逐字节不变 —— 已有用户的配置不能因为这次改动搬家。"""
    root = desktop_config.config_root("win32", {"APPDATA": r"C:/Users/me/AppData/Roaming"})
    assert root == Path(r"C:/Users/me/AppData/Roaming") / "XionghanChess"


def test_config_root_windows_without_appdata_falls_back_to_home() -> None:
    root = desktop_config.config_root("win32", {"HOME": r"C:/Users/me"})
    assert root.name == "XionghanChess"


def test_config_root_macos_uses_application_support() -> None:
    root = desktop_config.config_root("darwin", {"HOME": "/Users/me"})
    assert root == Path("/Users/me/Library/Application Support/XionghanChess")


def test_config_root_linux_uses_xdg_config_home() -> None:
    root = desktop_config.config_root("linux", {"HOME": "/home/me",
                                                "XDG_CONFIG_HOME": "/home/me/.config-custom"})
    assert root == Path("/home/me/.config-custom/xionghan-chess")


def test_config_root_linux_defaults_to_dot_config() -> None:
    root = desktop_config.config_root("linux", {"HOME": "/home/me"})
    assert root == Path("/home/me/.config/xionghan-chess")


def test_config_root_platforms_do_not_collide() -> None:
    """三个平台不能落到同一个目录，否则双系统共享 HOME 时会互相覆盖配置。"""
    roots = {
        desktop_config.config_root("win32", {"APPDATA": "/x", "HOME": "/x"}),
        desktop_config.config_root("darwin", {"HOME": "/x"}),
        desktop_config.config_root("linux", {"HOME": "/x"}),
    }
    assert len(roots) == 3
