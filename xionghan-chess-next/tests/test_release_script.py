"""发布链路脚本的离线守卫：版本源闸门要真的能拦住，dry-run 不许落地。

不跑真实打包（60 秒且要 PyInstaller），只测纯逻辑：
版本源比对、版本资源四元组、EXE 命名、dry-run 不写盘。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from xionghan_chess import __version__

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release.py"


def _module():
    spec = importlib.util.spec_from_file_location("release_for_tests", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_sources_pass_on_the_real_repo() -> None:
    module = _module()
    assert module.check_version_sources() is True
    assert module.check_packaging_resource() is True


def test_version_drift_blocks_the_build(monkeypatch) -> None:
    """把版本改成一个仓库里不存在的值 —— 闸门必须拦住，而不是打出名不符实的包。"""
    module = _module()
    monkeypatch.setattr(module, "__version__", "0.0.0-drift")
    assert module.check_version_sources() is False


def test_exe_name_carries_the_version() -> None:
    module = _module()
    assert module.exe_path().name == f"匈漢象棋-{__version__}-桌面版.exe"


def test_install_dry_run_does_not_touch_disk(tmp_path, monkeypatch) -> None:
    module = _module()
    stub = tmp_path / f"匈漢象棋-{__version__}-桌面版.exe"
    stub.write_bytes(b"stub")
    monkeypatch.setattr(module, "exe_path", lambda: stub)

    dest = tmp_path / "install"
    assert module.install(dest, dry_run=True) is True
    assert not dest.exists(), "dry-run 不该真的建目录或拷文件"
