import sys, os
# CI debug marker — will show in workflow logs and in output HTML
print("SCRIPT_DEBUG:BEGIN")
print("SCRIPT_PATH:", __file__)
print("PYARGS:", sys.argv)
print("CWD:", os.getcwd())
print("ENV_COMMIT:", os.environ.get("COMMIT"))
print("SCRIPT_DEBUG:END")
# run_backtest.py - simple SMA crossover backtest -> writes bt_plot.html
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Configuration
DATA_PATH = Path("data/ohlc.csv")
OUT_HTML = Path("bt_plot.html")
SHORT = 20
LONG = 50
INITIAL_CASH = 10000

def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    return df

def run_sma_backtest(df: pd.DataFrame):
    df["sma_short"] = df["close"].rolling(SHORT).mean()
    df["sma_long"] = df["close"].rolling(LONG).mean()
    df = df.dropna().copy()
    df["position"] = 0
    df.loc[df["sma_short"] > df["sma_long"], "position"] = 1
    df.loc[df["sma_short"] <= df["sma_long"], "position"] = 0
    df["signal"] = df["position"].diff().fillna(0)
    cash = INITIAL_CASH
    shares = 0.0
    equity = []
    for idx, row in df.iterrows():
        price = row["close"]
        if row["signal"] == 1 and cash > 0:
            shares = cash / price
            cash = 0.0
        elif row["signal"] == -1 and shares > 0:
            cash = shares * price
            shares = 0.0
        total = cash + shares * price
        equity.append(total)
    df["equity"] = equity
    return df

def plot_and_write(df: pd.DataFrame, out: Path):
    plt.style.use("ggplot")
    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(df.index, df["close"], label="Close", color="black", linewidth=1)
    ax.plot(df.index, df["sma_short"], label=f"SMA{SHORT}", linewidth=1)
    ax.plot(df.index, df["sma_long"], label=f"SMA{LONG}", linewidth=1)
    ax.set_title("Backtest: SMA Crossover")
    ax.legend(loc="best")
    ax2 = fig.add_axes([0.1, 0.1, 0.8, 0.25])
    ax2.plot(df.index, df["equity"], label="Equity", color="tab:blue", linewidth=1)
    ax2.set_ylabel("Equity")
    png_path = out.with_suffix(".png")
    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)
    html = f"""<html><body><h1>Backtest result</h1><img src="{png_path.name}" alt="plot" /></body></html>"""
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")

def main():
    try:
        df = load_data(DATA_PATH)
    except Exception as e:
        print(f"ERROR loading data: {e}", file=sys.stderr)
        sys.exit(2)
    df_bt = run_sma_backtest(df)
    plot_and_write(df_bt, OUT_HTML)

if __name__ == "__main__":
    main()

