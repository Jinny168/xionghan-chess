"""打包 spec 的裁剪清单守卫（阶段2 S2-6）。

`packaging/build_windows.spec` 里有一份 `DROP_BINARIES` —— 打包时会被真的从产物里
删掉的文件名。删对了省 18 MB，删错了**不会有任何报错**，只会在用户机器上表现为
「一放音乐就崩」「连不上服务器」「消息框按钮变英文」。所以这里把
「必须留」与「必须删」两侧都钉住。

本文件只读 spec 文本，不需要 Windows、不需要 PyInstaller。
"""

from __future__ import annotations

import ast
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "packaging" / "build_windows.spec"


def drop_list() -> set[str]:
    tree = ast.parse(SPEC.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "DROP_BINARIES"
                for target in node.targets):
            return {element.value for element in node.value.elts}
    raise AssertionError("spec 里找不到 DROP_BINARIES 定义")


def test_spec_builds_onefile_not_onedir() -> None:
    """产物必须是单文件：COLLECT 的存在意味着变成目录分发。"""
    source = SPEC.read_text(encoding="utf-8")
    assert "EXE(" in source
    assert "COLLECT(" not in source.replace("# ", "")


def test_runtime_loaded_qt_binaries_are_never_dropped() -> None:
    """实测装配链只加载 6 个 Qt 子模块 —— 它们的二进制必须留着。"""
    dropped = drop_list()
    critical = {
        "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll",
        "QtCore.pyd", "QtGui.pyd", "QtWidgets.pyd",
    }
    assert critical & dropped == set()


def test_audio_and_network_dependencies_are_never_dropped() -> None:
    """BGM 是 OGG，Qt Multimedia 在 Windows 上走 FFmpeg 后端；HTTPS 走 OpenSSL。

    这两组都是「删了不报错、只在用到时崩」的典型，单独守一道。
    """
    dropped = drop_list()
    for name in ("avcodec-63.dll", "avformat-63.dll", "avutil-61.dll", "swscale-10.dll",
                 "Qt6Multimedia.dll", "Qt6Network.dll", "Qt6WebSockets.dll",
                 "libcrypto-3-x64.dll", "libssl-3-x64.dll"):
        assert name not in dropped, f"{name} 被误删，运行期会崩"


def test_opengl_software_fallback_is_dropped() -> None:
    """opengl32sw.dll 19.7 MB，是软件 OpenGL 回退。本程序是 QWidget 光栅绘制。

    这条同时记录了「为什么敢删」：它不是在用 OpenGL，只是 Qt 打包时顺手带的。
    """
    assert "opengl32sw.dll" in drop_list()


def test_spec_passes_exe_name_from_environment() -> None:
    """产物名由构建脚本经环境变量传入 —— 避免 PS 与 spec 各写一份版本号。"""
    source = SPEC.read_text(encoding="utf-8")
    assert "XIONGHAN_EXE_NAME" in source


def test_qt_translations_keep_chinese() -> None:
    """Qt 自带对话框的按钮文字来自翻译文件，只留中文与英文。"""
    source = SPEC.read_text(encoding="utf-8")
    assert "_zh_CN.qm" in source
    assert "_en.qm" in source
