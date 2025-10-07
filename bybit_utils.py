from pybit.unified_trading import HTTP
import json

# ⚠️ 請填入你的測試網 API Key / Secret
API_KEY = "Arvl0ldQYWAiqw526Z"
API_SECRET ="EuAHPXQJB2XrF54m5vtpifhTcPOqleHWRw0T"

# 建立測試網 Session
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

# === 查餘額 ===
def get_balance(accountType="UNIFIED"):
    try:
        balance = session.get_wallet_balance(accountType=accountType)
        coins = balance.get("result", {}).get("list", [])[0].get("coin", [])
        print("[餘額檢查]")
        for c in coins:
            if c["coin"] == "USDT":
                print(f"USDT: {c['walletBalance']}")
        return balance
    except Exception as e:
        print(f"[錯誤] 查餘額失敗: {e}")
        return None

# === 查倉位 ===
def get_position(symbol, category="linear"):
    try:
        pos = session.get_positions(category=category, symbol=symbol)
        print(f"[查倉] {symbol} → {json.dumps(pos.get('result', {}), ensure_ascii=False)}")
        return pos
    except Exception as e:
        print(f"[錯誤] 查倉失敗: {e}")
        return None

# === 開倉 ===
def open_position(symbol, qty, side="Buy", category="linear"):
    try:
        order = session.place_order(
            category=category,
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty
        )
        print(f"[開倉] {side} {qty} {symbol} → orderId={order.get('result', {}).get('orderId')}, retCode={order.get('retCode')}")
        return order
    except Exception as e:
        print(f"[錯誤] 開倉失敗: {e}")
        return None

# === 平倉 ===
def close_position(symbol, qty, side="Sell", category="linear"):
    try:
        order = session.place_order(
            category=category,
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            reduceOnly=True   # ✅ 確保是平倉
        )
        print(f"[平倉] {side} {qty} {symbol} → orderId={order.get('result', {}).get('orderId')}, retCode={order.get('retCode')}")
        return order
    except Exception as e:
        print(f"[錯誤] 平倉失敗: {e}")
        return None