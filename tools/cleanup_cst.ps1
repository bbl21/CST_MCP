Get-Process | Where-Object {$_.ProcessName -like 'cst*'} | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Output "done"