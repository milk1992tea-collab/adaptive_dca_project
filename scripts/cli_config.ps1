# scripts/cli_config.ps1
# Simple, robust interactive credential writer

Function Prompt-Secure {
    Param([string]$Message)
    Write-Host $Message -NoNewline
    $sec = Read-Host -AsSecureString
    if ($null -eq $sec) { return "" }
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$cfgPath = Join-Path $scriptRoot '..\config\credentials.json'
$cfgPath = [System.IO.Path]::GetFullPath($cfgPath)

Write-Host ""
Write-Host "Providers to configure (comma separated, default: coingecko):" -ForegroundColor Cyan
$providers = Read-Host "Providers"
if (-not $providers) { $providers = "coingecko" }
$providers = $providers.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }

$payload = @{}
foreach ($p in $providers) {
    Write-Host ""
    Write-Host "Configuring provider: $p" -ForegroundColor Yellow
    $entry = @{}
    switch ($p.ToLower()) {
        "coingecko" {
            $vs = Read-Host "Optional vs_currency (default usd)"
            if ($vs) { $entry["vs_currency"] = $vs }
        }
        "binance" {
            $entry["api_key"] = Prompt-Secure "Enter BINANCE API KEY: "
            $entry["api_secret"] = Prompt-Secure "Enter BINANCE SECRET: "
            $ue = Read-Host "Store in file or env? (file/env) [file]"
            if (-not $ue) { $ue = "file" }
            $entry["use_env"] = $ue
        }
        "ccxt" {
            $entry["exchange_id"] = Read-Host "Exchange id for ccxt (default binance)"
            if (-not $entry["exchange_id"]) { $entry["exchange_id"] = "binance" }
            $entry["api_key"] = Prompt-Secure "Enter API KEY (optional): "
            $entry["api_secret"] = Prompt-Secure "Enter API SECRET (optional): "
            $ue = Read-Host "Store in file or env? (file/env) [env]"
            if (-not $ue) { $ue = "env" }
            $entry["use_env"] = $ue
        }
        Default {
            while ($true) {
                $k = Read-Host "Enter key (leave empty to finish)"
                if (-not $k) { break }
                $v = Read-Host "Enter value for $k"
                $entry[$k] = $v
            }
        }
    }
    $payload[$p] = $entry
}

# ensure .gitignore
$gitignore = Join-Path $scriptRoot '..\.gitignore'
if (-not (Test-Path $gitignore)) { "" | Out-File $gitignore -Encoding utf8 }
$gi = Get-Content $gitignore -ErrorAction SilentlyContinue
if ($gi -notcontains "config/credentials.json") {
    Add-Content -Path $gitignore -Value "`n# local credentials`nconfig/credentials.json"
}

$json = $payload | ConvertTo-Json -Depth 5
$json | Out-File -FilePath $cfgPath -Encoding utf8

# attempt to restrict ACL
try {
    $acl = Get-Acl $cfgPath
    $acl.SetAccessRuleProtection($true, $false)
    $me = [System.Security.Principal.NTAccount]::new((whoami))
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($me, "FullControl", "Allow")
    $acl.SetAccessRule($rule)
    Set-Acl -Path $cfgPath -AclObject $acl
    Write-Host "Wrote credentials to $cfgPath and restricted file permissions to current user." -ForegroundColor Green
} catch { Write-Host "Could not set ACL: $_" -ForegroundColor Yellow }

Write-Host "Done."
