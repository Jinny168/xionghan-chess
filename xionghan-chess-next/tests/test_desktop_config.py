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

import datetime
import json
import os
import sys
from pathlib import Path

import pytest

from xionghan_chess.desktop import config as desktop_config


@pytest.fixture()
def isolated_appdata(tmp_path, monkeypatch):
    """把**全部平台的配置根**都指进临时目录，隔离真实用户配置。

    只改 APPDATA 不够：`config_root()` 在 Linux 读 `XDG_CONFIG_HOME`、macOS 读
    `HOME`。CI 上 desktop smoke 先于 pytest 跑，且 ci.yml 给两个 step 共用同一个
    `XDG_CONFIG_HOME`（$RUNNER_TEMP/xdg-config）——smoke 的 load_config /
    _apply_settings 会在那里留下 settings.json，「file absent」前提被 **step 顺序**
    打破（#123 实证：本用例读到 smoke 留下的 profile=traditional；Windows 本机
    永远复现不了，因为 smoke 不在 pytest 前跑）。三个 env 全指进 tmp_path 后，
    用例与 CI step 顺序解耦。
    """
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path


# --------------------------------------------------------------------------- #
# 默认值完整性
# --------------------------------------------------------------------------- #


def test_defaults_declares_server_url() -> None:
    """S1-1 修复的回归守卫：server_url 必须在 DEFAULTS 里。"""
    assert "server_url" in desktop_config.DEFAULTS
    assert desktop_config.DEFAULTS["server_url"] == desktop_config.DEFAULT_SERVER_URL


# --------------------------------------------------------------------------- #
# B2：每方时限默认 20 → 10 分钟
# --------------------------------------------------------------------------- #


def test_initial_minutes_defaults_to_ten(isolated_appdata) -> None:
    """首次运行（没有配置文件）→ 10 分钟。"""
    assert desktop_config.DEFAULTS["initial_minutes"] == 10
    assert desktop_config.load_config()["initial_minutes"] == 10


def test_existing_initial_minutes_is_not_overwritten(isolated_appdata) -> None:
    """B2 只改**默认值**：用户配置里已经写着的 20 分钟必须原样保留。

    这条是"改默认值"最容易踩的坑 —— 顺手写成"总是写成新默认"就等于把
    老用户的选择悄悄抹掉。
    """
    path = desktop_config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": desktop_config.CONFIG_VERSION, "initial_minutes": 20}), encoding="utf-8"
    )
    assert desktop_config.load_config()["initial_minutes"] == 20


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
    assert json.loads(after_first)["initial_minutes"] == 10, "迁移应把坏值收敛成默认值"

    second = desktop_config.load_config()
    assert first == second
    assert path.read_text(encoding="utf-8") == after_first, "第二次读取不该再改文件"


@pytest.mark.parametrize(
    "key,raw,expected",
    [
        ("initial_minutes", 999, 180),
        ("initial_minutes", 0, 1),
        ("initial_minutes", "abc", 10),
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
    desktop_config.config_path().write_text(json.dumps({"theme": "dark", "future_feature": {"a": 1}}), encoding="utf-8")
    loaded = desktop_config.load_config()
    assert loaded["future_feature"] == {"a": 1}


def test_newer_schema_version_is_left_alone(isolated_appdata) -> None:
    """文件来自更新版本：不认识的配置按原样用，不回写、不改值。"""
    path = desktop_config.config_path()
    original = {"schema_version": desktop_config.CONFIG_VERSION + 99, "initial_minutes": 999, "future_feature": True}
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
    root = desktop_config.config_root("linux", {"HOME": "/home/me", "XDG_CONFIG_HOME": "/home/me/.config-custom"})
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


# --------------------------------------------------------------------------- #
# v1 -> v2 迁移：让 2.0.0 的兵规则默认值对**老用户**真正生效
# --------------------------------------------------------------------------- #


def _write_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_migration_drops_deleted_option_and_stale_backward_key(isolated_appdata) -> None:
    """老配置里显式存着 `pawn_backward_at_base: true` 与已删除的 `pawn_full_movement_at_base`。

    不删这两个键的话 `RuleOptions.merged()` 会用存量的 `true` 盖掉新默认值 ——
    也就是说"改默认值"**只对全新安装生效**，老用户升级后底线兵照样能后退。
    这是本轮最容易白干的地方，所以断言要看**实际行为**，不是只看默认值。
    """
    path = desktop_config.config_path()
    _write_config(
        path,
        {
            "schema_version": 1,
            "rule_options": {
                "pawn_backward_at_base": True,
                "pawn_full_movement_at_base": True,  # 2.0.0 已删除的选项
                "pawn_charge": True,  # 用户真的改过的项，必须保留
            },
        },
    )
    loaded = desktop_config.load_config()
    options = loaded["rule_options"]
    assert "pawn_backward_at_base" not in options, "存量键必须被清掉，否则新默认值被覆盖"
    assert "pawn_full_movement_at_base" not in options, "已删除选项的残键必须被清掉"
    assert options.get("pawn_charge") is True, "用户真的改过的项不许动"

    # 行为断言：用迁移后的配置开一局，底线兵**不能后退**（横走仍在）
    from xionghan_chess.core.model import Color, GameState, Piece, PieceType
    from xionghan_chess.core.profiles import get_profile
    from xionghan_chess.core.rules import RulesEngine

    profile = get_profile("desktop_complete")
    # 关掉升变才看得到"能不能后退"：开升变时底线落子必须带 promotion，着法会被展开
    rules = RulesEngine(profile, profile.options.merged({**options, "pawn_promotion": False}))
    board = GameState(
        "desktop_complete",
        [
            Piece.create(PieceType.KING, Color.RED, 12, 0),
            Piece.create(PieceType.KING, Color.BLACK, 2, 9),
            Piece.create(PieceType.PAWN, Color.RED, 0, 4),
        ],
    )
    targets = {(m.target.row, m.target.col) for m in rules.legal_moves(board) if (m.source.row, m.source.col) == (0, 4)}
    assert (1, 4) not in targets, "迁移后底线兵仍能后退 —— 存量键没清干净"
    assert (0, 3) in targets, "横走应当还在（由 crossed 放行，与这个开关无关）"


def test_migration_does_not_trigger_a_restart_on_first_settings_save() -> None:
    """迁移删了键，设置窗口保存的是**全量键** —— 不能因此判成"规则变了"重开对局。

    老用户升级后第一次点「确定」就丢掉正在下的一局，是本轮最贵的潜在事故。
    """
    old = dict(desktop_config.DEFAULTS)
    old["rule_options"] = {"pawn_charge": True}  # 迁移后的存量（缺键）
    new = dict(old)
    new["rule_options"] = dict(old["rule_options"], pawn_backward_at_base=False)  # 设置窗口写回全量
    assert desktop_config.settings_differ_in_game_breaking_keys(old, new) is False


def test_migration_is_idempotent() -> None:
    """连跑两次：第二次 `changed=False`，不产生无谓写盘。"""
    raw = {"schema_version": 1, "rule_options": {"pawn_backward_at_base": True, "pawn_full_movement_at_base": True}}
    once, changed_once = desktop_config.migrate(raw)
    assert changed_once is True
    twice, changed_twice = desktop_config.migrate(once)
    assert changed_twice is False, "第二次迁移不该再报改动"
    assert twice == once, "幂等：两次结果必须一致"


# --------------------------------------------------------------------------- #
# windowed 崩溃日志：console=False 没有 stderr，崩溃证据只能自己留
# --------------------------------------------------------------------------- #
def test_crash_log_path_lives_under_data_dir(isolated_appdata) -> None:
    """崩溃日志必须落在 data_dir（与 settings/statistics 同一个来源），且带时间戳。"""
    from xionghan_chess.desktop import crashlog

    path = crashlog.crash_log_path(datetime.datetime(2026, 11, 11, 13, 53, 7))
    assert path.name == "crash-20261111-135307.log"
    assert path.parent == desktop_config.data_dir()
    assert path.parent.is_dir(), "crash_dir() 应当顺手建好目录"


def test_faulthandler_path_lives_under_data_dir(isolated_appdata) -> None:
    from xionghan_chess.desktop import crashlog

    assert crashlog.faulthandler_log_path() == desktop_config.data_dir() / "crash-faulthandler.log"


def test_write_uncaught_records_traceback_and_versions(isolated_appdata) -> None:
    """一条未捕获异常落盘后，文件里必须有 traceback、异常消息与版本头。"""
    from xionghan_chess.desktop import crashlog

    try:
        raise RuntimeError("boom-marker-42")
    except RuntimeError:
        target = crashlog.write_uncaught(*sys.exc_info())

    text = target.read_text(encoding="utf-8")
    assert target.parent == desktop_config.data_dir()
    assert target.name.startswith("crash-")
    assert "Traceback (most recent call last)" in text
    assert "RuntimeError: boom-marker-42" in text
    assert "python:" in text
    assert "pyside6:" in text


def test_prune_keeps_only_five_crash_logs(isolated_appdata) -> None:
    """crash-*.log 最多保留最近 5 个；faulthandler 文件不计入。"""
    from xionghan_chess.desktop import crashlog

    folder = desktop_config.data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(8):
        path = folder / f"crash-2026111100000{index}.log"
        path.write_text("x", encoding="utf-8")
        os.utime(path, (index + 1, index + 1))  # mtime 递增：最新是 index=7
    crashlog._prune_crash_logs()

    remaining = sorted(p.name for p in folder.glob("crash-*.log"))
    assert len(remaining) == 5
    assert "crash-20261111000003.log" in remaining  # 保留 mtime 4..8 这 5 个
    assert "crash-20261111000002.log" not in remaining


def test_oversized_log_is_rotated(isolated_appdata) -> None:
    from xionghan_chess.desktop import crashlog

    target = desktop_config.data_dir() / "crash-oversize.log"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * (crashlog.CRASH_LOG_LIMIT_BYTES + 1))
    crashlog._truncate_if_oversized(target)
    assert not target.exists()


# --------------------------------------------------------------------------- #
# v2 配置的手改坏值：不迁移也必须收敛（否则 audio.py 启动期 int("loud") 崩溃）
# --------------------------------------------------------------------------- #


def test_v2_config_with_bad_numbers_is_converged(isolated_appdata) -> None:
    """`schema_version == 2` 不进迁移循环，但数值键仍要收敛。

    回归的是一条真实启动崩溃：`audio.py` 里 `int(config.get("sound_volume", 70))`
    遇到手改的 `"loud"` 抛 ValueError，发生在 `MainWindow.__init__`。
    """
    path = desktop_config.config_path()
    _write_config(
        path,
        {"schema_version": desktop_config.CONFIG_VERSION, "initial_minutes": "abc", "sound_volume": "loud"},
    )
    loaded = desktop_config.load_config()
    assert loaded["initial_minutes"] == desktop_config.DEFAULTS["initial_minutes"] == 10
    assert loaded["sound_volume"] == desktop_config.DEFAULTS["sound_volume"] == 70
    assert isinstance(loaded["initial_minutes"], int)
    assert isinstance(loaded["sound_volume"], int)
    assert desktop_config.load_config() == loaded, "收敛必须幂等"


def test_v2_bad_numbers_do_not_touch_other_keys(isolated_appdata) -> None:
    """收敛只碰数值键：字符串 / 布尔键的语义不能被顺手改写。"""
    path = desktop_config.config_path()
    _write_config(
        path,
        {
            "schema_version": desktop_config.CONFIG_VERSION,
            "sound_volume": "loud",
            "theme": "dark",
            "sound": False,
            "language": "en",
        },
    )
    loaded = desktop_config.load_config()
    assert loaded["sound_volume"] == 70
    assert loaded["theme"] == "dark"
    assert loaded["sound"] is False
    assert loaded["language"] == "en"


def test_v2_bad_numbers_are_converged_without_rewriting_the_file(isolated_appdata) -> None:
    """收敛是**读时**行为：不因为夹紧而写盘（只读目录在加载时不该出错）。"""
    path = desktop_config.config_path()
    _write_config(path, {"schema_version": desktop_config.CONFIG_VERSION, "sound_volume": "loud"})
    before = path.read_text(encoding="utf-8")
    assert desktop_config.load_config()["sound_volume"] == 70
    assert path.read_text(encoding="utf-8") == before


# --------------------------------------------------------------------------- #
# B 项：1.6.x 棋子美术偏好的加载时纠错（cartoon 不能被静默改回 glyph）
# --------------------------------------------------------------------------- #


def _write_legacy_config(path: Path, style: str) -> None:
    """1.6.x 存量的真实形状：有 `piece_style`，**没有** `piece_render`。"""
    _write_config(path, {"schema_version": desktop_config.CONFIG_VERSION, "piece_style": style})


def _assert_three_places_consistent(config: dict, style: str) -> None:
    """棋盘 / 设置 / 图谱三处都读这两个键，必须指向同一套美术。

    - 棋盘：`board_widget.py:499,1283` 按 `piece_render` 选图片路径、`piece_style` 选美术；
    - 设置：`dialogs.py:207-210` 下拉当前项读 `piece_style`，`:424-425` 按 `piece_render`
      决定落在「书法字形」回退项还是三套美术之一；
    - 图谱：`piece_atlas.py:475` 的「使用中」直接比 `config["piece_style"] == choice`。
    """
    assert config["piece_style"] == style
    assert config["piece_render"] == "image"
    # `QA_PIECE_ATLAS.md:89` 红线：不得出现「设置显示 A、棋盘/图谱为 B」的中间态
    assert (config["piece_style"], config["piece_render"]) != (style, "glyph")


def test_legacy_cartoon_choice_is_preserved_with_image_render(isolated_appdata) -> None:
    """1.6.x 显式选过 cartoon 的用户：升级后仍是 cartoon/image，三处一致。

    选 cartoon 被改回 glyph 是「1.7.0 程序补 `piece_render` 默认」+「1.7.1 把补出的
    值当用户意图」叠加的结果；这条把这组配置钉成回归守卫。
    """
    path = desktop_config.config_path()
    _write_legacy_config(path, "cartoon")

    loaded = desktop_config.load_config()
    _assert_three_places_consistent(loaded, "cartoon")

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    _assert_three_places_consistent(on_disk, "cartoon")


@pytest.mark.parametrize("style", ["traditional", "modern", "cartoon"])
def test_legacy_art_style_whitelist(isolated_appdata, style: str) -> None:
    """三套美术都在白名单内；白名单外的 `glyph` / 未知值不进纠错。"""
    _write_legacy_config(desktop_config.config_path(), style)
    _assert_three_places_consistent(desktop_config.load_config(), style)


def test_explicit_glyph_render_stays_glyph(isolated_appdata) -> None:
    """2.x 明确选字形：`piece_render="glyph"` 键存在 → 原逻辑，glyph/glyph 不变且不回写。"""
    path = desktop_config.config_path()
    original = {"schema_version": desktop_config.CONFIG_VERSION, "piece_style": "glyph", "piece_render": "glyph"}
    _write_config(path, original)

    loaded = desktop_config.load_config()
    assert (loaded["piece_style"], loaded["piece_render"]) == ("glyph", "glyph")
    assert json.loads(path.read_text(encoding="utf-8")) == original, "值没变就不该回写"


def test_v2_explicit_image_style_is_untouched(isolated_appdata) -> None:
    """2.x 选过风格：`piece_render="image"` + `piece_style="cartoon"` → 原样保留。"""
    path = desktop_config.config_path()
    original = {"schema_version": desktop_config.CONFIG_VERSION, "piece_style": "cartoon", "piece_render": "image"}
    _write_config(path, original)

    loaded = desktop_config.load_config()
    _assert_three_places_consistent(loaded, "cartoon")
    assert json.loads(path.read_text(encoding="utf-8")) == original, "现状路径不该回写"


def test_user_who_switched_back_to_glyph_is_not_corrected(isolated_appdata, monkeypatch) -> None:
    """「先 cartoon、再主动切回字形」→ 四值互斥写成 `piece_style="glyph"`，不在白名单。

    裁决 B-1 第 4 条的代码级落点：该用户当下的选择就是字形，纠错不应命中。
    互斥契约见 `tests/test_desktop_piece_settings.py:80-83`。
    """
    path = desktop_config.config_path()
    _write_config(
        path,
        {
            "schema_version": desktop_config.CONFIG_VERSION,
            "piece_style": "glyph",
            "piece_render": "glyph",
            "theme": "dark",  # 一个真实 2.x 用户配置的其他键，确认不被顺手改掉
        },
    )
    calls: list[tuple[object, object]] = []
    real = desktop_config._normalize_piece_style

    def spy(style: object, render: object) -> tuple[str, str]:
        calls.append((style, render))
        return real(style, render)

    monkeypatch.setattr(desktop_config, "_normalize_piece_style", spy)
    loaded = desktop_config.load_config()
    assert (loaded["piece_style"], loaded["piece_render"]) == ("glyph", "glyph")
    assert loaded["theme"] == "dark"
    assert len(calls) == 1, "应走 2.x 现状分支，而不是纠错分支"


def test_legacy_correction_is_rewritten_and_survives_restart(isolated_appdata, monkeypatch) -> None:
    """纠错必须落盘；第二次启动读到带 `piece_render` 的磁盘值，走现状路径、不再重判。"""
    path = desktop_config.config_path()
    _write_legacy_config(path, "cartoon")

    real = desktop_config._normalize_piece_style
    first_calls: list[tuple[object, object]] = []

    def spy_first(style: object, render: object) -> tuple[str, str]:
        first_calls.append((style, render))
        return real(style, render)

    monkeypatch.setattr(desktop_config, "_normalize_piece_style", spy_first)
    first = desktop_config.load_config()
    assert first_calls == [], "1.6.x 存量应跳过 _normalize_piece_style（否则 :340 又改回 glyph）"
    _assert_three_places_consistent(first, "cartoon")
    after_first = path.read_text(encoding="utf-8")
    assert json.loads(after_first)["piece_render"] == "image", "纠错必须回写，不能只改内存"

    second_calls: list[tuple[object, object]] = []

    def spy_second(style: object, render: object) -> tuple[str, str]:
        second_calls.append((style, render))
        return real(style, render)

    monkeypatch.setattr(desktop_config, "_normalize_piece_style", spy_second)
    second = desktop_config.load_config()
    assert second == first, "重启前后配置必须一致"
    assert len(second_calls) == 1, "第二次启动应走 2.x 现状路径"
    assert path.read_text(encoding="utf-8") == after_first, "第二次启动不该再改磁盘"
