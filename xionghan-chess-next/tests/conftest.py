"""Session-wide guards: cross-engine parity gate + desktop user-data isolation.

Two independent guards live here, both keyed on **module path** (no marker, so a
new test cannot forget to opt in):

1. 跨引擎对拍门禁 —— 见下面的长注释（`test_cross_engine.py` 缺 node 时不许静默变绿）。
2. 桌面测试的用户目录隔离 —— 见文件末尾「工程债 ①」那一节（`test_desktop_*`
   一律不许碰真实的 `%APPDATA%/XionghanChess`）。

   起始快照拍在 **`pytest_configure`**（收集开始之前），判据是
   `(exists, size, mtime_ns, sha256)` 四元组，复检点是**每条桌面用例的 teardown**
   加 session 收尾 —— 三条一起才叫"护栏"，缺哪条都有盲区（理由见那一节的
   「为什么快照必须早于收集」）。

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
import time
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
    # 真实用户配置的**起始快照**必须是这里的第一件事：`pytest_configure` 早于收集，
    # 而收集要 import 每一个测试模块 —— 导入期的写盘是旧版最大的盲区（见文件末尾）。
    _capture_real_config_before("pytest_configure（收集开始之前）")


@pytest.hookimpl(tryfirst=True)
def pytest_collection(session: pytest.Session) -> None:
    """兜底快照点：`pytest_configure` 万一没拍上（pytest 版本换了钩子时序）。

    `pytest_collection` 仍然早于**任何测试模块被 import** —— 所以它退化的只是
    "早一点点"，而不是旧版那种"等收集跑完之后"的真空档。
    """
    _capture_real_config_before("pytest_collection（兜底，仍早于模块导入）")


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
#   ② 真实 settings.json 必须与**起始快照**逐字段相同 —— 这是"一个字节都没动"的直接证据。
#
# ---------------------------------------------------------------------------
# 复审补强（质检判"有条件通过"的两条可靠性缺陷）
#
# 缺陷 A（实测漏检 1/26）：反证时出现过一轮 `51 passed` + 汇总行仍打印
#   "真实配置未改动"，而真实 settings.json 已被改成 46 字节 / 43cfb21a…。
#   根因：起始快照原来拍在 **session 级 fixture** 里，而 session fixture 是
#   **收集完成之后**才实例化的 —— 收集期（模块 import）的写盘落在"起始"之前，
#   于是 `before == after` 永真，护栏对那一类写入**完全瞎**。
#   改法三件（缺一条都还会漏）：
#     1. 快照点前移到 `pytest_configure`（`pytest_collection` 兜底，两处都早于
#        任何测试模块被 import）；
#     2. 复检点从"下一条 setup / 会话末尾"加密到**每条桌面用例的 teardown**；
#     3. 判据从 `(exists, size, sha256)` 换成 `(exists, size, **mtime_ns**, sha256)`。
#        mtime_ns 是必须的：把同一份内容**写回去**（改写但不改内容 —— 迁移回写、
#        `save_config` 收到与磁盘相同的 dict）size 与 sha256 都不变，只有 mtime 会动。
#
# 缺陷 B：失败信息只说"上一条用例跑完之后"，没有 nodeid；pytest 还会把 ERROR 归到
#   **下一条无辜用例**的 setup 上。现在把 nodeid 存进会话级状态：
#     - 逐条 teardown 复检 → 打印"上一条 = `<nodeid>`"（就是刚跑完的那条）；
#     - 逐条 setup 复检   → 打印"上一条 = `<上一条桌面用例的 nodeid>`"；
#     - 会话收尾         → 打印"最后一条桌面用例 = `<nodeid>`"。
#   三处都带时间戳与期望/实际四元组，看到红就能直接定位到人。
# ---------------------------------------------------------------------------

#
# 不收编 `test_release_script.py`：它只在 tmp 里造 stub exe，完全不碰配置路径。
# 早先有 7 个 `test_desktop_*` 模块自带 `monkeypatch.setenv("APPDATA", tmp_path)`；
# 那是这条 autouse 隔离出现之前的**逐模块自救**，现在已被统一接管，7 处全部删除
# （不会再有"某模块忘了隔离"或"某模块隔离得不一样"的两种真相）。
# =========================================================================== #

DESKTOP_MODULE_PREFIX = "test_desktop_"

# 收集期统计，仅用于"隔离到底有没有真的挂上"的自检与汇总行。
_DESKTOP_TOTAL = 0
_ISOLATED_ROOTS: list[Path] = []
# 会话级护栏状态（拍快照的时点、上一条桌面用例、最近一次实测四元组…）。
# 刻意用 dict 而不是全局变量：hook 与 fixture 分布在本文件的四个地方，
# 加一个字段不该改四处签名。
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

    `pytest_configure` 里就要用它算真实落点，所以"懒"只是相对 conftest 的 import
    期而言：`desktop/__init__.py` 是空的，`desktop.config` 只依赖 `core`，不牵连
    PySide6，放在 configure 里安全。
    """
    from xionghan_chess.desktop import config as desktop_config

    return desktop_config


@dataclass(frozen=True)
class RealConfigState:
    """真实 settings.json 的 `(exists, size, mtime_ns, sha256)` 四元组。

    三项都要，不是冗余：
      - `size`    —— 抓截断/追加（46 字节那种最典型）；
      - `sha256`  —— 抓"长度巧合但内容不同"；
      - `mtime_ns`—— 抓**写回同内容**（size 与 sha256 都不动，只有 mtime 会跳）。
    `mtime_ns` 用纳秒：Windows 的 NTFS 是 100ns 粒度，秒级时间戳会把
    "同一秒内的改写"判成没动。
    """

    exists: bool
    size: int | None = None
    mtime_ns: int | None = None
    sha256: str | None = None

    def describe(self) -> str:
        if not self.exists:
            return "不存在"
        import datetime

        moment = datetime.datetime.fromtimestamp(self.mtime_ns / 1e9).isoformat(
            timespec="microseconds")
        return (f"{self.size} 字节 / mtime_ns={self.mtime_ns}（{moment}）/ "
                f"sha256={str(self.sha256)[:12]}…")

    def differing_fields(self, other: RealConfigState) -> list[str]:
        """哪几个字段对不上 —— 失败信息里直接说"变的是长度还是时间还是内容"。"""
        return [name for name in ("exists", "size", "mtime_ns", "sha256")
                if getattr(self, name) != getattr(other, name)]


ABSENT = RealConfigState(exists=False)


def _fingerprint(path: Path) -> RealConfigState:
    """`(存在, 字节数, mtime_ns, sha256)`。不存在就是 `ABSENT`，不抛异常。

    刻意**不调用** `config_path()`：它自带 `mkdir(parents=True)`，
    「看一眼真实配置」这件事本身就会建目录（正是本轮要拦的那类副作用）。
    """
    try:
        stat = path.stat()
        data = path.read_bytes()
    except OSError:
        return ABSENT
    return RealConfigState(exists=True, size=len(data),
                           mtime_ns=stat.st_mtime_ns,
                           sha256=hashlib.sha256(data).hexdigest())


def _real_settings_path() -> Path:
    return _desktop_config().config_root() / "settings.json"


def _capture_real_config_before(origin: str) -> None:
    """拍**起始**快照。幂等：先到的那一次说了算，后面几次只做兜底。

    `origin` 会写进日志/汇总行 —— "快照是在收集之前拍的"是这条护栏的唯一前提，
    得能在输出里看见，不能靠读代码相信。
    """
    if _GUARD_STATE.get("before") is not None:
        return
    try:
        path = _real_settings_path()
    except Exception as exc:  # noqa: BLE001 - 桌面包不可导入不该炸掉整个 session
        _GUARD_STATE["error"] = f"desktop 包不可导入，起始快照拍不了：{exc!r}"
        return
    _GUARD_STATE.update(real_settings=path,
                        before=_fingerprint(path),
                        before_from=origin,
                        before_at=time.strftime("%Y-%m-%d %H:%M:%S"))


def _assert_real_config_untouched(*, phase: str, culprit: str, hint: str = "") -> None:
    """真实 settings.json 必须仍等于起始快照；不等就 red，并把"人"点出来。

    `phase`   —— 什么时候查的（setup / teardown / 会话收尾 + 时间戳）；
    `culprit` —— 最可疑的那一条用例（"上一条 = `<nodeid>`" 之类），单独一行；
    `hint`    —— 这一步特有的排查线索（收集期 vs 用例内）。
    """
    before = _GUARD_STATE.get("before")
    real_settings = _GUARD_STATE.get("real_settings")
    if not isinstance(before, RealConfigState) or real_settings is None:
        return  # 快照没拍上由会话收尾统一判（不许在这里静默变绿）
    now = _fingerprint(Path(real_settings))
    _GUARD_STATE["last_observed"] = now
    if now == before:
        return
    _GUARD_STATE["guard_failed"] = True   # 会话收尾据此避免重复报同一条
    changed = "、".join(before.differing_fields(now))
    pytest.fail(
        "真实用户配置被改动了 —— 隔离没兜住：\n"
        f"  时点：{phase}（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n"
        f"  {culprit}\n"
        f"  真实文件：{real_settings}\n"
        f"  期望（{_GUARD_STATE.get('before_from')} 拍的快照，{_GUARD_STATE.get('before_at')}）："
        f"{before.describe()}\n"
        f"  实际（刚刚实测）：{now.describe()}\n"
        f"  变了的字段：{changed}\n"
        "  多半是某条 `test_desktop_*` 在 `APPDATA`/`HOME`/`XDG_CONFIG_HOME` 之外"
        "拼了路径，或用别的模块名绑定了 `save_config`（只 patch `config` 模块"
        "拦不住 `from .config import save_config` 的副本）。"
        + (f"\n  {hint}" if hint else ""),
        pytrace=False,
    )


@dataclass
class IsolatedUserData:
    """`isolated_user_data` 的返回值：落点 + 落盘记账。

    `saves` 记录的是**每一次** `save_config()` 的入参副本，用来断言
    「保存确实发生过」（只隔离 env 是断言不了这件事的）。
    """

    root: Path                 # 配置根（tmp 下），settings.json 的父目录
    settings: Path             # settings.json 的完整路径
    saves: list[dict] = field(default_factory=list)


@pytest.fixture()
def isolated_user_data(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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

    # 判据①（逐条）：不是"我设了环境变量所以应该隔离了"，而是**问一次配置根**
    # 看它到底落在哪。平台分派写错、变量名拼错，都会在这里当场红。
    root = desktop_config.config_root()
    assert root.is_relative_to(tmp_path), (
        f"配置根没有落进 tmp：{root}（tmp={tmp_path}）。\n"
        "隔离失效，继续跑会写真实的用户配置目录。检查 conftest 里 "
        "APPDATA / HOME / XDG_CONFIG_HOME 是否都设了，"
        "以及 desktop/config.py::config_root 的平台分派是否改过。"
    )
    # 先记账再复检：复检失败时"隔离生效次数"仍然是真数 —— 否则会话收尾会再补一条
    # 「隔离 fixture 一次都没生效」的误导性失败（真正的原因是复检本身红了）。
    _ISOLATED_ROOTS.append(root)

    # 滚动对账：**上一条**桌面用例如果绕过隔离写了真实配置，在这里当场点出它的名字
    # （nodeid 由 `_isolate_desktop_user_data` 的 teardown 记下 —— 见缺陷 B）。
    previous = _GUARD_STATE.get("last_desktop_nodeid")
    _assert_real_config_untouched(
        phase=f"`{request.node.nodeid}` 的 setup（上一条收尾之后、本条开跑之前）",
        culprit=("上一条 = `" + str(previous) + "`" if previous
                 else "上一条 = （无：本条是第一条拿到隔离的桌面用例）"),
        hint="这条红在下一条用例的 setup 上，但**不是下一条的错** —— 真正动手的是"
             "「上一条」那条用例的 teardown，或者收集期（模块 import）的写盘。",
    )

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
def _isolate_desktop_user_data(request: pytest.FixtureRequest):
    """`test_desktop_*` 模块**自动**挂上 `isolated_user_data`，不用逐条声明。

    走 `getfixturevalue` 而不是把 `isolated_user_data` 直接标成 `autouse=True`：
    后者会给 1100+ 条与配置无关的用例也设一遍环境变量，白付代价。

    除了挂隔离，这里还承担**逐条 teardown 复检**：旧版只在"下一条 setup"和
    "会话收尾"查，中间隔着一条用例的 teardown（关窗、`atexit` 之类）以及
    最后一条用例之后的整段收尾 —— 那些写入只能等到"轮末"才发现归责不清。
    现在每条桌面用例跑完的当口就查一次，红在哪条，哪条就是嫌疑人。
    """
    if not _is_desktop_test(request.node):
        yield
        return

    nodeid = request.node.nodeid
    request.getfixturevalue("isolated_user_data")   # 内部含 setup 侧的滚动复检
    _GUARD_STATE["last_desktop_nodeid"] = nodeid    # 供下一条 setup / 会话收尾引用
    yield
    _assert_real_config_untouched(
        phase=f"`{nodeid}` 的 teardown（本条跑完的当口）",
        culprit=f"上一条 = `{nodeid}`",
        hint="本条 teardown 是**逐条**复检点。若这条用例本身没碰真实配置，"
             "嫌疑就在**收集期**（某个测试模块在 import 时写盘）—— "
             "那种写入只有早于收集的起始快照才抓得到。",
    )


@pytest.fixture(scope="session", autouse=True)
def _real_user_data_guard(tmp_path_factory: pytest.TempPathFactory):
    """session 级判据：隔离范围正确 + 真实配置一个字节都没动。

    ⚠️ 起始快照**不在这里**拍。session fixture 是收集结束之后才实例化的，
    在这里拍就等于对收集期写盘完全瞎 —— 那正是"汇总行说没改动、文件其实变了"的
    根因。这里只在 configure/collection 两级都没拍成的极端情况下兜底，并在收尾时
    **显式判失败**（宁可红，不要静默绿）。
    """
    basetemp = Path(tmp_path_factory.getbasetemp())
    _GUARD_STATE["basetemp"] = basetemp
    _capture_real_config_before("session fixture（收集之后，仅兜底）")
    yield

    real_settings = _GUARD_STATE.get("real_settings")
    after = _fingerprint(Path(real_settings)) if real_settings is not None else None
    _GUARD_STATE["after"] = after          # 先落盘，保证下面无论怎么红汇总行都有数

    stray = [root for root in _ISOLATED_ROOTS if not root.is_relative_to(basetemp)]
    if stray:
        pytest.fail(
            "有桌面测试的配置根落在 pytest 临时根之外：" + "，".join(map(str, stray)),
            pytrace=False,
        )

    if _DESKTOP_TOTAL and not _ISOLATED_ROOTS and not _GUARD_STATE.get("guard_failed"):
        pytest.fail(
            f"收集到 {_DESKTOP_TOTAL} 条桌面用例，但隔离 fixture 一次都没生效 —— "
            "模块判定（DESKTOP_MODULE_PREFIX）多半和实际文件名脱钩了。",
            pytrace=False,
        )

    if _DESKTOP_TOTAL and _GUARD_STATE.get("before") is None:
        pytest.fail(
            "真实配置的起始快照**一次都没拍成**，这条护栏等于没开：\n"
            f"  原因：{_GUARD_STATE.get('error', '未知')}\n"
            "  → `pytest_configure` / `pytest_collection` 里 `_capture_real_config_before`"
            " 必须能导入 `xionghan_chess.desktop.config`（它纯 Python，不依赖 PySide6）。\n"
            "  → 宁可红也不要静默绿：没有起始快照就无法判断整轮跑完有没有动真实配置。",
            pytrace=False,
        )

    late = str(_GUARD_STATE.get("before_from", ""))
    if _DESKTOP_TOTAL and late.startswith("session fixture"):
        pytest.fail(
            "起始快照是在**收集之后**才拍到的（退化到 session fixture 兜底）—— "
            "收集期（测试模块 import）的写盘会成为盲区，护栏不可信：\n"
            f"  快照时点：{late}\n"
            "  → 检查 `pytest_configure` 是否还在，以及它能否导入 desktop.config。",
            pytrace=False,
        )

    if _GUARD_STATE.get("guard_failed"):
        return                             # 逐条复检已经报过，别把同一个现象报两遍
    _assert_real_config_untouched(
        phase="整轮跑完（session 收尾）",
        culprit=("最后一条桌面用例 = `"
                 + str(_GUARD_STATE.get("last_desktop_nodeid", "（无）")) + "`"),
    )


def pytest_report_header(config: pytest.Config) -> str:
    """开局打印真实落点、起始快照，以及**快照是在哪个时点拍的**。

    "快照早于收集"是这条护栏唯一的立足点，所以连同"什么时候拍的"一起打出来 ——
    跑完直接和结尾那行对账，不用回头翻代码。
    """
    before = _GUARD_STATE.get("before")
    if not isinstance(before, RealConfigState):
        return f"用户配置隔离：起始快照未拍成（{_GUARD_STATE.get('error', '未知')}）"
    return (
        f"用户配置隔离：真实落点 {_GUARD_STATE['real_settings']}"
        f"（起始 {before.describe()}）\n"
        f"               快照时点：{_GUARD_STATE.get('before_from')}"
        f" @ {_GUARD_STATE.get('before_at')}；桌面测试一律改道 tmp，"
        "每条用例 teardown 复检一次"
    )


def _user_data_summary(terminalreporter) -> None:
    """结尾对账一行：跑了一遍，真实用户配置到底动没动。

    判据与失败信息同源（四元组），并把**快照时点**印在同一行 —— 只要那行写的
    不是「收集开始之前」，这轮的"未改动"就不算证据。
    """
    real_settings = _GUARD_STATE.get("real_settings")
    before = _GUARD_STATE.get("before")
    after = _GUARD_STATE.get("after")
    base = (f"用户配置隔离：桌面用例 {_DESKTOP_TOTAL} 条 | "
            f"隔离生效 {len(_ISOLATED_ROOTS)} 次 | ")
    if not isinstance(before, RealConfigState):
        terminalreporter.write_sep(
            "=", base + "**起始快照没拍上 → 本轮护栏未生效，覆盖为零**")
        return
    if real_settings is None:
        return
    if not isinstance(after, RealConfigState):
        terminalreporter.write_sep("=", base + "**收尾没读到真实配置**")
        return
    if not _DESKTOP_TOTAL:
        state = "本轮无桌面用例"
    elif after == before:
        state = "真实配置未改动（exists/size/mtime_ns/sha256 四元组逐字段相等）"
    else:
        state = "**真实配置被改了**（见上方失败信息）"
    terminalreporter.write_sep(
        "=",
        f"{base}{real_settings} 现为 {after.describe()} | {state} | "
        f"快照时点 {_GUARD_STATE.get('before_from')}",
    )
