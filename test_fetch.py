# test_fetch.py
import time
import ccxt

symbols = [
    'BTC/USDT:USDT','ETH/USDT:USDT','SOL/USDT:USDT','XPL/USDT:USDT',
    'XRP/USDT:USDT','DOGE/USDT:USDT','ASTER/USDT:USDT','PUMPFUN/USDT:USDT',
    'SOMI/USDT:USDT','SUI/USDT:USDT',
    # 若需測試被排除的幣種也可加在下面
    'STRK/USDT:USDT','XAN/USDT:USDT','VFY/USDT:USDT','KAITO/USDT:USDT','APT/USDT:USDT'
]

exchange = ccxt.bybit({
    "enableRateLimit": True,
    "timeout": 15000,  # 毫秒，短一點可快速定位卡住的 call
})

print("Starting fetch checks:", time.strftime("%Y-%m-%d %H:%M:%S"))
for s in symbols:
    try:
        t0 = time.time()
        print(f"-> Fetching {s} ...", flush=True)
        # 嘗試抓一筆 1m 或 15m（limit=10）以快速回應
        ohlcv = exchange.fetch_ohlcv(s, timeframe='1m', limit=10)
        dt = time.time() - t0
        print(f"   OK {s}  rows={len(ohlcv)} elapsed={dt:.2f}s", flush=True)
    except Exception as e:
        dt = time.time() - t0
        print(f"   ERR {s}  elapsed={dt:.2f}s  error={type(e).__name__}: {e}", flush=True)
print("Done", time.strftime("%Y-%m-%d %H:%M:%S"))