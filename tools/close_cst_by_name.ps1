param(
    [string]$ProjectName,
    [switch]$Force
)

if ($Force -or -not $ProjectName) {
    Stop-Process -Name 'CST DESIGN ENVIRONMENT_AMD64' -Force -ErrorAction SilentlyContinue
    Stop-Process -Name cstd -Force -ErrorAction SilentlyContinue
    Write-Output "closed all"
} else {
    Get-Process 'CST DESIGN ENVIRONMENT_AMD64' -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -like "*$ProjectName*" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Output "closed: $ProjectName"
}
