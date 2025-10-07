# place_test_order.py
import json
from pathlib import Path
from binance.client import Client

CONFIG_FILE = Path(__file__).parent / "config.json"

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
        print("🚀 嘗試下單 10 USDT 的 BTCUSDT 市價單...")
        order = client.create_order(
            symbol="BTCUSDT",
            side="BUY",
            type="MARKET",
            quoteOrderQty=10  # 用 10 USDT 買 BTC
        )
        print("✅ 下單成功！訂單資訊：")
        print(order)
    except Exception as e:
        print("❌ 下單失敗，錯誤訊息：", str(e))

if __name__ == "__main__":
    main()