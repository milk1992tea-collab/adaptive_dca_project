import ccxt
import pandas as pd
import pandas_ta as ta
import optuna
import itertools
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# === 1. 幣種與週期 ===
symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
timeframes = ["15m", "1h", "4h", "1d"]
strategies = ["RSI", "MACD", "BBANDS", "TD9"]

strategy_combos = ["+".join(c) for c in itertools.combinations(strategies, 2)]

# === 2. 抓取幣安歷史資料 ===
def fetch_data(symbol="BTC/USDT", timeframe="1h", limit=500):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# === 3. 技術指標計算 ===
def add_indicators(df, rsi_period=14):
    df["rsi"] = ta.rsi(df["close"], length=rsi_period)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd["MACD_12_26_9"], macd["MACDs_12_26_9"], macd["MACDh_12_26_9"]

    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None and not bb.empty:
        df["bb_lower"]  = bb.iloc[:,0]
        df["bb_middle"] = bb.iloc[:,1]
        df["bb_upper"]  = bb.iloc[:,2]

    df["td9_buy"] = (df["close"] < df["close"].shift(1)).rolling(9).sum() == 9
    df["td9_sell"] = (df["close"] > df["close"].shift(1)).rolling(9).sum() == 9
    return df

# === 4. 策略模擬 + 績效指標 ===
def run_strategy(df, strategy_combo, params):
    df = add_indicators(df, rsi_period=params["rsi_period"])
    capital = 1000
    position = 0
    trades = []
    equity_curve = []
    entry_time = None
    holding_times = []

    max_holding_hours = params.get("max_holding_hours", 1e9)

    for i in range(len(df)):
        row = df.iloc[i]
        signal = None

        if "RSI" in strategy_combo and not pd.isna(row["rsi"]):
            if row["rsi"] < params["rsi_buy"]:
                signal = "buy"
            elif row["rsi"] > params["rsi_sell"]:
                signal = "sell"

        if "MACD" in strategy_combo and not pd.isna(row["macd"]):
            if row["macd"] > row["macd_signal"]:
                signal = "buy"
            elif row["macd"] < row["macd_signal"]:
                signal = "sell"

        if "TD9" in strategy_combo:
            if row["td9_buy"]:
                signal = "buy"
            elif row["td9_sell"]:
                signal = "sell"

        if "BBANDS" in strategy_combo and "bb_lower" in df.columns and "bb_upper" in df.columns:
            if row["close"] < row["bb_lower"]:
                signal = "buy"
            elif row["close"] > row["bb_upper"]:
                signal = "sell"

        # === 強制平倉檢查 ===
        if position > 0 and entry_time is not None:
            holding_hours = (row["timestamp"] - entry_time).total_seconds() / 3600
            if holding_hours >= max_holding_hours:
                capital = position * row["close"]
                trades.append((entry_price, row["close"]))
                holding_times.append(holding_hours)
                position = 0
                entry_time = None

        if signal == "buy" and capital > 0:
            position = capital / row["close"]
            entry_price = row["close"]
            entry_time = row["timestamp"]
            capital = 0

        elif signal == "sell" and position > 0:
            capital = position * row["close"]
            trades.append((entry_price, row["close"]))
            if entry_time is not None:
                holding_times.append((row["timestamp"] - entry_time).total_seconds()/3600)
            position = 0
            entry_time = None

        equity_curve.append(capital + position * row["close"])

    if position > 0:
        capital = position * df.iloc[-1]["close"]

    final_capital = capital
    equity_curve = np.array(equity_curve)

    returns = np.diff(equity_curve) / equity_curve[:-1] if len(equity_curve) > 1 else np.array([0])
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    max_dd = np.max(np.maximum.accumulate(equity_curve) - equity_curve)
    max_dd_pct = max_dd / np.max(np.maximum.accumulate(equity_curve)) if len(equity_curve) > 0 else 0
    win_rate = sum(1 for e, x in trades if x > e) / len(trades) if trades else 0

    profits = [x-e for e,x in trades if x>e]
    losses  = [e-x for e,x in trades if x<e]
    profit_factor = (sum(profits) / abs(sum(losses))) if losses else float('inf')

    avg_holding_time = np.mean(holding_times) if holding_times else 0

    return {
        "final_capital": final_capital,
        "return_pct": final_capital / 1000 - 1,
        "sharpe": sharpe,
        "max_drawdown_pct": max_dd_pct,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_holding_time_h": avg_holding_time
    }

# === 5. Optuna 目標函數 (多目標) ===
def objective(trial, timeframe, symbols):
    strategy_combo = trial.suggest_categorical("strategy_combo", strategy_combos)
    rsi_period = trial.suggest_int("rsi_period", 7, 21)
    rsi_buy = trial.suggest_int("rsi_buy", 20, 40)
    rsi_sell = trial.suggest_int("rsi_sell", 60, 80)
    dca_interval = trial.suggest_int("dca_interval", 5, 30)

    total_metrics = {"final_capital":0,"return_pct":0,"sharpe":0,"max_drawdown_pct":0,"win_rate":0,"profit_factor":0,"avg_holding_time_h":0}
    for sym in symbols:
        df = fetch_data(sym, timeframe=timeframe, limit=500)
        metrics = run_strategy(df, strategy_combo, {
            "rsi_period": rsi_period,
            "rsi_buy": rsi_buy,
            "rsi_sell": rsi_sell,
            "dca_interval": dca_interval,
            "max_holding_hours": 24   # ✅ 強制平倉時間
        })
        for k in total_metrics:
            total_metrics[k] += metrics[k]

    avg_metrics = {k: v/len(symbols) for k,v in total_metrics.items()}

    return (
        avg_metrics["final_capital"],
        avg_metrics["profit_factor"],
        -avg_metrics["avg_holding_time_h"]
    )

# === 6. 主程式 ===
results = []
for tf in timeframes:
    study_name = f"multi_strategy_multiobj_{tf}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    study = optuna.create_study(
        study_name=study_name,
        directions=["maximize", "maximize", "minimize"],
        storage="sqlite:///D:/crypto_data/optuna_study.db",
        load_if_exists=False
    )
    study.optimize(lambda trial: objective(trial, tf, symbols), n_trials=30)

    pareto_trials = study.best_trials
    for t in pareto_trials:
        results.append({
            "timeframe": tf,
                        "strategy_combo": t.params["strategy_combo"],
            "rsi_period": t.params["rsi_period"],
            "rsi_buy": t.params["rsi_buy"],
            "rsi_sell": t.params["rsi_sell"],
            "dca_interval": t.params["dca_interval"],
            "final_capital": t.values[0],
            "profit_factor": t.values[1],
            "avg_holding_time_h": -t.values[2]  # 還原正值
        })

# === 7. 輸出結果 ===
df_results = pd.DataFrame(results)
out_path = f"D:/crypto_data/results/multi_asset_multi_timeframe_results_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
df_results.to_csv(out_path, index=False, encoding="utf-8-sig")

print("✅ 多幣種 × 多週期最佳策略表已輸出:", out_path)
print(df_results)

# === 8. 畫圖 ===
plt.figure(figsize=(8,5))
plt.bar(df_results["timeframe"], df_results["final_capital"], color="skyblue")
plt.title("不同週期最佳策略績效比較 (多幣種平均, 強制平倉版)")
plt.xlabel("Timeframe")
plt.ylabel("Final Capital")

for i, v in enumerate(df_results["final_capital"]):
    plt.text(i, v+5, f"{v:.1f}", ha="center", fontsize=9)

plot_path = "D:/crypto_data/plots/multi_asset_multi_timeframe_performance.png"
os.makedirs(os.path.dirname(plot_path), exist_ok=True)
plt.savefig(plot_path, dpi=150)
plt.close()

print("📊 圖表已輸出:", plot_path)


# === 9. 自動清理舊 study 工具 ===
def cleanup_old_studies(storage_url="sqlite:///D:/crypto_data/optuna_study.db", keep_recent=5, core_studies=None):
    """
    自動清理舊的探索 study，只保留核心 study + 最近 N 個。
    """
    if core_studies is None:
        core_studies = ["core_strategy_1h"]  # 你想長期保留的核心 study 名稱

    storage = optuna.storages.RDBStorage(url=storage_url)
    # ✅ 改用全域 API
    all_studies = optuna.get_all_study_summaries(storage=storage)

    # 排序：依建立時間由新到舊
    all_studies_sorted = sorted(all_studies, key=lambda s: s.datetime_start or datetime.min, reverse=True)

    # 保留核心 + 最近 N 個
    keep_names = set(core_studies)
    keep_names.update([s.study_name for s in all_studies_sorted[:keep_recent]])

    # 刪除其餘
    for s in all_studies_sorted:
        if s.study_name not in keep_names:
            print(f"🗑️ 刪除舊 study: {s.study_name}")
            storage.delete_study(study_id=s._study_id)


# ✅ 執行清理：保留核心 + 最近 5 個探索 study
cleanup_old_studies(keep_recent=5, core_studies=["core_strategy_1h"])