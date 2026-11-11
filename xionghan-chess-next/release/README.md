# release/ 产物与复现方式

本目录的交付物**不入库**（`.gitignore` 里有 `*.exe`），只保留构建/放置方式，保证任何人能重做一遍。

## 桌面版（Windows 单文件 EXE）

```bash
# 在仓库根目录，用现有 spec（packaging/build_windows.spec），不要自创参数
XIONGHAN_EXE_NAME="匈漢象棋-2.0.3-桌面版" \
  .venv/Scripts/pyinstaller.exe packaging/build_windows.spec \
  --noconfirm --distpath release --workpath build/2.0.3
```

- 产物：`release/匈漢象棋-<版本>-桌面版.exe`（onefile，**2.0.3 实测 63,307,185 B ≈ 60.4 MiB**）
- 命名：`匈漢象棋-<版本>-桌面版.exe`；**旧版移进 `release/_old/`**，不在顶层堆叠
- ⚠️ **覆盖已存在的 exe 会撞 safe-delete**（PyInstaller 走 `os.remove` 被拦，构建在最后一步失败）：
  `build_windows.ps1:159-166` 已加「先删同名旧产物」前置逻辑，用脚本构建即可绕过
- ⚠️ **exe / zip 不可字节复现**：同一份源码两次 `--clean` 构建字节数会差 ~2 KB、SHA 也不同。
  记录时必须以「某次构建」为限定，不能当作「由源码可复现」
- 冒活：`python scripts/probe_exe.py "release/<exe>"`（判据是「数据目录被创建 + 进程未即崩」，
  不是「打包成功」）

### 版本记录

| 版本 | 内容 | 代码来源 |
|---|---|---|
| **2.0.3** | **版本线对齐（纠正 2.0.1/2.0.2 造成的版本号倒挂）+ 11/11 五项修复：桌面终局结算弹窗（`to_dict` 补 `finished`）、非法难度报错只说三档、旧档名存储归一、桌面崩溃日志落盘（`crashlog.py`）、Windows asyncio 改 Selector 事件循环** | `06ee382` |
| 2.0.2 | ⚠️ **无 git 版本提交**（手改 `version_info.txt` 打包，代码基线同 2.0.0；`D:\匈汉象棋\` 有产物但仓库历史查不到） | — |
| 2.0.1 | ⚠️ **无 git 版本提交**（同上） | — |
| **2.0.0** | **巡禁竖移 + 兵底线不再后退 + 设置四项 + 规则版本位（`RULE_VERSION=2`）** | `cb26bdc` |
| **1.8.2** | **棋子图谱两栏竖排 + 演示随棋子裁剪 + 开关统一「勾选=增强」+ 关于页版本不再写死** | `c59d4fa` |
| **1.8.1** | **开局布局归位（尉在将正后、士对称两枚）+ 马两条自定义规则（别马腿/直走三格仅移动）+ 三模式正交定义（完整/经典/精简）+ 修复兵冲锋吞吃子** | `eb060e6` |
| **1.8.0** | **座位 token 移出 query（改请求头 + WS 首帧，破坏性变更）+ 审计 P0/P1 修复（端点 500、僵尸房、广播去 replay、坐标越界、WS 64 KB、名字 24 码点、聊天 200 条、AI 看门狗）+ 网页令牌化与桌面危险色校正** | `53aa536` |
| **1.7.5** | **新增「网页合成」音效包（复刻投稿版 WebAudio 合成，8 事件）+ 设置里「音效风格」切换** | `ae68a01` |
| **1.7.4** | **尉与仕对调开局位（红 (12,6)↔(11,5)，黑镜像）—— 尉首着 0→4，其余子着数不变** | `756a938` |
| **1.7.3** | **50 子布局（每方 25、11 型，甲/楯/刺 移除）+ 尉改标准主教 + 图谱三栏合并（演示盘/可写开关）+ 兵两开关暴露** | `3b30104` |
| **1.7.2** | **54 子布局（每方 27、12 型，甲/楯 移除）+ 射吃子可越子 + 兵「冲锋/三连」两开关（默认关）** | `243596b` |
| 1.7.1 | 62 子布局（14 型）+ 射穿子前的规则 | `bd66678` |

> **2.0.3 桌面版经用户实机验证：终局出现结算弹窗**（D-1 修复的直接体感证据）。

### 当前交付（2026-11-11）

| 产物 | 字节数 | 指纹 | 备注 |
|---|---|---|---|
| `匈漢象棋-2.0.3-桌面版.exe` | **63,307,185 B** | `FileVersion 2.0.3.0`；SHA256 `E3312EF2…C789EB` | onefile |
| `匈漢象棋-2.0.3-网页版.zip` | **31,102,211 B** | 213 条目；SHA256 `95163691…3EAF9C` | 含 `requirements/lock/py312-server.txt` |
| `release/_old/` | — | — | 2.0.0 两个（历史对照） |

桌面快捷方式指向 `D:\匈汉象棋\匈漢象棋.exe`（2.0.3），由 `scripts/make_shortcut.py` 生成/重建。

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
