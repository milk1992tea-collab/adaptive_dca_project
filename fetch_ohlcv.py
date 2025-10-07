# fetch_ohlcv.py
import ccxt, pandas as pd
ex = ccxt.binance({'enableRateLimit': True})
# change symbol/timeframe/limit as needed
ohlcv = ex.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=500)
df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.to_csv('ohlcv.csv', index=False)
print("wrote", len(df), "rows to ohlcv.csv")
