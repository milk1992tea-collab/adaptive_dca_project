from pybit.unified_trading import HTTP
import json
import traceback

API_KEY ="Arvl0ldQYWAiqw526Z"
API_SECRET ="EuAHPXQJB2XrF54m5vtpifhTcPOqleHWRw0T"

def main():
    session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)

    # 1. 查詢帳號資訊（UID）
    try:
        acc_info = session.get_account_info()
        print("[帳號資訊]")
        print(json.dumps(acc_info, indent=2, ensure_ascii=False))
    except Exception as e:
        print("[錯誤] 無法取得帳號資訊")
        traceback.print_exc()

    # 2. 查詢餘額
    try:
        balance = session.get_wallet_balance(accountType="UNIFIED")
        print("[餘額檢查]")
        print(json.dumps(balance, indent=2, ensure_ascii=False))
    except Exception as e:
        print("[錯誤] 無法取得餘額")
        traceback.print_exc()

if __name__ == "__main__":
    main()