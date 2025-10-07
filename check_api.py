import ccxt

exchange = ccxt.binance({
    "apiKey": "Z8KuHMC0dGPAippEbY",
    "secret": "QkMQxXHvpLUIrULFziFxuiEw250yGuxsCAzU",
    "enableRateLimit": True,
    "options": {"defaultType": "future"}
})
exchange.set_sandbox_mode(True)  # 測試網

try:
    balance = exchange.fetch_balance()
    print("✅ API Key 驗證成功，可以使用")
    print(balance)
except Exception as e:
    print("❌ API Key 驗證失敗:", str(e))