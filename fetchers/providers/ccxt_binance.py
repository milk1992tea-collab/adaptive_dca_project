# fetchers/providers/ccxt_binance.py
import logging
import pandas as pd

logger = logging.getLogger("providers.ccxt_binance")

def _load_creds():
    try:
        from fetchers.credentials_loader import load_credentials
        creds = load_credentials().get("ccxt", {}) or {}
    except Exception:
        creds = {}
    return creds

def get_turnover_top(n=20, exchange_id='binance', symbol_usd_suffix='USDT'):
    creds = _load_creds()
    api_key = creds.get("api_key") or creds.get("apiKey") or None
    api_secret = creds.get("api_secret") or creds.get("secret") or None

    try:
        import ccxt
    except Exception as e:
        logger.error("ccxt provider: ccxt not installed: %s", e)
        raise

    ex_cls = getattr(ccxt, exchange_id, None)
    if ex_cls is None:
        logger.error("ccxt provider: exchange %s not found in ccxt", exchange_id)
        raise RuntimeError(f"exchange {exchange_id} not found")

    ex = ex_cls({
        'apiKey': api_key,
        'secret': api_secret,
        # optional: enable rateLimit or verbose for debugging
    })

    try:
        tickers = ex.fetch_tickers()
    except Exception as e:
        logger.error("ccxt provider: fetch_tickers failed: %s", e)
        raise

    rows = []
    for k, v in list(tickers.items())[:n]:
        symbol = v.get('symbol') or k
        # normalize USDT pairs to base asset when possible
        if '/' in symbol and symbol.endswith('/' + symbol_usd_suffix):
            ticker = symbol.split('/')[0].upper()
        else:
            ticker = symbol.upper().split('/')[0]
        volume = v.get('quoteVolume') or v.get('baseVolume') or 0
        rows.append({"ticker": ticker, "name": ticker, "turnover": volume})
    return pd.DataFrame(rows)
