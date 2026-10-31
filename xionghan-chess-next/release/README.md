# release/ 产物与复现方式

本目录的交付物**不入库**（`.gitignore` 里有 `*.exe`），只保留构建/放置方式，保证任何人能重做一遍。

## 桌面版（Windows 单文件 EXE）

```bash
# 在仓库根目录，用现有 spec（packaging/build_windows.spec），不要自创参数
XIONGHAN_EXE_NAME="匈漢象棋-1.7.1-桌面版" \
  .venv/Scripts/pyinstaller.exe packaging/build_windows.spec \
  --noconfirm --distpath release --workpath build/1.7.1
```

- 产物：`release/匈漢象棋-<版本>-桌面版.exe`（onefile，约 55 MB）
- 命名：沿用 `匈漢象棋-<版本>-桌面版.exe`；**不覆盖**旧版本，旧包留作对照
- 冒活：`python scripts/probe_exe.py "release/<exe>"`（判据是「数据目录被创建 + 进程未即崩」，
  不是「打包成功」）

### 版本记录

| 版本 | 内容 | 代码来源 |
|---|---|---|
| **1.7.4** | **尉与仕对调开局位（红 (12,6)↔(11,5)，黑镜像）—— 尉首着 0→4，其余子着数不变** | `756a938` |
| **1.7.3** | **50 子布局（每方 25、11 型，甲/楯/刺 移除）+ 尉改标准主教 + 图谱三栏合并（演示盘/可写开关）+ 兵两开关暴露** | `3b30104` |
| **1.7.2** | **54 子布局（每方 27、12 型，甲/楯 移除）+ 射吃子可越子 + 兵「冲锋/三连」两开关（默认关）** | `243596b` |
| 1.7.1 | 62 子布局（14 型）+ 射穿子前的规则 | `bd66678` |

## 桌面快捷方式

```bash
python scripts/make_shortcut.py "<桌面的 .lnk 绝对路径>" "<EXE 绝对路径>"
```

- 走 `IShellLinkW` + `IPersistFile::Save`（ctypes），因为本机安全策略拦掉了
  PowerShell 的 `New-Object -ComObject` 与 `cscript`；
- 注意 **桌面可能被 OneDrive 重定向**：真实路径取注册表
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders` 的 `Desktop`
  （本机为 `D:\Data\OneDrive\Desktop`，而 `C:\Users\<user>\Desktop` 并不存在）。

## 网页版一键启动

`启动网页版.bat`（仓库根目录）：设 `PYTHONPATH=src`，起
`uvicorn xionghan_chess.service.app:app --host 127.0.0.1 --port 8765`，
延迟 2 秒后打开默认浏览器；关闭弹出的“服务”窗口即停止。

放在仓库根而不是 `release/`：它依赖相对路径的 `.venv\` 与 `src\`，跟着源码走才不会失效。
