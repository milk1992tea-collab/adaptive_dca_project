import pandas as pd
import ccxt

def fetch_multi_timeframes(symbol="BTC/USDT", limit=1000):
    """
    從 Bybit 抓取多週期 K 線資料
    symbol: 幣對 (例如 "BTC/USDT")
    limit: K 線數量
    回傳: dict { timeframe: DataFrame }
    """
    exchange = ccxt.bybit({
        "options": {"defaultType": "future"}
    })

    timeframes = ["1m", "15m", "1h", "4h", "1d"]
    dfs = {}

    for tf in timeframes:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            dfs[tf] = df
        except Exception as e:
            print(f"抓取 {symbol} {tf} 失敗: {e}")
            dfs[tf] = pd.DataFrame()

    return dfs

if __name__ == "__main__":
    dfs = fetch_multi_timeframes("BTC/USDT", limit=10)
    for tf, df in dfs.items():
        print(f"\n=== {tf} ===")
        print(df.head())