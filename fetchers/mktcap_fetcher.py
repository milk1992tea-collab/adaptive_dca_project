# fetchers\mktcap_fetcher.py
# 依賴: requests, pandas
# 功能: 以 CoinGecko API 抓取加密貨幣市值排行，含快取回退與簡單日誌
import os
import json
import time
import logging
from typing import Optional
import requests
import pandas as pd

logger = logging.getLogger("mktcap_fetcher")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)

CACHE_DIR = os.environ.get("ADAPTIVE_DCA_CACHE", os.path.join(os.path.expanduser("~"), ".adaptive_dca_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "mktcap_last_success.json")

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&price_change_percentage=24h"

def _save_cache(records):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"ts": int(time.time()), "records": records}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Failed to save cache: %s", e)

def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load cache: %s", e)
        return None

def normalize_ticker(t: str) -> str:
    if t is None:
        return ""
    return str(t).strip().upper()

def fetch_from_coingecko(timeout=15) -> Optional[pd.DataFrame]:
    try:
        r = requests.get(COINGECKO_MARKETS_URL, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            logger.warning("Unexpected coingecko payload")
            return None
        rows = []
        for it in data:
            # id,symbol,name,market_cap
            rows.append({
                "ticker": normalize_ticker(it.get("symbol")),
                "name": it.get("name"),
                "marketcap": float(it.get("market_cap") or 0),
                "price": float(it.get("current_price") or 0),
            })
        df = pd.DataFrame(rows)
        df = df.drop_duplicates(subset="ticker")
        return df
    except Exception as e:
        logger.warning("fetch_from_coingecko failed: %s", e)
        return None

def fetch_marketcap_top(n=20, use_cache_on_fail=True) -> pd.DataFrame:
    df = fetch_from_coingecko()
    if df is not None and not df.empty:
        df = df.sort_values("marketcap", ascending=False).head(n)
        records = df.to_dict(orient="records")
        _save_cache(records)
        logger.info("Fetched %d records from CoinGecko", len(records))
        return df
    logger.error("CoinGecko fetch failed")
    if use_cache_on_fail:
        cached = _load_cache()
        if cached and "records" in cached:
            logger.warning("Using cached mktcap data ts=%d", cached.get("ts", 0))
            return pd.DataFrame(cached["records"])
    return pd.DataFrame(columns=["ticker", "name", "marketcap", "price"])

if __name__ == "__main__":
    print(fetch_marketcap_top(20))
