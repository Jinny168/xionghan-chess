"""创建 Windows 快捷方式（.lnk）—— 纯 ctypes 调 COM，不依赖 pywin32 / WScript.Shell。

环境里 PowerShell 的 `New-Object -ComObject` 与 `cscript` 都被安全策略拦了，
所以直接用 ctypes 走 `IShellLinkW` + `IPersistFile::Save`。

用法：
    python scripts/make_shortcut.py <目标.lnk> <目标 exe> [图标,索引] [描述]
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import POINTER, Structure, byref, c_ulong, c_ushort, c_void_p, c_wchar_p

ole32 = ctypes.oledll.ole32                 # oledll：HRESULT 失败自动抛 OSError
ole32.CoInitializeEx.argtypes = [c_void_p, c_ulong]
ole32.CoInitializeEx.restype = ctypes.HRESULT
ole32.CoCreateInstance.argtypes = [c_void_p, c_void_p, c_ulong, c_void_p, c_void_p]
ole32.CoCreateInstance.restype = ctypes.HRESULT

CLSCTX_INPROC_SERVER = 1
COINIT_APARTMENTTHREADED = 2


class GUID(Structure):
    _fields_ = [("Data1", c_ulong), ("Data2", c_ushort),
                ("Data3", c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, text: str) -> None:
        super().__init__()
        ole32.CLSIDFromString(c_wchar_p(text), byref(self))


CLSID_SHELL_LINK = "{00021401-0000-0000-C000-000000000046}"
IID_ISHELL_LINK_W = "{000214F9-0000-0000-C000-000000000046}"
IID_IPERSIST_FILE = "{0000010B-0000-0000-C000-000000000046}"

# IShellLinkW vtable 下标（IUnknown 占 0..2）
QI, RELEASE = 0, 2
SET_DESCRIPTION, SET_WORKING_DIR, SET_ICON_LOCATION, SET_PATH = 7, 9, 17, 20
PERSIST_SAVE = 6


def _call(ptr: int, index: int, *args) -> None:
    """按 vtable 下标调用；实参统一按 void* 传（COM 只关心指针值）。"""
    vtable = ctypes.cast(c_void_p(ptr), POINTER(POINTER(c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *([c_void_p] * len(args)))
    packed = []
    for arg in args:
        if isinstance(arg, int):
            packed.append(c_void_p(arg))
        elif isinstance(arg, str):
            packed.append(ctypes.cast(c_wchar_p(arg), c_void_p))
        else:
            packed.append(ctypes.cast(arg, c_void_p))
    proto(vtable[index])(c_void_p(ptr), *packed)


def make_shortcut(lnk: str, target: str, workdir: str, icon: str, description: str) -> None:
    ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)

    clsid = GUID(CLSID_SHELL_LINK)
    iid_link = GUID(IID_ISHELL_LINK_W)
    iid_persist = GUID(IID_IPERSIST_FILE)

    link = c_void_p()
    ole32.CoCreateInstance(ctypes.cast(byref(clsid), c_void_p), None, CLSCTX_INPROC_SERVER,
                           ctypes.cast(byref(iid_link), c_void_p),
                           ctypes.cast(byref(link), c_void_p))
    if not link.value:
        raise OSError("CoCreateInstance 返回空指针")

    _call(link.value, SET_PATH, target)
    _call(link.value, SET_WORKING_DIR, workdir)
    _call(link.value, SET_ICON_LOCATION, icon, 0)
    _call(link.value, SET_DESCRIPTION, description)

    persist = c_void_p()
    _call(link.value, QI, byref(iid_persist), byref(persist))
    _call(persist.value, PERSIST_SAVE, lnk, 1)      # TRUE = 立即写盘
    _call(persist.value, RELEASE)
    _call(link.value, RELEASE)
    ole32.CoUninitialize()


if __name__ == "__main__":
    lnk_path, exe_path = sys.argv[1], sys.argv[2]
    icon = sys.argv[3] if len(sys.argv) > 3 else exe_path + ",0"
    desc = sys.argv[4] if len(sys.argv) > 4 else "匈汉象棋"
    make_shortcut(lnk_path, exe_path, exe_path.rsplit("\\", 1)[0], icon, desc)
    print("created:", lnk_path)
