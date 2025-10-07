import ccxt

def fetch_24h_volume():
    exchange = ccxt.binance({
        "apiKey": "CJ6QeXhEdXesdyVZekgDIjxQXfLdliW0KqKTFblufhZcTFdGFoG6WCwp6NraAbof",
        "secret": "YKzM0yVKvBHO447FXjIJqDcsnS9ccEEheB53cw1LIAOIovMp9TReOlxDfxXFsMB5",
    })
    markets = exchange.fetch_tickers()
    return {symbol: info["quoteVolume"] for symbol, info in markets.items()}