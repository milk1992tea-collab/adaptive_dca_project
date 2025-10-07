import ccxt, traceback
ex = ccxt.bybit({'enableRateLimit': True})
print('EXCHANGE', ex.id)
try:
    ex.load_markets()
    print('MARKETS_OK')
except Exception as e:
    print('LOAD_ERR', e)
try:
    df = __import__('backtester').fetch_ohlcv('BTC/USDT:USDT', timeframe='5m', limit=10)
    print('ROWS', len(df))
except Exception as e:
    print('FETCH_ERR', e)
    traceback.print_exc()
