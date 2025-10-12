param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("foreground","background")]
    [string]$Mode = "foreground"
)

# Resolve script root: fallback to current directory if $PSScriptRoot is null/empty
$scriptRoot = $PSScriptRoot
if ([string]::IsNullOrEmpty($scriptRoot)) {
    $scriptRoot = (Get-Location).Path
}

# 設定 venv python 路徑
$venvPy = Join-Path $scriptRoot '.venv\Scripts\python.exe'
if (-Not (Test-Path $venvPy)) {
    Write-Host "虛擬環境 python 未找到： $venvPy" -ForegroundColor Yellow
    exit 1
}

$uvArgs = '-m uvicorn app:app --host 127.0.0.1 --port 18081 --log-level info --no-access-log --http h11'

if ($Mode -eq 'foreground') {
    & $venvPy $uvArgs
} else {
    $logDir = Join-Path $scriptRoot 'logs'
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    $ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
    $out = Join-Path $logDir ("uvicorn.out." + $ts + ".log")
    $err = Join-Path $logDir ("uvicorn.err." + $ts + ".log")
    $proc = Start-Process -FilePath $venvPy -ArgumentList $uvArgs -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    "$($proc.Id) `t $ts" | Out-File -FilePath (Join-Path $scriptRoot 'uvicorn.pid') -Encoding utf8
    Write-Host "Started PID $($proc.Id). Logs: $out , $err"
}
