$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { py -3.11 -m venv (Join-Path $ProjectRoot ".venv") }
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# FIX (阶段0 S0-A): 原为 `-e "$ProjectRoot[desktop,build]"`。PowerShell 会把
# `[desktop,build]` 当作**字面量**拼进字符串（它既不是变量展开也不是合法路径分隔），
# 得到 `…\xionghan-chess-next[desktop,build]`；随后 `New-Item -Force` 会因父目录存在
# 而静默成功，导致下面 PyInstaller 那一行**从未真正执行过** —— 构建链静默断裂。
# 与脚本其余路径一致，改用 Join-Path。
& $Python -m pip install -e (Join-Path $ProjectRoot "[desktop,build]")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$release = Join-Path $ProjectRoot "release"
$work = Join-Path $ProjectRoot "build-onefile"
$icon = Join-Path $ProjectRoot "src\xionghan_chess\desktop\resources\icon.ico"

# 阶段1 S1-7：构建期资源断言。
# `--add-data`（本脚本）与 pyproject 的 `[tool.setuptools.package-data]` 是**两处手工同步**，
# 漏一个不会报错，只会让成品静默缺资源（图标全缺却没明显报错是已知打包事故）。
# 这里显式校验三份数据源 + 图标存在且非空，把"静默丢失"变成"构建即失败"。
$dataRoots = @(
    (Join-Path $ProjectRoot 'src\xionghan_chess\desktop\resources'),
    (Join-Path $ProjectRoot 'src\xionghan_chess\core\data'),
    (Join-Path $ProjectRoot 'locales'),
    # 棋子美术（66 张 160×160 PNG）。它是 Git LFS 跟踪的，见下面的专项断言。
    (Join-Path $ProjectRoot 'web\assets\pieces')
)
foreach ($root in $dataRoots) {
    if (-not (Test-Path $root)) { Write-Error "资源目录缺失：$root"; exit 1 }
    $items = @(Get-ChildItem -Path $root -Recurse -File)
    if ($items.Count -eq 0) { Write-Error "资源目录为空：$root"; exit 1 }
    $sum = ($items | Measure-Object -Property Length -Sum).Sum
    Write-Host ("  资源校验 OK：{0}  ({1} 个文件, {2:N1} MB)" -f $root, $items.Count, ($sum/1MB))
}
if (-not (Test-Path $icon)) { Write-Error "图标缺失：$icon"; exit 1 }
$iconInfo = Get-Item $icon
Write-Host ("  图标校验 OK：{0}  ({1:N0} B)" -f $icon, $iconInfo.Length)

# 阶段2 S2-4：字体授权断言。
# 1.6.0 曾把系统字体 msyh.ttc / simkai.ttf 拷进仓库随包分发 —— 那是微软授权字体，
# 随安装包再分发需要单独授权。现改用 SIL OFL 1.1 的 Noto 子集。
# OFL 条件 2 要求副本分发时随附许可证，所以 OFL.txt 必须在包里；缺它同样属于合规问题，
# 且和资源缺失一样"不报错、装完才发现"，因此在这里拦成构建失败。
$fontDir = Join-Path $ProjectRoot 'src\xionghan_chess\desktop\resources\fonts'
foreach ($legacy in @('msyh.ttc', 'simkai.ttf')) {
    if (Test-Path (Join-Path $fontDir $legacy)) {
        Write-Error "授权风险：随包资源仍含微软授权字体 $legacy（见 S2-4）"; exit 1
    }
}
if (-not (Test-Path (Join-Path $fontDir 'OFL.txt'))) {
    Write-Error "合规缺失：字体目录缺 OFL.txt（SIL OFL 1.1 条件 2 要求随附许可证）"; exit 1
}
foreach ($fontFile in @('NotoSansSC-subset.ttf', 'NotoSerifSC-subset.ttf')) {
    $fontPath = Join-Path $fontDir $fontFile
    if (-not (Test-Path $fontPath)) { Write-Error "随包字体缺失：$fontPath"; exit 1 }
    if ((Get-Item $fontPath).Length -lt 1MB) { Write-Error "随包字体疑似损坏（过小）：$fontPath"; exit 1 }
}
$fontSum = (Get-ChildItem -Path $fontDir -File | Measure-Object -Property Length -Sum).Sum
Write-Host ("  字体校验 OK：OFL 开源字体，{0:N1} MB（S2-4，原微软字体 31.5 MB 已移除）" -f ($fontSum/1MB))

# ---- 棋子美术断言（三风格 PNG）----
# 为什么必须逐张验魔数：`web/assets/pieces/**/*.png` 是 **Git LFS** 跟踪的。
# 新克隆若没跑 `git lfs pull`，拿到的是约 130 B 的 `version https://git-lfs...` 指针
# 文本 —— PyInstaller 会照样把它们塞进 EXE，运行期只是「缺图 → 回退字形」，
# **不报任何错**。所以这里把「静默缺图」拦成「构建失败」。
$pieceDir = Join-Path $ProjectRoot 'web\assets\pieces'
$styles = @('traditional', 'modern', 'cartoon')
$pieceFiles = @(Get-ChildItem -Path $pieceDir -Recurse -File -Filter *.png)
if (-not ($pieceFiles.Count -in @(66, 84))) {
    Write-Error ("棋子图数量异常：{0}（期望 66 = 11 型 × 3 风格 × 2 色，或 84 = 14 × 3 × 2）。可能是 Git LFS 未拉取：先 `git lfs pull`。" -f $pieceFiles.Count)
    exit 1
}
$pieceSum = ($pieceFiles | Measure-Object -Property Length -Sum).Sum
if ($pieceSum -lt 300KB -or $pieceSum -gt 512KB) {
    Write-Error ("棋子图总体积异常：{0:N0} B（期望 300 KB ~ 512 KB）。66 个 LFS 指针只有约 8.6 KB —— 大概率是 Git LFS 未拉取：先 `git lfs pull`。" -f $pieceSum)
    exit 1
}
$bad = @()
foreach ($file in $pieceFiles) {
    if ($file.Length -gt 24KB) {
        $bad += ("{0}: 单张 {1:N0} B 超过 24 KB 硬门禁" -f $file.Name, $file.Length)
        continue
    }
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Length -lt 24 -or $bytes[0] -ne 0x89 -or $bytes[1] -ne 0x50 -or $bytes[2] -ne 0x4E -or $bytes[3] -ne 0x47) {
        $bad += ("{0}: 不是 PNG（缺少 89 50 4E 47 魔数）" -f $file.Name)
        continue
    }
    # PNG IHDR：宽高是第 16..23 字节的大端 32 位整数。
    $width = ([int]$bytes[16] -shl 24) -bor ([int]$bytes[17] -shl 16) -bor ([int]$bytes[18] -shl 8) -bor [int]$bytes[19]
    $height = ([int]$bytes[20] -shl 24) -bor ([int]$bytes[21] -shl 16) -bor ([int]$bytes[22] -shl 8) -bor [int]$bytes[23]
    if ($width -ne 160 -or $height -ne 160) {
        $bad += ("{0}: {1}×{2}（期望 160×160）" -f $file.Name, $width, $height)
    }
}
# 三风格必须齐全：任一风格缺某个已存在的后缀，就是"某几个子在其他风格下变大变小"。
$stems = @{}
foreach ($style in $styles) {
    $dir = Join-Path $pieceDir $style
    if (-not (Test-Path $dir)) { $bad += ("缺少风格目录：{0}" -f $style); continue }
    $names = @(Get-ChildItem -Path $dir -File -Filter *.png | ForEach-Object { $_.Name })
    if ($names.Count -eq 0) { $bad += ("风格目录为空：{0}" -f $style); continue }
    $stems[$style] = $names
}
if ($stems.Count -gt 0) {
    foreach ($style in $stems.Keys) {
        foreach ($other in $stems.Keys) {
            if ($style -eq $other) { continue }
            $missing = @($stems[$style] | Where-Object { $stems[$other] -notcontains $_ })
            if ($missing.Count -gt 0) {
                $bad += ("风格 {0} 缺少 {1} 张：{2}" -f $other, $missing.Count, ($missing -join ', '))
            }
        }
    }
}
if ($bad.Count -gt 0) {
    Write-Error ("棋子图校验失败（{0} 项）：`n  {1}`n若全部报「不是 PNG / 尺寸不对」，几乎一定是 Git LFS 未拉取：先 `git lfs pull`。" -f $bad.Count, ($bad -join "`n  "))
    exit 1
}
Write-Host ("  棋子图校验 OK：{0} 张，{1:N1} KB，均 160×160 且三风格齐全" -f $pieceFiles.Count, ($pieceSum/1KB))

# 阶段2 S2-6：Qt 体积裁剪 —— 已改为在 `build_windows.spec` 里做，**不要**再用
# `--exclude-module`。
#
# 实测记录（避免以后有人重走这条死路）：
#   加 46 个 `--exclude-module PySide6.QtXxx` -> 73,458,712 B
#   一个都不加                              -> 73,542,180 B
#   差 83 KB，属压缩噪声；且两次构建的 Analysis TOC 里 Qt6Qml.dll / Qt6Quick.dll /
#   Qt6Pdf.dll / opengl32sw.dll 一个都没少。原因：`--exclude-module` 只影响 import
#   图，而 PySide6 的 hook 是按 site-packages 里的文件**直接收**二进制的。
#
# 有效做法是在 Analysis 之后过滤 `a.binaries` / `a.datas`（只能在 spec 里做）：
#   过滤后 55,225,671 B，同一份代码同一台机器，**省 18.3 MB（-24.9%）**，
#   裁掉 7 个未使用 Qt 二进制 + Qt 翻译 144 -> 10 个。
# 打包产物已用 scripts/probe_exe.py 探活（临时 APPDATA，验证数据目录被创建 + 进程存活）。
$productName = -join [char[]](0x5308, 0x6F22, 0x8C61, 0x68CB)
$platformName = -join [char[]](0x684C, 0x9762, 0x7248)
$artifactName = "$productName-1.7.0-$platformName"
# FIX (阶段0 S0-A 续)：构建链第三个缺陷。
# PyInstaller 把 INFO 级日志写到 **stderr**；在 `$ErrorActionPreference = "Stop"`
# 下，PowerShell 会把任何原生命令的 stderr 输出包装成 NativeCommandError 并**中止脚本**
# —— 即使构建其实成功了。表现为脚本报「NativeCommandError」但 release/ 里已有产物。
# 处置：原生命令段临时切到 Continue，真正的是否失败只看 $LASTEXITCODE（下面已逐行检查）。
$ErrorActionPreference = "Continue"
$env:XIONGHAN_EXE_NAME = $artifactName
& $Python -m PyInstaller --noconfirm --clean --distpath $release --workpath $work (Join-Path $PSScriptRoot "build_windows.spec")
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = "Stop"; exit $LASTEXITCODE }
$ErrorActionPreference = "Stop"
Copy-Item -LiteralPath (Join-Path $release "$artifactName.exe") -Destination (Join-Path $release "$productName-$platformName.exe") -Force
Write-Host "Build completed: $release\$artifactName.exe"
