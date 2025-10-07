import os
import pandas as pd
import ccxt

from code.get_top_50_assets import get_top_50_assets_by_volume

def download_ohlcv(exchange, symbol, timeframe, limit=1000):
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=[
        "datetime","open","high","low","close","volume"
    ])
    df["datetime"] = pd.to_datetime(df["datetime"], unit="ms")
    df.set_index("datetime", inplace=True)
    return df

if __name__ == "__main__":
    # 确保已安装：ccxt, pandas
    # pip install ccxt pandas

    project_root = os.path.dirname(os.path.dirname(__file__))
    ohlcv_dir    = os.path.join(project_root, "data", "ohlcv")
    os.makedirs(ohlcv_dir, exist_ok=True)

    exchange = ccxt.binance()
    assets   = get_top_50_assets_by_volume()

    for sym in assets:
        sym_file = sym.replace("/", "_")
        for tf in ["5m", "4h"]:
            try:
                df = download_ohlcv(exchange, sym, tf, limit=1000)
                out_path = os.path.join(ohlcv_dir, f"{sym_file}_{tf}.csv")
                df.to_csv(out_path)
                print(f"Saved {out_path}")
            except Exception as e:
                print(f"Failed {sym} {tf}: {e}")