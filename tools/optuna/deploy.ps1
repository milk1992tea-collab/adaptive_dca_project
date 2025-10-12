# deploy.ps1 - one-shot deploy for local/real env
param(
  [int]$Port = 18081,
  [int]$Keep = 5
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# rotate logs: keep $Keep latest archives
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$archive = Join-Path $logs "archive_$timestamp"
New-Item -ItemType Directory -Path $archive | Out-Null
Get-ChildItem -Path $logs -File -ErrorAction SilentlyContinue | ForEach-Object {
  Move-Item -Path $_.FullName -Destination $archive -Force
}

# cleanup older archives
Get-ChildItem -Path $logs -Directory -Filter 'archive_*' | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# start uvicorn in background with redirected stdout/err
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { Write-Error "Python executable not found: $py"; exit 1 }

$stdout = Join-Path $logs 'uvicorn.out.log'
$stderr = Join-Path $logs 'uvicorn.err.log'

# stop any uvicorn in this venv if present (safe filter)
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $py } | ForEach-Object {
  try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } catch {}
}

$argList = "-X","utf8","-u","-m","uvicorn","app:app","--host","127.0.0.1","--port",$Port,"--log-level","info"
$proc = Start-Process -FilePath $py -ArgumentList $argList -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Start-Sleep -Seconds 1

# verify
$listen = netstat -ano | Select-String (":$Port") -SimpleMatch
if ($listen) {
  Write-Output "Started uvicorn PID: $($proc.Id) on port $Port"
} else {
  Write-Output "uvicorn did not start; check logs"
}

# health check
try {
  $h = curl.exe -4 -sS "http://127.0.0.1:$Port/health"
  Write-Output "health: $h"
} catch {
  Write-Output "health check failed"
}
