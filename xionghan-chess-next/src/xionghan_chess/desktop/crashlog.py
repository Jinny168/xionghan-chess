"""桌面端崩溃日志落盘 —— windowed 构建没有控制台，必须自己留证据。

`packaging/build_windows.spec` 是 `console=False`（PyInstaller windowed）：进程没有
stderr 句柄，用户侧崩溃只会弹一个对话框，`2>file` 也抓不到任何东西。这里补两条
**互相独立**的通道：

- `sys.excepthook`：Python 层未捕获异常 → `crash-<YYYYmmdd-HHMMSS>.log`（含时间、
  Python/PySide6/平台版本与完整 traceback）；
- `faulthandler`：原生层崩溃（Qt/numpy 段错误）→ 常开的 `crash-faulthandler.log`
  （追加）。faulthandler 需要在启动时就持有文件对象，不能等崩溃才打开。

两条通道都**只写异常与调用栈**：不写棋谱、不写账号 token、不写完整 settings。

文件上限：单个日志 > 1 MB 在下次启动/写入前被轮转掉；`crash-*.log` 最多保留最近
5 个，避免无限增长。路径复用 `config.data_dir()`（也就是
`%APPDATA%\\XionghanChess` / `~/Library/Application Support/XionghanChess` /
`$XDG_CONFIG_HOME/xionghan-chess`），不另拼一套来源。
"""

from __future__ import annotations

import datetime
import faulthandler
import platform
import sys
import traceback
from pathlib import Path
from types import TracebackType

from .config import data_dir

CRASH_LOG_LIMIT_BYTES = 1024 * 1024  # 单文件上限 1 MB
CRASH_LOG_KEEP = 5  # crash-*.log 最多保留最近 5 个
CRASH_PREFIX = "crash-"
FAULTHANDLER_FILENAME = "crash-faulthandler.log"


def crash_dir() -> Path:
    """崩溃日志目录；不存在则建。与 settings/statistics/games 同一个 data_dir。"""
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def crash_log_path(now: datetime.datetime | None = None) -> Path:
    """`crash-<YYYYmmdd-HHMMSS>.log`；`now` 可注入，便于测试与确定性命名。"""
    stamp = (now or datetime.datetime.now()).strftime("%Y%m%d-%H%M%S")
    return crash_dir() / f"{CRASH_PREFIX}{stamp}.log"


def faulthandler_log_path() -> Path:
    """常开的原生崩溃日志（进程生命周期内保持打开）。"""
    return crash_dir() / FAULTHANDLER_FILENAME


def _truncate_if_oversized(path: Path, limit: int = CRASH_LOG_LIMIT_BYTES) -> None:
    """超限就丢弃旧内容（轮转）。调用方必须保证此刻没有别的句柄占着该文件。"""
    try:
        if path.exists() and path.stat().st_size > limit:
            path.unlink()
    except OSError:
        # 日志不是关键路径：读不到/删不掉都不能反过来把进程弄崩。
        pass


def _prune_crash_logs(keep: int = CRASH_LOG_KEEP) -> None:
    """只留最近 `keep` 个 `crash-*.log`（按 mtime 倒序），faulthandler 文件不在其列。"""
    try:
        logs = sorted(
            (p for p in crash_dir().glob(f"{CRASH_PREFIX}*.log") if p.name != FAULTHANDLER_FILENAME),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in logs[keep:]:
            stale.unlink(missing_ok=True)
    except OSError:
        pass


def _pyside_version() -> str:
    try:
        import PySide6

        return PySide6.__version__
    except Exception:
        return "unavailable"


def format_uncaught(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: TracebackType | None,
) -> str:
    """崩溃报告正文：版本头 + 完整 traceback（不含任何业务数据）。"""
    body = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    return (
        f"time: {datetime.datetime.now().isoformat(timespec='seconds')}\n"
        f"python: {platform.python_version()} ({sys.executable})\n"
        f"pyside6: {_pyside_version()}\n"
        f"platform: {platform.platform()}\n"
        f"{'-' * 60}\n"
        f"{body}"
    )


def write_uncaught(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: TracebackType | None,
    path: Path | None = None,
) -> Path:
    """把一条未捕获异常写进崩溃日志，返回落盘路径。"""
    target = path or crash_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    _truncate_if_oversized(target)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(format_uncaught(exc_type, exc_value, exc_tb))
        handle.write("\n")
    _prune_crash_logs()
    return target


def install() -> None:
    """安装两条崩溃通道；应在 `QApplication` **之前**调用，启动期崩溃也能留证。"""
    _prune_crash_logs()

    # 保留既有 excepthook 的行为（默认会打印到 stderr；windowed 下为空，但别的
    # 环境/测试里可能有人装着钩子，不能悄悄吞掉）。
    previous = sys.excepthook

    def _hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            write_uncaught(exc_type, exc_value, exc_tb)
        except Exception:
            # 写日志失败绝不能掩盖原始异常，也不能递归触发钩子。
            pass
        previous(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook

    # 已经有人启用过 faulthandler 时不要二次 enable：重复调用会关闭前一个 file，
    # 等于把别人的通道拆掉。
    if faulthandler.is_enabled():
        return
    try:
        path = faulthandler_log_path()
        _truncate_if_oversized(path)
        handle = path.open("ab")  # faulthandler 直接写 fd，用二进制追加避免换行转换
        faulthandler.enable(file=handle, all_threads=True)
    except (OSError, ValueError):
        pass
