# minimal_agent.py
# Usage: python minimal_agent.py --mode backtest --data ohlcv.csv --n1 10 --n2 30
import os, sys, argparse, time, json
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import optuna
import ccxt

DEFAULT_DATA = "ohlcv.csv"
DATE_COL = "timestamp"

def load_ohlcv(csv_path):
    df = pd.read_csv(csv_path)
    if DATE_COL in df.columns:
        try:
            df[DATE_COL] = pd.to_datetime(df[DATE_COL])
            df.set_index(DATE_COL, inplace=True)
        except Exception:
            pass
    df = df.rename(columns={"close":"Close","open":"Open","high":"High","low":"Low","volume":"Volume"})
    return df[["Open","High","Low","Close","Volume"]]

class MACross(Strategy):
    n1 = 10
    n2 = 30

    def init(self):
        # Use a lambda so Backtesting.I receives a pandas Series and rolling works correctly
        self.ma1 = self.I(lambda s, n: pd.Series(s).rolling(n).mean().to_numpy(), self.data.Close, self.n1)
        self.ma2 = self.I(lambda s, n: pd.Series(s).rolling(n).mean().to_numpy(), self.data.Close, self.n2)

    def next(self):
        if crossover(self.ma1, self.ma2):
            if getattr(self.position, "is_short", False):
                try:
                    self.position.close()
                except Exception:
                    pass
            self.buy()
        elif crossover(self.ma2, self.ma1):
            if getattr(self.position, "is_long", False):
                try:
                    self.position.close()
                except Exception:
                    pass
            self.sell()

def run_backtest(df, n1=10, n2=30, cash=1_000_000, fee=0.001):
    class S(MACross): pass
    S.n1 = int(n1); S.n2 = int(n2)
    bt = Backtest(df, S, cash=cash, commission=fee, trade_on_close=True)
    stats = bt.run()
    return bt, stats

def optuna_search(csv_path, trials=50):
    df = load_ohlcv(csv_path)
    def objective(trial):
        n1 = trial.suggest_int("n1", 2, 50)
        n2 = trial.suggest_int("n2", 5, 200)
        if n1 >= n2:
            return -1e6
        bt, stats = run_backtest(df, n1=n1, n2=n2)
        sharpe = stats.get('Sharpe Ratio', None)
        if sharpe is None or pd.isna(sharpe):
            return -1e6
        return float(sharpe)
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=trials)
    return study

class PaperExecutor:
    def __init__(self, exchange, symbol, qty=None):
        self.ex = exchange
        self.symbol = symbol
        self.qty = qty or 0.001
        self.state = {"position": None}
    def fetch_price(self):
        ob = self.ex.fetch_ticker(self.symbol)
        return ob.get('last', None)
    def decide_ma(self, df, n1, n2):
        ma1 = df['Close'].rolling(n1).mean().iloc[-1]
        ma2 = df['Close'].rolling(n2).mean().iloc[-1]
        return "buy" if ma1 > ma2 else "sell"
    def paper_step(self, df, n1, n2):
        action = self.decide_ma(df, n1, n2)
        price = self.fetch_price()
        ts = pd.Timestamp.utcnow().isoformat()
        if action == "buy" and self.state["position"] != "long":
            self.state["position"] = "long"
            print(f"{ts} PAPER BUY {self.symbol} {self.qty} @ {price}")
        elif action == "sell" and self.state["position"] != "short":
            self.state["position"] = "short"
            print(f"{ts} PAPER SELL {self.symbol} {self.qty} @ {price}")
        else:
            print(f"{ts} PAPER HOLD {self.symbol} pos={self.state['position']} @ {price}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["backtest","optuna","paper"], required=True)
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--symbol", default="BTC/USDT")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--n1", type=int, default=10)
    ap.add_argument("--n2", type=int, default=30)
    args = ap.parse_args()

    if args.mode in ("backtest","optuna"):
        if not os.path.exists(args.data):
            print("Missing data file:", args.data); sys.exit(1)
        df = load_ohlcv(args.data)

    if args.mode == "backtest":
        bt, stats = run_backtest(df, n1=args.n1, n2=args.n2)
        print(stats)
        bt.plot(open_browser=False, filename="bt_plot.html")
        print("plot saved: bt_plot.html")
    elif args.mode == "optuna":
        study = optuna_search(args.data, trials=args.trials)
        print("Best params:", study.best_params, "Best value:", study.best_value)
        with open("optuna_study.json","w") as f: json.dump({"best":study.best_params}, f)
    elif args.mode == "paper":
        ex = ccxt.binance({
            "apiKey": os.environ.get("BINANCE_API_KEY", ""),
            "secret": os.environ.get("BINANCE_SECRET", ""),
            "enableRateLimit": True,
        })
        if os.environ.get("BINANCE_TESTNET") == "1":
            ex.urls['api'] = ex.urls.get('test', ex.urls['api'])
        df_live = pd.DataFrame(ex.fetch_ohlcv(args.symbol, timeframe='1h', limit=200),
                               columns=['ts','Open','High','Low','Close','Volume'])
        df_live['ts'] = pd.to_datetime(df_live['ts'], unit='ms')
        df_live.set_index('ts', inplace=True)
        execer = PaperExecutor(ex, args.symbol)
        for i in range(args.limit):
            execer.paper_step(df_live, n1=args.n1, n2=args.n2)
            time.sleep(5)

if __name__ == "__main__":
    main()

