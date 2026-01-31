# 只杀有conhost子进程的Game_x64h（游戏进程），不杀编辑器
$gameProcs = Get-Process -Name "Game_x64h" -ErrorAction SilentlyContinue
$killed = $false

foreach ($proc in $gameProcs) {
    # 检查是否有conhost子进程
    $children = Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq $proc.Id -and $_.Name -eq "conhost.exe" }
    if ($children) {
        Write-Host "Found game process with console: PID $($proc.Id)"
        # 用taskkill强制杀，比Stop-Process更可靠
        $result = & taskkill /F /PID $proc.Id 2>&1
        Write-Host $result
        $killed = $true
    }
}

if (-not $killed) {
    Write-Host "No game process with console found"
}
