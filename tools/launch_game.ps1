# Y3 游戏启动脚本（自动读取配置）
# 使用方法：通过计划任务 Y3LaunchGame 调用
# 配置自动从 .vscode/settings.json 和 header.project 读取

$ErrorActionPreference = "Stop"

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsDir = $scriptDir

# 向上查找 script 目录（tools 的父目录）
$scriptPath = Split-Path -Parent $toolsDir

# 验证 script 目录
if (-not (Test-Path (Join-Path $scriptPath "main.lua"))) {
    Write-Host "[ERROR] Cannot find script directory (no main.lua found)"
    exit 1
}

# 读取 .vscode/settings.json 获取编辑器路径
$vscodeSettings = Join-Path $scriptPath ".vscode\settings.json"
if (-not (Test-Path $vscodeSettings)) {
    Write-Host "[ERROR] Cannot find .vscode/settings.json"
    Write-Host "[TIP] Open project in VSCode/Cursor first, Y3 Helper will create this file"
    exit 1
}

$settings = Get-Content $vscodeSettings -Raw | ConvertFrom-Json
$editorPath = $settings.'Y3-Helper.EditorPath'
if (-not $editorPath) {
    Write-Host "[ERROR] Y3-Helper.EditorPath not found in settings.json"
    exit 1
}

# 从编辑器路径推算游戏可执行文件
$gameDir = Split-Path -Parent $editorPath
$gameExe = Join-Path $gameDir "Engine\Binaries\Win64\Game_x64h.exe"
if (-not (Test-Path $gameExe)) {
    Write-Host "[ERROR] Cannot find Game_x64h.exe at: $gameExe"
    exit 1
}

# 从 script 路径推算项目路径
# script 路径格式: <project>/maps/<map_name>/script
$pathParts = $scriptPath -split '\\'
$mapsIndex = [array]::IndexOf($pathParts, "maps")
if ($mapsIndex -lt 0) {
    Write-Host "[ERROR] Cannot find 'maps' in path to determine project root"
    exit 1
}
$projectPath = ($pathParts[0..($mapsIndex-1)]) -join '\'

# 读取 header.project 获取 level_id
$headerFile = Join-Path $projectPath "header.project"
if (-not (Test-Path $headerFile)) {
    Write-Host "[ERROR] Cannot find header.project at: $headerFile"
    exit 1
}

$headerData = Get-Content $headerFile -Raw | ConvertFrom-Json
$levelId = $headerData.entry_map.id
if (-not $levelId) {
    Write-Host "[ERROR] Cannot read entry_map.id from header.project"
    exit 1
}

# 输出配置信息
Write-Host "===== Y3 Game Launcher ====="
Write-Host "[OK] Script Path: $scriptPath"
Write-Host "[OK] Project Path: $projectPath"
Write-Host "[OK] Level ID: $levelId"
Write-Host "[OK] Game EXE: $gameExe"

# 构建启动参数（注意路径中的反斜杠需要转义）
$escapedProjectPath = $projectPath -replace '\\', '\\\\'
$pythonArgs = "type@editor_game,subtype@editor_game,editor_map_path@$escapedProjectPath,level_id@$levelId,release@true,lua_dummy@space,lua_wait_debugger@true"

# 切换到游戏目录并启动
$gameWorkDir = Split-Path -Parent $gameExe
Set-Location $gameWorkDir

Write-Host "[OK] Starting game..."
Start-Process -FilePath $gameExe -ArgumentList @(
    "--dx11",
    "--start=Python",
    "--python-args=$pythonArgs",
    "--plugin-config=Plugins-PyQt",
    "--console",
    "--luaconsole"
)

Write-Host "[OK] Game launch command sent"
