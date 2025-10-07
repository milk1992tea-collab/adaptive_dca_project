# fetchers/providers/test_stub.py
import pandas as pd
def get_turnover_top(n=20):
    samples = [("BTC","Bitcoin",2.424609e9),("ETH","Ethereum",5.418299e8),("BNB","BNB",1.77856e8)]
    rows = [{"ticker": s[0], "name": s[1], "turnover": s[2]} for s in samples[:n]]
    i = len(rows)
    while len(rows) < n:
        rows.append({"ticker": f"TK{i}", "name": f"Token{i}", "turnover": 1000.0})
        i += 1
    return pd.DataFrame(rows)
