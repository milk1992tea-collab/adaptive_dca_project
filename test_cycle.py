from bybit_utils import get_balance, stress_test

symbol = "BTCUSDT"
qty = "5"           # 代表 5 USDT 名義價值，符合最小下單金額
cycles = 5          # 測試循環次數
delay_seconds = 2   # 每步驟之間的延遲秒數

print("=== 測試開始 ===")
get_balance()

stress_test(symbol, qty, cycles=cycles, delay=delay_seconds)

print("\n=== 測試結束 ===")
get_balance()