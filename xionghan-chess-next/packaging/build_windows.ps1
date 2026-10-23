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
    (Join-Path $ProjectRoot 'locales')
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
$productName = -join [char[]](0x5308, 0x6F22, 0x8C61, 0x68CB)
$platformName = -join [char[]](0x684C, 0x9762, 0x7248)
$artifactName = "$productName-1.7.0-$platformName"
# FIX (阶段0 S0-A 续)：构建链第三个缺陷。
# PyInstaller 把 INFO 级日志写到 **stderr**；在 `$ErrorActionPreference = "Stop"`
# 下，PowerShell 会把任何原生命令的 stderr 输出包装成 NativeCommandError 并**中止脚本**
# —— 即使构建其实成功了。表现为脚本报「NativeCommandError」但 release/ 里已有产物。
# 处置：原生命令段临时切到 Continue，真正的是否失败只看 $LASTEXITCODE（下面已逐行检查）。
$ErrorActionPreference = "Continue"
& $Python -m PyInstaller --noconfirm --clean --onefile --name $artifactName --windowed --icon $icon --add-data "$(Join-Path $ProjectRoot 'src\xionghan_chess\desktop\resources');xionghan_chess\desktop\resources" --add-data "$(Join-Path $ProjectRoot 'src\xionghan_chess\core\data');xionghan_chess\core\data" --add-data "$(Join-Path $ProjectRoot 'locales');locales" --paths (Join-Path $ProjectRoot "src") --distpath $release --workpath $work --specpath $work (Join-Path $PSScriptRoot "desktop_entry.py")
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = "Stop"; exit $LASTEXITCODE }
$ErrorActionPreference = "Stop"
Copy-Item -LiteralPath (Join-Path $release "$artifactName.exe") -Destination (Join-Path $release "$productName-$platformName.exe") -Force
Write-Host "Build completed: $release\$artifactName.exe"
