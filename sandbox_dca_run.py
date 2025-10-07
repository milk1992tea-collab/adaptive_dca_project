# sandbox_dca_run.py (patched to use turnover_adapter)
import math, time
from fetchers.mktcap_fetcher import fetch_marketcap_top
from fetchers.turnover_adapter import fetch_turnover_top
from fetchers.pool_merge import tag_from_sources
import store_db

def place_order_stub(ticker, qty, price=None):
    return {'ticker': ticker, 'qty': qty, 'status': 'filled', 'price': price or 0.0, 'ts': int(time.time())}

def run_sandbox_dca(amount_total=1000, allocation="equal", pool_name="merged", min_per_stock_amount=10.0):
    store_db.init_db()
    tdf = fetch_turnover_top(20)
    mdf = fetch_marketcap_top(20)
    if 'price' not in mdf.columns:
        mdf['price'] = 100.0
    merged = tag_from_sources(tdf, mdf)
    price_map = {row['ticker']: row.get('price', 100.0) for row in mdf.to_dict(orient="records")}
    merged['price'] = merged['ticker'].map(price_map).fillna(100.0)
    store_db.save_list('turnover', tdf.to_dict(orient="records"))
    store_db.save_list('mktcap', mdf.to_dict(orient="records"))
    store_db.save_list('merged', merged.to_dict(orient="records"))
    print("Saved lists: turnover,mktcap,merged. merged count=", len(merged))
    tickers = merged['ticker'].tolist()
    per = amount_total / max(1, len(tickers))
    results = []
    for t in tickers:
        price = float(merged.loc[merged["ticker"]==t, "price"].iloc[0])
        qty = math.floor(per / max(1e-6, price))
        if qty <= 0:
            if per >= min_per_stock_amount:
                qty = 1
            else:
                continue
        r = place_order_stub(t, qty, price=price)
        results.append(r)
    store_db.insert_dca_run("sandbox_dca", results, status="done")
    print("DCA simulated orders:", results)
    return results

if __name__ == "__main__":
    run_sandbox_dca()
