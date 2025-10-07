from pybit.unified_trading import HTTP

# 初始化 Session（正式網要改 testnet=False）
session = HTTP(
    testnet=True,
    api_key="Z8KuHMC0dGPAippEbY",
    api_secret="QkMQxXHvpLUIrULFziFxuiEw250yGuxsCAzU"
)

# 1️⃣ 下單：買入 0.01 BTCUSDT 市價單
order = session.place_order(
    category="linear",   # 永續合約
    symbol="BTCUSDT",
    side="Buy",          # 買入
    orderType="Market",  # 市價單
    qty="0.01"
)
print("下單結果:", order)

# 2️⃣ 查詢未成交訂單
open_orders = session.get_open_orders(category="linear", symbol="BTCUSDT")
print("未成交訂單:", open_orders)

# 3️⃣ 查詢倉位
positions = session.get_positions(category="linear", symbol="BTCUSDT")
print("當前倉位:", positions)

# 4️⃣ 平倉：賣出 0.01 BTCUSDT 市價單
close_order = session.place_order(
    category="linear",
    symbol="BTCUSDT",
    side="Sell",         # 賣出
    orderType="Market",
    qty="0.01",
    reduceOnly=True      # 僅用於平倉
)
print("平倉結果:", close_order)