import json
import csv
from pathlib import Path

BEST_PATH = "best_params.json"
LOG_PATH = "live_trades.csv"

def view_best_params():
    if Path(BEST_PATH).exists():
        with open(BEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("=== 最佳參數 ===")
        print(json.dumps(data.get("params", {}), indent=2, ensure_ascii=False))
        print(f"最佳分數: {data.get('score')}")
        print(f"更新時間: {data.get('timestamp')}")
    else:
        print("[提示] 尚未產生 best_params.json")

def view_trade_log(last_n=10):
    if Path(LOG_PATH).exists():
        print(f"\n=== 最近 {last_n} 筆交易紀錄 ===")
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            for row in reader[-last_n:]:
                print(f"{row['timestamp']} | {row['action']} {row['qty']} {row['symbol']} @ {row['price']} | {row['note']}")
    else:
        print("[提示] 尚未產生 live_trades.csv")

if __name__ == "__main__":
    view_best_params()
    view_trade_log(last_n=10)