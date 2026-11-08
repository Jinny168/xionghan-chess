"""打包产物冒活探针：用副作用判断 EXE 真的跑起来了。

为什么不能只看「进程还在」：PyInstaller 单文件包如果缺插件或 DLL，典型表现是
**窗口一闪而过 / 弹个英文错误框 / 静默退出**，而 `--windowed` 没有控制台，
日志会直接丢掉。所以判据取可观测的副作用：

1. `%APPDATA%\\XionghanChess\\` 被创建（`config.data_dir()` 在启动链上）；
2. 进程在 N 秒后仍存活（说明没有启动即崩）。

用法（本脚本需要在仓库根目录运行）：
    python scripts/probe_exe.py release/s26-spec/s26-spec.exe
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_DIR_NAME = "XionghanChess"


def probe(exe: Path, wait_seconds: float = 45.0) -> int:
    if not exe.is_file():
        print(f"FAIL 产物不存在：{exe}")
        return 1
    sandbox = Path(tempfile.mkdtemp(prefix="xionghan-exe-probe-"))
    env = dict(os.environ)
    env["APPDATA"] = str(sandbox)
    print(f"产物 {exe.name}  {exe.stat().st_size:,} B")
    print(f"临时 APPDATA: {sandbox}")

    process = subprocess.Popen([str(exe)], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    target = sandbox / APP_DIR_NAME
    deadline = time.time() + wait_seconds
    created = False
    while time.time() < deadline:
        if target.is_dir():
            created = True
            break
        if process.poll() is not None:
            break
        time.sleep(0.5)

    alive = process.poll() is None
    files = sorted(p.name for p in target.rglob("*"))[:8] if target.is_dir() else []

    if alive:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    print(f"  {'OK  ' if created else 'FAIL'} 数据目录已创建：{target}")
    if files:
        print(f"       其中：{', '.join(files)}")
    print(f"  {'OK  ' if alive else 'FAIL'} 启动后仍存活（未即崩）")
    passed = created and alive
    print("EXE_PROBE_OK" if passed else "EXE_PROBE_FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法: python scripts/probe_exe.py <exe 路径>")
    raise SystemExit(probe(Path(sys.argv[1])))
