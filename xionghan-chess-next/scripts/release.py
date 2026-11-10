r"""发布链路：把「打包 → 装到 D 盘 → 回读线上」收成一条命令。

## 为什么要有它

发布这件事以前是四段手工作业，每段都有各自的坑，而且踩过的都记不全：

1. **打包**：`XIONGHAN_EXE_NAME` 里的版本号要手打，写错就产出一个名字对不上的包；
2. **安装**：EXE 正在运行时 `cp` 会 `Device or resource busy`，
   要先重命名再拷（Windows 允许重命名运行中的 EXE）；
3. **部署**：只有会话里的部署工具能做，脚本替不了 —— 所以这一步**明确留给操作者**；
4. **回读**：`verify_deploy.py` 已有，但容易忘。

这个脚本负责 1、2、4 三步的机械动作，并在**每一步之前**做前置校验
（版本源不一致就不许打包），最后把「还差一步部署」明明白白打出来。

## 用法

    python scripts/release.py --check        # 版本源一致性 + 线上回读（最常用，几秒）
    python scripts/release.py --build        # 打包（名字自动取 __version__）
    python scripts/release.py --install      # 装到 D:\匈汉象棋（自动处理占用）
    python scripts/release.py --all-local    # build + install
    python scripts/release.py --verify       # 只回读线上
    python scripts/release.py --build --dry-run   # 只打印将执行的命令

退出码：0 全通过；1 有步骤失败（含线上版本不一致）；2 网络不可达。

## 与部署工具的分工

- **脚本能做**：构建、落地、安装、回读、文件校验
- **脚本不能做**：调用会话里的部署工具（那是模型的工具，不是本地进程）
  → 脚本在 `--all-local` 结束后会打印下一步提示：「现在去部署，部署完再跑 --verify」
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess import __version__  # noqa: E402

DIST = ROOT / "release"
DEFAULT_DEST = Path(r"D:/匈汉象棋")
STABLE_NAME = "匈漢象棋.exe"

# 版本源清单：与 `tests/test_release_version_sources_agree` 同一批文件。
# 打包前先比一遍 —— 名字里带版本号，版本源没同步就打出来的包会「名不符实」。
VERSION_SOURCES = [
    ("src/xionghan_chess/__init__.py", r'__version__ = "{v}"'),
    ("package.json", r'"version": "{v}"'),
    ("android/XionghanChessAndroid.csproj", r"<ApplicationDisplayVersion>{v}</ApplicationDisplayVersion>"),
    ("deploy/docker-compose.yml", r"image: xionghan-chess:{v}"),
    ("android/Resources/assets/offline/welcome.html", r"大厅 · v{v}"),
    ("web/index.html", r"?v={v}"),
]


def _say(mark: str, message: str) -> None:
    print(f"[{mark}] {message}")


def check_version_sources() -> bool:
    """所有版本源都写着当前 `__version__` 吗？"""
    ok = True
    for relative, pattern in VERSION_SOURCES:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        if pattern.format(v=__version__) not in text:
            _say("FAIL", f"{relative} 没有写着 {__version__}")
            ok = False
    if ok:
        _say("OK", f"版本源一致（{len(VERSION_SOURCES)} 处）：{__version__}")
    return ok


def check_packaging_resource() -> bool:
    """`packaging/version_info.txt` 的四元组也要跟上（字符串替换碰不到它）。"""
    text = (ROOT / "packaging/version_info.txt").read_text(encoding="utf-8")
    major, minor, patch = __version__.split(".")
    expected = f"filevers=({major}, {minor}, {patch}, 0)"
    if expected not in text:
        _say("FAIL", f"version_info.txt 的 filevers 不是 {expected}")
        return False
    _say("OK", f"版本资源四元组匹配：{expected}")
    return True


def exe_path() -> Path:
    return DIST / f"匈漢象棋-{__version__}-桌面版.exe"


def build(dry_run: bool = False) -> bool:
    if not (check_version_sources() and check_packaging_resource()):
        _say("STOP", "版本源不一致，拒绝打包 —— 先把版本号同步好")
        return False

    command = [
        str(ROOT / ".venv" / "Scripts" / "pyinstaller.exe"),
        "packaging/build_windows.spec",
        "--noconfirm",
        "--distpath",
        str(DIST),
        "--workpath",
        str(ROOT / "build" / __version__),
    ]
    environment = dict(os.environ, XIONGHAN_EXE_NAME=exe_path().stem)
    _say("RUN", f"打包 {exe_path().name}")
    if dry_run:
        _say("DRY", " ".join(command))
        return True

    started = time.time()
    result = subprocess.run(command, cwd=ROOT, env=environment)  # noqa: S603
    if result.returncode != 0:
        _say("FAIL", f"PyInstaller 退出码 {result.returncode}")
        return False
    if not exe_path().exists():
        _say("FAIL", f"没有产出 {exe_path()}")
        return False

    size = exe_path().stat().st_size
    _say("OK", f"产出 {exe_path().name}（{size / 1048576:.1f} MB，{time.time() - started:.0f}s）")

    probe = ROOT / "scripts" / "probe_exe.py"
    if probe.exists():
        check = subprocess.run([sys.executable, str(probe), str(exe_path())], cwd=ROOT)  # noqa: S603
        _say("OK" if check.returncode == 0 else "FAIL", "启动冒烟 probe_exe.py")
        if check.returncode != 0:
            return False
    return True


def install(dest: Path = DEFAULT_DEST, dry_run: bool = False) -> bool:
    source = exe_path()
    if not source.exists():
        _say("FAIL", f"找不到 {source}，先 --build")
        return False

    target = dest / STABLE_NAME
    versioned = dest / f"匈漢象棋-{__version__}.exe"
    _say("RUN", f"安装到 {target}")
    if dry_run:
        # dry-run 必须在**任何写盘之前**返回 —— 建目录也算写盘（单测抓到过）
        _say("DRY", f"copy {source.name} -> {target}")
        return True

    dest.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source, versioned)  # 版本副本不会被占用，先放
    try:
        shutil.copy2(source, target)
    except OSError:
        # 旧版正在运行 → Windows 允许重命名但不能覆盖，重命名后重新拷
        backup = dest / f"匈漢象棋-旧版-{time.strftime('%Y%m%d-%H%M%S')}.exe"
        _say("NOTE", f"{target.name} 被占用（旧版在运行），重命名为 {backup.name}")
        target.rename(backup)
        shutil.copy2(source, target)

    if target.stat().st_size != source.stat().st_size:
        _say("FAIL", "安装后大小不一致")
        return False
    _say("OK", f"{target}（{target.stat().st_size / 1048576:.1f} MB）+ 版本副本 {versioned.name}")
    return True


def _verify_module():
    spec = importlib.util.spec_from_file_location("verify_deploy_for_release", ROOT / "scripts" / "verify_deploy.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(url: str | None = None) -> int:
    module = _verify_module()
    result = module.check(url or module.DEFAULT_URL, __version__)
    if result["network"]:
        _say("NETWORK", f"无法访问站点：{result['messages']}")
        return 2
    if result["ok"]:
        _say("OK", f"线上版本 {result['version']}，缓存戳 {sorted(result['busters'])}")
        return 0
    _say("FAIL", f"线上版本 {result['version']}，期望 {__version__}")
    for message in result["messages"]:
        print(f"       {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="发布链路：打包 / 安装 / 回读")
    parser.add_argument("--build", action="store_true", help="打包桌面版")
    parser.add_argument("--install", action="store_true", help="装到 D:\\匈汉象棋")
    parser.add_argument("--verify", action="store_true", help="回读线上版本")
    parser.add_argument("--check", action="store_true", help="版本源一致性 + 线上回读")
    parser.add_argument("--all-local", action="store_true", help="打包 + 安装（不含部署）")
    parser.add_argument("--url", default=None, help="回读用的站点地址")
    parser.add_argument("--dest", default=str(DEFAULT_DEST), help="安装目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的命令")
    args = parser.parse_args()

    if not any((args.build, args.install, args.verify, args.check, args.all_local)):
        parser.print_help()
        return 0

    exit_code = 0
    if args.check:
        if not (check_version_sources() and check_packaging_resource()):
            return 1
        exit_code = max(exit_code, verify(args.url))
    if args.build or args.all_local:
        if not build(args.dry_run):
            return 1
    if args.install or args.all_local:
        if not install(Path(args.dest), args.dry_run):
            return 1
        if not args.dry_run:
            _say("NEXT", "现在调用部署工具发布；部署完再跑 `python scripts/release.py --verify`")
    if args.verify and not args.check:
        exit_code = max(exit_code, verify(args.url))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
