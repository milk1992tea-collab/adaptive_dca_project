# fetchers/turnover_real.py
import pandas as pd

def get_turnover_top(n=20):
    # 最小可用 stub：回傳 n 筆 ticker,name,turnover
    samples = [
        ("BTC","Bitcoin",2424609000.0),
        ("ETH","Ethereum",541829900.0),
        ("BNB","BNB",177856000.0),
        ("USDT","Tether",177522806.0),
        ("XRP","XRP",174612376.0)
    ]
    rows = []
    for i in range(min(n, len(samples))):
        t = samples[i]
        rows.append({"ticker": t[0], "name": t[1], "turnover": t[2]})
    i = len(rows)
    while len(rows) < n:
        rows.append({"ticker": f"TK{i}", "name": f"Token{i}", "turnover": 1000.0})
        i += 1
    return pd.DataFrame(rows)
