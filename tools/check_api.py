# check_api.py
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
    client = Client(api_key, api_secret, testnet=True)

    try:
        account = client.get_account()
        balances = account.get("balances", [])
        print("✅ API 測試成功，帳戶餘額：")
        for b in balances:
            if float(b["free"]) > 0 or float(b["locked"]) > 0:
                print(f"{b['asset']}: free={b['free']}, locked={b['locked']}")
    except Exception as e:
        print("❌ API 測試失敗，錯誤訊息：", str(e))

if __name__ == "__main__":
    main()