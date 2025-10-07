$proj = "C:\Users\unive\Desktop\v_infinity\adaptive_dca_ai"
$python = "C:\Users\unive\AppData\Local\Programs\Python\Python313\python.exe"
$p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "run_live.py" }
if (-not $p) {
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$proj`" && `"$python`" -u run_live.py *> `"$proj\logs\manual_run_all.log`"" -WindowStyle Hidden
}
