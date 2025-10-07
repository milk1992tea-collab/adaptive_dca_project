<#
run_long_test.ps1
?券???Windows 銝???long-running dry-run 銝衣?扳隤???啣虜嚗??啁撣豢? snapshot 銝血?詨?甇Ｘ???

雿輻蝭?嚗?
# ????隞??嚗??臬???safe_write_demo嚗?
.\run_long_test.ps1 start -Exe "python" -Args ".\safe_write_demo.py" -IntervalSec 30 -DurationHours 8

# ?迫隞??嚗??Start-Process ????蝔?嚗?
.\run_long_test.ps1 stop

# ?? snapshot
.\run_long_test.ps1 snapshot

?身嚗ntervalSec=30s, DurationHours=8, log thresholds: 10 hits per Interval => trigger snapshot
#>

param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("start","stop","status","snapshot")]
  [string]$Action,

  [string]$Exe = "python",
  [string]$Args = ".\safe_write_demo.py",
  [string]$ServiceName = "AdaptiveDCA",
  [int]$IntervalSec = 30,
  [int]$DurationHours = 8,
  [int]$ThresholdPerInterval = 10,
  [string]$LogPath = ".\logs\stderr.log",
  [string]$DryRunLogGlob = "$env:USERPROFILE\Desktop\adaptive_dca_dryrun_*.log",
  [string]$SnapshotRoot = "$env:ProgramData\adaptive_dca_snapshots"
)

function Ensure-SnapshotRoot {
  param($root)

  # 若呼叫時沒傳入 root，使用外層變數 $SnapshotRoot 當預設
  if (-not $root) { $root = $SnapshotRoot }

  # 確保不是 null 或空字串
  if (-not $root -or [string]::IsNullOrWhiteSpace([string]$root)) {
    Write-Warning "Ensure-SnapshotRoot: snapshot root is empty; using default ProgramData path"
    $root = Join-Path $env:ProgramData "adaptive_dca_snapshots"
  }

  if (-not (Test-Path $root)) { New-Item -Path $root -ItemType Directory -Force | Out-Null }
}

function Timestamp { (Get-Date).ToString("yyyyMMdd_HHmmss") }

function Make-Snapshot {
  param($reason)
  Ensure-SnapshotRoot -root $SnapshotRoot
  $ts = Timestamp
  $outdir = Join-Path $SnapshotRoot $ts
  New-Item -Path $outdir -ItemType Directory | Out-Null

  # copy recent logs
  try {
    if (Test-Path $LogPath) { Copy-Item $LogPath -Destination (Join-Path $outdir "stderr.log") -Force }
    $latest = Get-ChildItem -Path $DryRunLogGlob -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { Copy-Item $latest.FullName -Destination (Join-Path $outdir $latest.Name) -Force }
  } catch {
    $err = ($_ | Out-String).Trim()
    Write-Warning ("Failed to copy logs: " + $err)
  }

  # process list
  try {
    Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet | Out-File (Join-Path $outdir "process_list.txt")
  } catch {
    $err = ($_ | Out-String).Trim()
    Write-Warning ("Failed to capture process list: " + $err)
  }

  # open handles via handle.exe if available
  try {
    $handleExe = "C:\Windows\Sysinternals\handle.exe"
    if (Test-Path $handleExe) {
      & $handleExe > (Join-Path $outdir "handles.txt") 2>&1
    } else {
      "handle.exe not found; install from Sysinternals for handle snapshots" | Out-File (Join-Path $outdir "handles.txt")
    }
  } catch {
    $err = ($_ | Out-String).Trim()
    Write-Warning ("Failed to capture handles: " + $err)
  }

  # additional environment snapshot
  try {
    Get-CimInstance Win32_ComputerSystem | Out-File (Join-Path $outdir "computer_system.txt")
    Get-CimInstance Win32_OperatingSystem | Out-File (Join-Path $outdir "os_info.txt")
  } catch {
    $err = ($_ | Out-String).Trim()
    Write-Warning ("Failed to capture system info: " + $err)
  }

  # short explanation file
  "Snapshot created at $(Get-Date) Reason: $reason" | Out-File (Join-Path $outdir "README.txt")
  Write-Output "Snapshot saved to $outdir"
}

function Tail-LinesCount {
  param($path, $pattern, $lines = 200)
  if (-not (Test-Path $path)) { return 0 }
  try {
    $tail = Get-Content $path -Tail $lines -ErrorAction SilentlyContinue
    return ($tail | Select-String -Pattern $pattern -SimpleMatch).Count
  } catch {
    return 0
  }
}

function Rotate-Logs {
  param($path, $keepDays=7)
  if (-not (Test-Path $path)) { return }
  try {
    $dir = Split-Path $path -Parent
    $date = (Get-Date).ToString("yyyyMMdd_HHmmss")
    Copy-Item $path -Destination (Join-Path $dir ("stderr_" + $date + ".log")) -Force
    Get-ChildItem $dir -Filter "stderr_*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$keepDays) } | Remove-Item -Force -ErrorAction SilentlyContinue
  } catch {
    $err = ($_ | Out-String).Trim()
    Write-Warning ("Log rotate failed: " + $err)
  }
}

# persistent marker file for background PID if we start process
$PidMarker = Join-Path $env:TEMP "adaptive_dca_demo_pid.txt"

if ($Action -eq "start") {
  Ensure-SnapshotRoot -root $SnapshotRoot
  Rotate-Logs -path $LogPath -keepDays 7

  Write-Output ("Starting dry-run process: " + $Exe + " " + $Args)
  try {
    $proc = Start-Process -FilePath $Exe -ArgumentList $Args -WorkingDirectory (Get-Location) -PassThru -WindowStyle Hidden
    $proc.Id | Out-File -FilePath $PidMarker -Encoding ascii
    Write-Output ("Started PID " + $proc.Id + ". Monitoring for " + $DurationHours + " hour(s), interval " + $IntervalSec + " sec.")
  } catch {
    $err = ($_ | Out-String).Trim()
    Write-Warning ("Failed to start process: " + $err)
    exit 1
  }

  $end = (Get-Date).AddHours($DurationHours)
  while ((Get-Date) -lt $end) {
    Start-Sleep -Seconds $IntervalSec

    $countW0 = Tail-LinesCount -path $LogPath -pattern "WROTE 0 signals"
    $countKI = Tail-LinesCount -path $LogPath -pattern "KeyboardInterrupt"
    $countUn = Tail-LinesCount -path $LogPath -pattern "Unhandled exception"
    $countWarn = Tail-LinesCount -path $LogPath -pattern "WARNING replace_signals"

    Write-Output ("" -f ((Get-Date -Format "yyyy-MM-dd HH:mm:ss")), $("monitor: W0={0} KI={1} UN={2} WARN={3}" -f $countW0,$countKI,$countUn,$countWarn))

    if (($countW0 + $countKI + $countUn + $countWarn) -gt $ThresholdPerInterval) {
      $reason = "threshold_exceeded W0=$countW0 KI=$countKI UN=$countUn WARN=$countWarn"
      Make-Snapshot -reason $reason

      # optional auto-stop (閮餉圾?誑蝳?芸??迫)
      # Write-Output "Stopping NSSM service $ServiceName due to threshold."
      # & 'C:\nssm\nssm.exe' stop $ServiceName

      Start-Sleep -Seconds ([Math]::Min(600, $IntervalSec * 4))
    }
  }

  if (Test-Path $PidMarker) {
    try {
      $pid = Get-Content $PidMarker -Raw
      if ($pid) {
        Stop-Process -Id [int]$pid -ErrorAction SilentlyContinue
      }
    } catch {
      $err = ($_ | Out-String).Trim()
      Write-Warning ("Failed to stop PID " + $pid + ": " + $err)
    } finally {
      Remove-Item $PidMarker -Force -ErrorAction SilentlyContinue
    }
  }
  Write-Output "Monitoring loop finished."
  exit 0
}

if ($Action -eq "stop") {
  if (Test-Path $PidMarker) {
    try {
      $pid = Get-Content $PidMarker -Raw
      if ($pid) {
        Stop-Process -Id [int]$pid -ErrorAction SilentlyContinue
        Write-Output ("Stopped PID " + $pid)
      }
    } catch {
      $err = ($_ | Out-String).Trim()
      Write-Warning ("Failed to stop PID " + $pid + ": " + $err)
    } finally {
      Remove-Item $PidMarker -Force -ErrorAction SilentlyContinue
    }
  } else {
    Write-Output "No running marker found. If process started via NSSM, use NSSM to stop."
  }
  exit 0
}

if ($Action -eq "snapshot") {
  Make-Snapshot -reason "manual_snapshot"
  exit 0
}

if ($Action -eq "status") {
  if (Test-Path $PidMarker) {
    $pid = Get-Content $PidMarker -Raw
    Write-Output ("Marker PID: " + $pid)
    if ($pid) {
      try {
        Get-Process -Id [int]$pid | Select Id,ProcessName,CPU,StartTime
      } catch {
        Write-Warning ("Process " + $pid + " not found.")
      }
    }
  } else {
    Write-Output "No marker file found."
  }
  exit 0
}
