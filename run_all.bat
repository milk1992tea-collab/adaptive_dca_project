@echo off
echo ================================
echo   Bybit 策略自動檢查與啟動
echo ================================

REM 1. 執行 precheck.py
echo [步驟 1] 檢查 API / 餘額 / 倉位...
python precheck.py
IF %ERRORLEVEL% NEQ 0 (
    echo [錯誤] precheck.py 執行失敗，請檢查環境。
    pause
    exit /b
)

REM 2. 啟動 run_live_strategy.py
echo [步驟 2] 啟動策略模擬...
python run_live_strategy.py

echo ================================
echo   策略執行完成
echo ================================
pause