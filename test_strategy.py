from bybit_utils import open_position, close_position, get_position
from strategy import dca_strategy
import time

symbol = "BTCUSDT"

print("=== 策略測試開始 ===")

for i in range(10):  # 模擬 10 根 K 線
    price = 100 + i * 5  # 假設價格走勢
    decision = dca_strategy(price)

    if decision["action"] == "buy":
        open_position(symbol, decision["qty"], side="Buy")
    elif decision["action"] == "sell":
        close_position(symbol, decision["qty"], side="Sell")
    else:
        print(f"[{i}] 價格 {price} → 無操作")

    time.sleep(2)

print("=== 策略測試結束 ===")