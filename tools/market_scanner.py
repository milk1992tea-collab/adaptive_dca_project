# market_scanner.py
import os
import pandas as pd
from binance.client import Client

# 初始化 Binance API
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET)

# === 抓取現貨成交額前 N 名 ===
def top_spot_symbols(limit=50, quote="USDT"):
    tickers = client.get_ticker()
    df = pd.DataFrame(tickers)
    df["quoteVolume"] = df["quoteVolume"].astype(float)
    df = df[df["symbol"].str.endswith(quote)]  # 只要 USDT 交易對
    df = df.sort_values("quoteVolume", ascending=False).head(limit)
    return df[["symbol", "quoteVolume"]]

# === 抓取永續合約成交額前 N 名 ===
def top_futures_symbols(limit=50):
    tickers = client.futures_ticker()
    df = pd.DataFrame(tickers)
    df["quoteVolume"] = df["quoteVolume"].astype(float)
    df = df.sort_values("quoteVolume", ascending=False).head(limit)
    return df[["symbol", "quoteVolume"]]

# === 主流程 ===
def scan_market(limit=50):
    spot = top_spot_symbols(limit)
    futures = top_futures_symbols(limit)
    return {
        "spot": spot,
        "futures": futures
    }

if __name__ == "__main__":
    result = scan_market(50)
    print("=== 現貨成交額前 50 ===")
    print(result["spot"].head(10))
    print("=== 永續合約成交額前 50 ===")
    print(result["futures"].head(10))