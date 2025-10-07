# portfolio_status.py
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
        print("🔍 查詢帳戶資產狀況...")
        account_info = client.get_account()
        balances = account_info["balances"]

        non_zero_assets = [
            b for b in balances if float(b["free"]) > 0 or float(b["locked"]) > 0
        ]

        if not non_zero_assets:
            print("✅ 帳戶沒有任何資產")
            return

        for asset in non_zero_assets:
            print(f"{asset['asset']}: free={asset['free']}, locked={asset['locked']}")
    except Exception as e:
        print("❌ 查詢失敗，錯誤訊息：", str(e))

if __name__ == "__main__":
    main()