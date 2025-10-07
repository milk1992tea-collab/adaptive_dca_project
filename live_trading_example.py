import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# === 1. 初始化交易所 ===
exchange = ccxt.binance({
    "apiKey": "你的API_KEY",
    "secret": "你的API_SECRET",
    "enableRateLimit": True
})

symbol = "BTC/USDT"
timeframe = "1h"
capital_usdt = 100  # 小額測試倉位
stop_loss_pct = 0.02   # 單筆最大虧損 2%
take_profit_pct = 0.05 # 單筆止盈 5%

# === 2. 抓取最新 K 線資料 ===
def fetch_data(symbol, timeframe="1h", limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# === 3. 訊號判斷 (RSI + MACD) ===
def generate_signal(df):
    df["rsi"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd"], df["macd_signal"] = macd["MACD_12_26_9"], macd["MACDs_12_26_9"]

    latest = df.iloc[-1]
    signal = None
    if latest["rsi"] < 30 and latest["macd"] > latest["macd_signal"]:
        signal = "buy"
    elif latest["rsi"] > 70 and latest["macd"] < latest["macd_signal"]:
        signal = "sell"
    return signal

# === 4. 下單邏輯 ===
def place_order(signal):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker["last"]

    if signal == "buy":
        amount = capital_usdt / price
        order = exchange.create_market_buy_order(symbol, amount)
        print(f"✅ Buy {amount:.5f} {symbol} @ {price}")
        return {"side":"buy","price":price,"amount":amount,"time":datetime.now()}
    elif signal == "sell":
        balance = exchange.fetch_balance()
        amount = balance["free"]["BTC"]  # 假設交易 BTC/USDT
        if amount > 0:
            order = exchange.create_market_sell_order(symbol, amount)
            print(f"✅ Sell {amount:.5f} {symbol} @ {price}")
            return {"side":"sell","price":price,"amount":amount,"time":datetime.now()}
    return None

# === 5. 主程式 ===
if __name__ == "__main__":
    df = fetch_data(symbol, timeframe)
    signal = generate_signal(df)
    if signal:
        trade = place_order(signal)
        if trade:
            # 風險控制：計算止盈止損價位
            entry_price = trade["price"]
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
            print(f"📉 Stop Loss: {stop_loss:.2f}, 📈 Take Profit: {take_profit:.2f}")