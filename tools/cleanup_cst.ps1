$CstForceKillAllowlist = @(
    'cstd',
    'CST DESIGN ENVIRONMENT_AMD64',
    'CSTDCMainController_AMD64',
    'CSTDCSolverServer_AMD64'
)

foreach ($name in $CstForceKillAllowlist) {
    Stop-Process -Name $name -Force -ErrorAction SilentlyContinue
}
Write-Output "done"
