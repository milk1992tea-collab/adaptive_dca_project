# list_orders.py
import json
from pathlib import Path
from binance.client import Client

CONFIG_FILE = Path(__file__).parent / "config.json"

# 你可以在這裡自由增減要查詢的交易對
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

def load_keys():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        return cfg.get("API_KEY"), cfg.get("API_SECRET")
    else:
        raise FileNotFoundError("找不到 config.json，請確認放在 tools/ 資料夾")

def main():
    api_key, api_secret = load_keys()
    client = Client(api_key, api_secret)
    client.API_URL = 'https://testnet.binance.vision/api'  # 強制指定 Testnet

    try:
        for symbol in SYMBOLS:
            print(f"\n🔍 查詢 {symbol} 最近的訂單紀錄...")
            orders = client.get_all_orders(symbol=symbol, limit=10)
            if not orders:
                print(f"✅ {symbol} 沒有任何歷史訂單")
                continue

            for o in orders:
                print(f"ID={o['orderId']} | 狀態={o['status']} | 類型={o['type']} | "
                      f"方向={o['side']} | 價格={o['price']} | 成交數量={o['executedQty']} | "
                      f"下單時間={o['time']}")
    except Exception as e:
        print("❌ 查詢失敗，錯誤訊息：", str(e))

if __name__ == "__main__":
    main()