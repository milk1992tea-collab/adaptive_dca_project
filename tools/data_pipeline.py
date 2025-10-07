# data_pipeline.py
import pandas as pd
import pandas_ta as ta
from binance.client import Client
import os

# === 初始化 Binance API ===
def init_client():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("⚠️ 請先設定 BINANCE_API_KEY / BINANCE_API_SECRET 環境變數或 .env 檔")
    return Client(api_key, api_secret)

# === 抓取 K 線資料 ===
def fetch_klines(symbol="BTCUSDT", interval="5m", limit=1000):
    client = init_client()
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# === TD Sequential (簡化版) ===
def calc_td_seq(df, length=13):
    td = [0] * len(df)
    count = 0
    for i in range(1, len(df)):
        if df["close"].iloc[i] < df["close"].iloc[i-1]:
            count += 1
        else:
            count = 0
        td[i] = count
    df["td_seq"] = td
    return df

# === 技術指標計算 ===
def add_indicators(df):
    # RSI
    df["rsi"] = ta.rsi(df["close"], length=14)

    # MACD (內部已用 EMA)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd"] = macd["MACD_12_26_9"]
    df["signal"] = macd["MACDs_12_26_9"]
    df["hist"] = macd["MACDh_12_26_9"]

    # 布林帶 (基於 EMA)
    bb = ta.bbands(df["close"], length=20, std=2, mamode="ema")
    df["bb_lower"] = bb.iloc[:, 0]
    df["bb_middle"] = bb.iloc[:, 1]
    df["bb_upper"] = bb.iloc[:, 2]

    # ATR
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # EMA (多週期)
    df["ema20"] = ta.ema(df["close"], length=20)
    df["ema50"] = ta.ema(df["close"], length=50)
    df["ema100"] = ta.ema(df["close"], length=100)

    # SKDJ (Stochastic KDJ)
    stoch = ta.stoch(df["high"], df["low"], df["close"], k=14, d=3, smooth_k=3)
    df["kdj_k"] = stoch["STOCHk_14_3_3"]
    df["kdj_d"] = stoch["STOCHd_14_3_3"]

    # TD Sequential
    df = calc_td_seq(df, length=13)

    return df.dropna()

# === 主流程 ===
def build_dataset(symbol="BTCUSDT", interval="5m", limit=1000):
    df = fetch_klines(symbol, interval, limit)
    df = add_indicators(df)
    return df

if __name__ == "__main__":
    df = build_dataset("BTCUSDT", "5m", 500)
    print(df.tail())