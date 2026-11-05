"""Session-wide guards: cross-engine parity gate + desktop user-data isolation.

Two independent guards live here, both keyed on **module path** (no marker, so a
new test cannot forget to opt in):

1. 跨引擎对拍门禁 —— 见下面的长注释（`test_cross_engine.py` 缺 node 时不许静默变绿）。
2. 桌面测试的用户目录隔离 —— 见文件末尾「工程债 ①」那一节（`test_desktop_*`
   一律不许碰真实的 `%APPDATA%/XionghanChess`）。

<br>

--- 以下为第 1 节（对拍门禁）的原始说明 ---

Session-wide guard for the cross-engine parity gate.

``tests/test_cross_engine.py`` is the project's ONLY guard against the Python
(``core/rules.py``) and offline (``android/Resources/assets/offline/offline.js``)
rule engines drifting apart. Every one of its cases self-skips when ``node`` is
missing (``shutil.which("node") is None``), which means that on a machine without
node the whole gate silently evaporates while ``pytest`` still reports a green
run.

This conftest turns that silent skip into a hard **failure** by default: the
parity gate must actually execute. A deliberately node-less environment can opt
back into the old skip behaviour with ``XH_ALLOW_NO_NODE=1``. The number of
parity cases collected / passed / failed / skipped is always printed at the end
so a green line can be told apart from an empty one.

Nothing here touches any assertion in ``test_cross_engine.py``: the per-case
``pytest.skip`` stays as the correct degradation path, we only add a default-fail
gate above it. No marker is registered on the tests themselves (that would mean
editing the parity module); membership is decided by module path.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pytest

NODE = shutil.which("node")
ALLOW_NO_NODE = os.environ.get("XH_ALLOW_NO_NODE") == "1"
PARITY_MODULE = "test_cross_engine.py"

NO_NODE_MESSAGE = (
    "跨引擎对拍无法运行：未在 PATH 中找到 `node`。\n"
    "`tests/test_cross_engine.py` 是本项目唯一的镜像护栏（Python rules.py ↔ "
    "offline.js）；缺 node 时它的用例会各自 skip，等同于护栏静默失效，故这里**默认直接判失败**。\n"
    "  → 请安装 Node.js（>=20）。\n"
    "  → 若确需在无 node 环境运行，设 `XH_ALLOW_NO_NODE=1` 显式放宽（届时对拍用例回到 skip）。"
)

# Collected parity-case count, filled during collection, read at the summary.
_PARITY_TOTAL = 0


def _is_parity(item: pytest.Item) -> bool:
    path = getattr(item, "path", None) or getattr(item, "fspath", "")
    return PARITY_MODULE in str(path)


def pytest_configure(config: pytest.Config) -> None:
    # Greppable intent even though the tests carry no marker themselves.
    config.addinivalue_line(
        "markers", "requires_node: cross-engine parity case that needs a `node` binary"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    global _PARITY_TOTAL, _DESKTOP_TOTAL
    _PARITY_TOTAL = sum(1 for item in items if _is_parity(item))
    _DESKTOP_TOTAL = sum(1 for item in items if _is_desktop_test(item))


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function):
    """Fail the parity module (red) instead of letting it skip to green.

    Runs in the call phase, so the outcome is a genuine FAILURE (not a setup
    error). Any other test, and any run where node is present or explicitly
    waived, returns ``None`` and lets the normal pyfunc call proceed.
    """
    if _is_parity(pyfuncitem) and NODE is None and not ALLOW_NO_NODE:
        pytest.fail(NO_NODE_MESSAGE, pytrace=False)
    return None


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    _parity_summary(terminalreporter)
    _user_data_summary(terminalreporter)


def _parity_summary(terminalreporter) -> None:
    total = _PARITY_TOTAL
    if not total:
        return
    stats = terminalreporter.stats

    def _count(outcome: str) -> int:
        return sum(1 for rep in stats.get(outcome, [])
                   if PARITY_MODULE in getattr(rep, "nodeid", ""))

    passed, failed = _count("passed"), _count("failed")
    skipped, errored = _count("skipped"), _count("error")

    if NODE is None and not ALLOW_NO_NODE:
        state = "node 缺失 → 对拍门禁已按**失败**处理（设 XH_ALLOW_NO_NODE=1 可放宽）"
    elif NODE is None:
        state = "node 缺失，已放宽（XH_ALLOW_NO_NODE=1）→ 对拍用例跳过"
    else:
        state = f"node 可用（{NODE}）"

    terminalreporter.write_sep(
        "=",
        f"跨引擎对拍门禁：收集 {total} 条 | 通过 {passed} | 失败 {failed} | "
        f"跳过 {skipped} | 报错 {errored} | {state}",
    )


# =========================================================================== #
# 工程债 ①：桌面测试的用户目录隔离
#
# 问题：`test_desktop_*` 里建 `MainWindow()` 会走 `load_config()` / `save_config()`，
# 落点是**真实**的 `%APPDATA%\XionghanChess\settings.json`。此前只有两个模块自己
# patch 了 `save_config`，而且 patch 的是 `config.save_config` —— app.py 是
# `from .config import save_config`，拿到了自己的绑定，**拦不住**。实测（2.0.0，
# 1177 条全量跑一遍）：真实 settings.json 的 sha256 从 a1f87f2e… 变成 7f43cf11…，
# `rule_options` 被整块写成 `desktop_complete` 的全量键。
#
# 修法（A 案）不是"再 patch 一个函数"，而是**两层一起上**：
#
#   层①（管落点）把 `APPDATA` / `HOME` / `XDG_CONFIG_HOME` **三个都**指到 tmp。
#     `config.py::config_root()` 按 `sys.platform` 分派：Windows 读 `APPDATA`，
#     darwin 读 `HOME`，linux 读 `XDG_CONFIG_HOME`（缺省 `$HOME/.config`）。
#     只设 `APPDATA` 在 macOS/Linux/CI 上等于**没隔离**，而开发者本机是 Windows，
#     本地一定绿 —— 这正是这种坑能活到 2.0.0 的原因。
#     `LOCALAPPDATA` 不设：全仓无 QSettings / QStandardPaths，没有第二个落点。
#
#   层②（管调用点）把 `app.save_config` 等**真实绑定**换成"记账 + 照旧落盘"的 spy。
#     只隔离则无法断言「这次操作确实存过盘」；只 patch 则会漏掉 `config_path()` 的
#     `mkdir(parents=True)` —— **只读也会建目录**，`load_config()` 迁移回写、以及
#     `piece_atlas` 的第二个写点，都在 patch 之外的路径上。
#
# 两层判据：
#   ① `config.config_root()` 必须真的落在 tmp 下（逐条断言 + session 级汇总）；
#   ② session 结束时，真实 settings.json 的 `(exists, size, sha256)` 必须与 session
#      起始快照**逐字段相同** —— 这是"整轮跑完一个字节都没动"的直接证据。
#
# 不收编 `test_release_script.py`：它只在 tmp 里造 stub exe，完全不碰配置路径。
# 其余 `test_desktop_*` 里已有 `monkeypatch.setenv("APPDATA", tmp_path)` 的模块
# 保留原样（多设一遍无害，autouse 先跑、它们后跑，仍然都指向 tmp）。
# =========================================================================== #

DESKTOP_MODULE_PREFIX = "test_desktop_"

# 收集期统计，仅用于"隔离到底有没有真的挂上"的自检与汇总行。
_DESKTOP_TOTAL = 0
_ISOLATED_ROOTS: list[Path] = []
_GUARD_STATE: dict[str, object] = {}


def _is_desktop_test(node: pytest.Item) -> bool:
    """按**模块文件名**判定，不用 marker。

    用 marker 的话，新写一个 `test_desktop_foo.py` 忘了加装饰器就成了漏网之鱼，
    而且漏了不会有任何提示 —— 与上面那节把 skip 变失败的思路一致：默认兜住。
    """
    path = getattr(node, "path", None) or getattr(node, "fspath", "")
    return Path(str(path)).name.startswith(DESKTOP_MODULE_PREFIX)


def _desktop_config():
    """懒导入 `desktop.config`（纯 Python，不拖 Qt）。

    conftest 在收集期就被加载，导入期把整个 desktop 包拉进来会牵连 PySide6。
    """
    from xionghan_chess.desktop import config as desktop_config

    return desktop_config


def _fingerprint(path: Path) -> tuple[bool, int | None, str | None]:
    """`(存在, 字节数, sha256)`。不存在就是 `(False, None, None)`，不抛异常。

    刻意**不调用** `config_path()`：它自带 `mkdir(parents=True)`，
    「看一眼真实配置」这件事本身就会建目录（正是本轮要拦的那类副作用）。
    """
    try:
        data = path.read_bytes()
    except OSError:
        return False, None, None
    return True, len(data), hashlib.sha256(data).hexdigest()


@dataclass
class IsolatedUserData:
    """`isolated_user_data` 的返回值：落点 + 落盘记账。

    `saves` 记录的是**每一次** `save_config()` 的入参副本，用来断言
    「保存确实发生过」（只隔离 env 是断言不了这件事的）。
    """

    root: Path                 # 配置根（tmp 下），settings.json 的父目录
    settings: Path             # settings.json 的完整路径
    saves: list[dict] = field(default_factory=list)


def _assert_real_config_untouched(who: str) -> None:
    """真实 settings.json 必须仍是 session 起始那一份 `(存在, 字节, sha256)`。

    `who` 只是给失败信息用的时间参照（"上一条用例"/"整轮跑完"）。
    session 级判据只能告诉你"变了"，这条能告诉你"是哪一条变的"。
    """
    before = _GUARD_STATE.get("before")
    real_settings = _GUARD_STATE.get("real_settings")
    if before is None or real_settings is None:
        return
    now = _fingerprint(real_settings)                    # type: ignore[arg-type]
    if now == before:
        return
    pytest.fail(
        f"{who}跑完之后，真实用户配置被改动了 —— 隔离没兜住：\n"
        f"  文件：{real_settings}\n"
        f"  起始：(存在={before[0]}, 字节={before[1]}, sha256={before[2]})\n"
        f"  现在：(存在={now[0]}, 字节={now[1]}, sha256={now[2]})\n"
        "多半是某条 `test_desktop_*` 在 `APPDATA`/`HOME`/`XDG_CONFIG_HOME` 之外"
        "拼了路径，或用别的模块名绑定了 `save_config`（只 patch `config` 模块"
        "拦不住 `from .config import save_config` 的副本）。",
        pytrace=False,
    )


@pytest.fixture()
def isolated_user_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> IsolatedUserData:
    """把桌面端的用户数据目录整体搬到 tmp，并给真实写盘点上记账。"""
    desktop_config = _desktop_config()

    roots = {
        "APPDATA": tmp_path / "appdata",              # Windows 分支
        "HOME": tmp_path / "home",                    # darwin 分支 / Linux 的缺省基线
        "XDG_CONFIG_HOME": tmp_path / "home" / "xdg-config",  # Linux 分支
    }
    for folder in roots.values():
        folder.mkdir(parents=True, exist_ok=True)
    for name, folder in roots.items():
        monkeypatch.setenv(name, str(folder))

    # 滚动对账：**上一个**用例如果绕过隔离写了真实配置，在这里当场点出它的名字。
    # （session 级判据要等收尾才知道，那时已经不知道该怪谁了。）
    _assert_real_config_untouched("上一条用例")

    # 判据①（逐条）：不是"我设了环境变量所以应该隔离了"，而是**问一次配置根**
    # 看它到底落在哪。平台分派写错、变量名拼错，都会在这里当场红。
    root = desktop_config.config_root()
    assert root.is_relative_to(tmp_path), (
        f"配置根没有落进 tmp：{root}（tmp={tmp_path}）。\n"
        "隔离失效，继续跑会写真实的用户配置目录。检查 conftest 里 "
        "APPDATA / HOME / XDG_CONFIG_HOME 是否都设了，"
        "以及 desktop/config.py::config_root 的平台分派是否改过。"
    )
    _ISOLATED_ROOTS.append(root)

    # 判据②（逐条）：以下模块名下的 `save_config` 是**真实绑定**，patch `config`
    # 模块拦不住它们 —— 它们各自 `from ..config import save_config` 拿了副本。
    # 换成一个"记账 + 照旧落盘"的 spy：落盘仍然发生（现在落在 tmp 里），
    # 于是既能断言"保存过"，又不改任何被测行为。
    from xionghan_chess.desktop import app as app_module
    from xionghan_chess.desktop.ui import piece_atlas

    real_save = desktop_config.save_config
    saves: list[dict] = []

    def spy(data: dict) -> None:
        saves.append(dict(data))
        real_save(data)

    monkeypatch.setattr(app_module, "save_config", spy)
    monkeypatch.setattr(piece_atlas, "save_config", spy)
    return IsolatedUserData(root=root, settings=root / "settings.json", saves=saves)


@pytest.fixture(autouse=True)
def _isolate_desktop_user_data(request: pytest.FixtureRequest) -> None:
    """`test_desktop_*` 模块**自动**挂上 `isolated_user_data`，不用逐条声明。

    走 `getfixturevalue` 而不是把 `isolated_user_data` 直接标成 `autouse=True`：
    后者会给 1100+ 条与配置无关的用例也设一遍环境变量，白付代价。
    """
    if _is_desktop_test(request.node):
        request.getfixturevalue("isolated_user_data")


@pytest.fixture(scope="session", autouse=True)
def _real_user_data_guard(tmp_path_factory: pytest.TempPathFactory):
    """session 级两层判据：隔离范围正确 + 真实配置一个字节都没动。"""
    desktop_config = _desktop_config()
    real_settings = desktop_config.config_root() / "settings.json"
    basetemp = Path(tmp_path_factory.getbasetemp())
    _GUARD_STATE.update(real_settings=real_settings,
                        before=_fingerprint(real_settings),
                        basetemp=basetemp)
    yield

    stray = [root for root in _ISOLATED_ROOTS if not root.is_relative_to(basetemp)]
    if stray:
        pytest.fail(
            "有桌面测试的配置根落在 pytest 临时根之外：" + "，".join(map(str, stray)),
            pytrace=False,
        )

    if _DESKTOP_TOTAL and not _ISOLATED_ROOTS:
        pytest.fail(
            f"收集到 {_DESKTOP_TOTAL} 条桌面用例，但隔离 fixture 一次都没生效 —— "
            "模块判定（DESKTOP_MODULE_PREFIX）多半和实际文件名脱钩了。",
            pytrace=False,
        )

    after = _fingerprint(real_settings)
    _GUARD_STATE["after"] = after
    _assert_real_config_untouched("整轮")


def pytest_report_header(config: pytest.Config) -> str:
    """开局打印真实配置的落点与指纹 —— 跑完直接和结尾那行对账。"""
    try:
        real_settings = _desktop_config().config_root() / "settings.json"
    except Exception:  # noqa: BLE001 - 桌面包不可用时不该连累整个 session
        return "用户配置隔离：desktop 包不可导入，跳过"
    exists, size, digest = _fingerprint(real_settings)
    state = f"{size} 字节 / sha256 {digest[:12]}…" if exists else "不存在"
    return f"用户配置隔离：真实落点 {real_settings}（{state}），桌面测试一律改道 tmp"


def _user_data_summary(terminalreporter) -> None:
    """结尾对账一行：跑了一遍，真实用户配置到底动没动。"""
    real_settings = _GUARD_STATE.get("real_settings")
    before = _GUARD_STATE.get("before")
    after = _GUARD_STATE.get("after")
    if real_settings is None or before is None or after is None:
        return
    if not _DESKTOP_TOTAL:
        state = "本轮无桌面用例"
    elif after == before:
        state = "真实配置未改动"
    else:
        state = "**真实配置被改了**（见上方失败信息）"
    exists, size, digest = after
    shown = f"{size} 字节 / sha256 {digest[:12]}…" if exists else "不存在"
    terminalreporter.write_sep(
        "=",
        f"用户配置隔离：桌面用例 {_DESKTOP_TOTAL} 条 | 隔离生效 {len(_ISOLATED_ROOTS)} 次 | "
        f"{real_settings} 现为 {shown} | {state}",
    )


def _user_data_summary(terminalreporter) -> None:
    """结尾对账一行：跑了一遍，真实用户配置到底动没动。"""
    real_settings = _GUARD_STATE.get("real_settings")
    before = _GUARD_STATE.get("before")
    after = _GUARD_STATE.get("after")
    if real_settings is None or before is None or after is None:
        return
    if not _DESKTOP_TOTAL:
        state = "本轮无桌面用例"
    elif after == before:
        state = "真实配置未改动"
    else:
        state = "**真实配置被改了**（见上方失败信息）"
    exists, size, digest = after
    shown = f"{size} 字节 / sha256 {digest[:12]}…" if exists else "不存在"
    terminalreporter.write_sep(
        "=",
        f"用户配置隔离：桌面用例 {_DESKTOP_TOTAL} 条 | 隔离生效 {len(_ISOLATED_ROOTS)} 次 | "
        f"{real_settings} 现为 {shown} | {state}",
    )
