# cancel_orders.py
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
        print("🔍 查詢所有未成交掛單...")
        open_orders = client.get_open_orders()
        if not open_orders:
            print("✅ 沒有未成交掛單")
            return

        for order in open_orders:
            symbol = order["symbol"]
            order_id = order["orderId"]
            print(f"🛑 取消 {symbol} 訂單 {order_id} ...")
            result = client.cancel_order(symbol=symbol, orderId=order_id)
            print("   → 已取消:", result["status"])
        print("🎉 所有掛單已清理完成")
    except Exception as e:
        print("❌ 操作失敗，錯誤訊息：", str(e))

if __name__ == "__main__":
    main()