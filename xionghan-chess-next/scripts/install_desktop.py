"""把桌面版部署到用户级目录，并在桌面放一个可直接双击的入口。

## 为什么不是 `.lnk`

Windows 快捷方式（`.lnk`）本质是一份 Shell Link 二进制，正常做法是用
`WScript.Shell` / `IShellLink` 这两个 COM 接口生成。本机的安全策略**禁止创建
COM 对象**（COM 可以执行任意代码），我实测过一条替代路线：按 MS-SHLLINK 手写
最小实现（76 字节头 + LinkInfo，结构用解析器验过、字段全对），但 shell 仍然
**解析不了** —— 双击无反应，`os.startfile` 也不启动。原因是 Windows 的解析
依赖 `LinkTargetIDList`（ItemIDList），那是 shell 命名空间的不透明二进制，
没有 COM 就没法可靠构造。

所以这里退一步用**符号链接**：双击行为与快捷方式一致（已实测进程能从 0 起
到 1），不带快捷方式的小箭头，且不复制 50+ MB。若哪天 COM 可用，把
`_place_desktop_entry()` 换回 IShellLink 即可。

## 为什么要部署到 LOCALAPPDATA

仓库里的 `release/*.exe` 在 Git 工作树里，工作树重建/清理后入口就断了。
部署到 `%LOCALAPPDATA%\\Programs\\XionghanChess\\` 才是「用户装了一个程序」的
常规位置，重建仓库不影响桌面入口。

用法：
    python scripts/install_desktop.py            # 部署最新构建 + 刷新桌面入口
    python scripts/install_desktop.py --dry-run  # 只看会做什么
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / "XionghanChess"
EXE_NAME = "XionghanChess.exe"
PRODUCT_NAME = "匈漢象棋"          # 桌面入口显示名（文件名由文件系统存 UTF-16，安全）


def newest_release() -> Path:
    candidates = [p for p in RELEASE_DIR.glob("*.exe") if p.is_file()]
    if not candidates:
        raise SystemExit(f"未找到构建产物：{RELEASE_DIR}/*.exe（先跑 packaging/build_windows.spec）")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _place_desktop_entry(target: Path, desktop: Path, dry_run: bool) -> str:
    """桌面入口：优先符号链接；无权限时退回复制（并说明原因）。"""
    link = desktop / f"{PRODUCT_NAME}.exe"
    legacy_lnk = desktop / f"{PRODUCT_NAME}.lnk"
    if dry_run:
        return f"将创建桌面入口：{link} -> {target}"

    # 清掉历史遗留：早期版本的 .lnk 是坏的（见模块说明），留着会是个点不开的图标
    if legacy_lnk.exists():
        legacy_lnk.unlink()
    if link.exists() or link.is_symlink():
        link.unlink()
    try:
        os.symlink(target, link)
        return f"已创建桌面符号链接：{link}"
    except OSError as exc:
        # 开发者模式关闭时普通用户建不了符号链接 —— 退回复制，功能优先
        shutil.copy2(target, link)
        return f"符号链接不可用（{exc.__class__.__name__}），已改为复制：{link}"


def running_instances() -> list[str]:
    """列出正在运行的桌面版进程（PIDs）。

    部署前必须先问这个：Windows 不允许覆盖正在运行的 exe，`shutil.copy2` 会抛
    WinError 32。更糟的是——如果脚本自己去 `taskkill`，会把用户正在下的棋**连同
    未保存的局面一起干掉**。所以这里只检测、不杀，让调用方给出明确提示。
    """
    try:
        completed = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/NH"],
            capture_output=True, text=True, errors="ignore", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.split()[1] for line in completed.stdout.splitlines()
            if line.strip().lower().startswith(EXE_NAME.lower()) and len(line.split()) > 1]


def deploy(dry_run: bool = False) -> int:
    source = newest_release()
    target = APP_DIR / EXE_NAME
    size_mb = source.stat().st_size / 1048576
    print(f"构建产物：{source.name}  {size_mb:.1f} MB")
    print(f"部署位置：{target}")

    busy = running_instances()
    if busy:
        print(f"中止：程序正在运行（PID {', '.join(busy)}）。")
        print("请先关闭匈漢象棋再重新执行 —— 直接覆盖会把这些实例里正在进行的对局丢掉。")
        return 1

    if not dry_run:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if target.stat().st_size != source.stat().st_size:
            raise SystemExit("复制后大小不一致，部署失败")

    desktop = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    # OneDrive 会把桌面重定向，用注册表里的真实路径更稳
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        desktop = Path(os.path.expandvars(value))
    except OSError:
        pass
    print(f"桌面目录：{desktop}（存在：{desktop.is_dir()}）")
    print(_place_desktop_entry(target, desktop, dry_run))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不改文件")
    raise SystemExit(deploy(parser.parse_args().dry_run))
