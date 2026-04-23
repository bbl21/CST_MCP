param(
    [string]$ProjectName,
    [switch]$Force
)

$CstForceKillAllowlist = @(
    'cstd',
    'CST DESIGN ENVIRONMENT_AMD64',
    'CSTDCMainController_AMD64',
    'CSTDCSolverServer_AMD64'
)

function Stop-AllowlistedCstProcesses {
    param([string[]]$Names)
    foreach ($name in $Names) {
        Stop-Process -Name $name -Force -ErrorAction SilentlyContinue
    }
}

if ($Force -or -not $ProjectName) {
    Stop-AllowlistedCstProcesses -Names $CstForceKillAllowlist
    Write-Output "closed all"
} else {
    Get-Process 'CST DESIGN ENVIRONMENT_AMD64' -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -like "*$ProjectName*" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    $remainingDesign = @(Get-Process 'CST DESIGN ENVIRONMENT_AMD64' -ErrorAction SilentlyContinue)
    if ($remainingDesign.Count -eq 0) {
        Stop-AllowlistedCstProcesses -Names @(
            'cstd',
            'CSTDCMainController_AMD64',
            'CSTDCSolverServer_AMD64'
        )
    }
    Write-Output "closed: $ProjectName"
}
