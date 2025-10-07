import json
from bybit_utils import get_balance, get_position
from pybit.unified_trading import HTTP

# ⚠️ 請填入你的測試網 API Key / Secret
API_KEY = "Arvl0ldQYWAiqw526Z"
API_SECRET = "EuAHPXQJB2XrF54m5vtpifhTcPOqleHWRw0T"

session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def check_api_status():
    try:
        resp = session.get_api_key_information()
        print("[API 狀態檢查]")
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[錯誤] API 狀態檢查失敗: {e}")

def precheck(symbol="BTCUSDT"):
    print("=== 策略啟動前檢查 ===")

    # 1. API Key 狀態
    check_api_status()

    # 2. 餘額檢查 (統一帳戶)
    balance = get_balance(accountType="UNIFIED")
    if balance:
        print("[檢查通過] 已成功讀取統一帳戶餘額")

    # 3. 倉位檢查
    pos = get_position(symbol, category="linear")
    if pos:
        print("[檢查通過] 已成功讀取倉位資訊")

    print("=== 檢查完成 ===")

if __name__ == "__main__":
    precheck()