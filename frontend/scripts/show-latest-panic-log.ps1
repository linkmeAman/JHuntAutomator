$pattern = "next-panic-*.log"
$logs = Get-ChildItem $env:TEMP -Filter $pattern -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if (-not $logs) {
  Write-Host "No panic logs found in $env:TEMP matching $pattern"
  exit 0
}
$latest = $logs[0]
Write-Host "Latest panic log:" $latest.FullName
Write-Host "----"
Get-Content $latest.FullName
