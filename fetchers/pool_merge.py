# fetchers/pool_merge.py  (patched)
import time
import pandas as pd

def tag_from_sources(turn_df, mkt_df):
    turn_set = set(turn_df['ticker'].astype(str).tolist()) if turn_df is not None else set()
    mkt_set = set(mkt_df['ticker'].astype(str).tolist()) if mkt_df is not None else set()
    all_tickers = list(turn_set.union(mkt_set))
    rows = []
    for t in all_tickers:
        tag = []
        name = None
        turnover = None
        marketcap = None
        price = None
        if t in turn_set:
            tag.append('turnover')
            row = turn_df[turn_df['ticker']==t].iloc[0]
            name = row.get('name') if name is None else name
            turnover = row.get('turnover') if 'turnover' in row.index else None
            if 'price' in row.index:
                price = row.get('price')
        if t in mkt_set:
            tag.append('mktcap')
            row = mkt_df[mkt_df['ticker']==t].iloc[0]
            name = row.get('name') if name is None else name
            marketcap = row.get('marketcap') if 'marketcap' in row.index else None
            if price is None and 'price' in row.index:
                price = row.get('price')
        rows.append({
            'ticker': t,
            'name': name,
            'turnover': turnover,
            'marketcap': marketcap,
            'price': price,
            'tags': tag,
            'ts': int(time.time())
        })
    df = pd.DataFrame(rows)
    df['is_both'] = df['tags'].apply(lambda x: 1 if len(x)>1 else 0)
    df = df.sort_values(['is_both','marketcap','turnover','ticker'], ascending=[False,False,False,True])
    df = df.drop(columns=['is_both'])
    return df.reset_index(drop=True)
