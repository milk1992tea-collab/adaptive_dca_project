# fetchers/providers/coingecko.py
import requests
import pandas as pd
import logging
logger = logging.getLogger("providers.coingecko")
COINGECKO_MARKETS_URL = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&price_change_percentage=24h'
def get_turnover_top(n=20, timeout=10):
    try:
        r = requests.get(COINGECKO_MARKETS_URL, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("coingecko fetch failed: %s", e)
        raise
    rows = []
    for it in data[:n]:
        rows.append({"ticker": str(it.get("symbol","")).upper(), "name": it.get("name"), "turnover": it.get("total_volume", 0)})
    return pd.DataFrame(rows)
