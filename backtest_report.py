import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data_fetch import fetch_multi_timeframes
from signal_generator import generate_signal
from strategies import run_strategy

BEST_PATH = "best_params.json"

def load_strategies():
    with open(BEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("strategies", {})

def backtest_equity(symbol, strategy_name, params, dfs):
    df_1m = dfs["1m"]
    balance = 10000
    position = 0
    entry_price = None
    equity_curve = []

    step = params.get("step", 5.0)
    base_qty = params.get("base_qty", 5.0)
    tp_pct = params.get("take_profit_pct", 0.05)
    sl_pct = params.get("stop_loss_pct", -0.03)

    for i in range(len(df_1m)):
        price = df_1m["close"].iloc[i]
        dfs_slice = {
            "1m": df_1m.iloc[:i+1],
            "15m": dfs["15m"].iloc[:i//15+1],
            "1h": dfs["1h"].iloc[:i//60+1],
            "4h": dfs["4h"].iloc[:i//240+1],
            "1d": dfs["1d"].iloc[:i//1440+1],
        }
        sigs = generate_signal(dfs_slice)
        decision = run_strategy(strategy_name, sigs)

        if decision == 1 and position == 0:
            position = balance / price
            entry_price = price
            balance = 0
        elif decision == -1 and position > 0:
            balance = position * price
            position, entry_price = 0, None

        if entry_price and position > 0:
            pnl_pct = (price - entry_price) / entry_price
            if pnl_pct >= tp_pct or pnl_pct <= sl_pct:
                balance = position * price
                position, entry_price = 0, None

        equity = balance + (position * price if position > 0 else 0)
        equity_curve.append(equity)

    return pd.Series(equity_curve, index=df_1m.index)

def plot_report(equity_curves):
    plt.figure(figsize=(12,6))
    for name, curve in equity_curves.items():
        plt.plot(curve.index, curve.values, label=name)
    plt.title("策略收益曲線比較")
    plt.xlabel("時間")
    plt.ylabel("資產淨值 (USDT)")
    plt.legend()
    plt.grid(True)
    plt.savefig("equity_report.png")
    plt.close()

    # Drawdown
    plt.figure(figsize=(12,6))
    for name, curve in equity_curves.items():
        peak = curve.cummax()
        drawdown = (curve - peak) / peak
        plt.plot(curve.index, drawdown.values, label=name)
    plt.title("策略最大回撤比較")
    plt.xlabel("時間")
    plt.ylabel("回撤比例")
    plt.legend()
    plt.grid(True)
    plt.savefig("drawdown_report.png")
    plt.close()

if __name__ == "__main__":
    symbol = "BTCUSDT"
    dfs = fetch_multi_timeframes(symbol, limit=1000)
    strategies = load_strategies()

    equity_curves = {}
    for name, cfg in strategies.items():
        params = cfg["params"]
        curve = backtest_equity(symbol, name, params, dfs)
        equity_curves[name] = curve

    plot_report(equity_curves)
    print("\n=== 回測報告已生成 ===")
    print("equity_report.png → 收益曲線")
    print("drawdown_report.png → 回撤曲線")