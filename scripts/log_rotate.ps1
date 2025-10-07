$log = "C:\Users\unive\Desktop\v_infinity\adaptive_dca_ai\logs\manual_run_all.log"
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 104857600)) {
    $stamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
    Move-Item $log "$log.$stamp"
    New-Item $log -ItemType File | Out-Null
}
