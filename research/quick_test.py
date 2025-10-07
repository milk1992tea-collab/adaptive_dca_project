import os
import requests
import optuna
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

# === 基本設定 ===
base_dir = "D:/crypto_data"
os.makedirs(os.path.join(base_dir, "klines"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "plots"), exist_ok=True)

# === 抓取前 N 個成交量最高的幣種 ===
def get_top_volume_symbols(limit=3, quote="USDT"):  # 減少到 3 個幣種
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url).json()
    usdt_pairs = [d for d in data if d["symbol"].endswith(quote)]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)
    return [d["symbol"] for d in sorted_pairs[:limit]]

# === 簡化策略（只示範 RSI+MACD） ===
def run_strategy_combo(df, params):
    close = df["close"]
    df["rsi"] = ta.rsi(close, length=params.get("rsi_period", 14))
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    df["macd"] = macd_df["MACD_12_26_9"]
    df["macdsignal"] = macd_df["MACDs_12_26_9"]

    buy = (df["rsi"] < params["rsi_buy"]) & (df["macd"] > df["macdsignal"])
    sell = (df["rsi"] > params["rsi_sell"]) & (df["macd"] < df["macdsignal"])

    position = 0
    capital = 1000
    for i in range(len(df)):
        if buy.iloc[i] and position == 0:
            position = capital / df["close"].iloc[i]
            capital = 0
        elif sell.iloc[i] and position > 0:
            capital = position * df["close"].iloc[i]
            position = 0
    if position > 0:
        capital = position * df["close"].iloc[-1]

    return capital

# === Optuna 目標函數 ===
def objective(trial, train_sets):
    params = {
        "rsi_period": trial.suggest_int("rsi_period", 7, 21),
        "rsi_buy": trial.suggest_int("rsi_buy", 20, 40),
        "rsi_sell": trial.suggest_int("rsi_sell", 60, 80),
    }
    total_capital = 0
    for df in train_sets:
        total_capital += run_strategy_combo(df, params)
    return total_capital / len(train_sets)

# === 主程式 ===
if __name__ == "__main__":
    storage = f"sqlite:///{base_dir}/optuna_study_test.db"
    study = optuna.create_study(direction="maximize", storage=storage, study_name="quick_test", load_if_exists=True)

    # 測試用：只抓 3 個幣種
    symbols = get_top_volume_symbols(limit=3)
    train_sets = []
    for sym in symbols:
        # 這裡用隨機數據模擬，避免依賴真實 API
        df = pd.DataFrame({
            "close": np.linspace(100, 200, 100) + np.random.randn(100)*5,
            "high": np.linspace(101, 201, 100) + np.random.randn(100)*5,
            "low": np.linspace(99, 199, 100) + np.random.randn(100)*5,
        })
        train_sets.append(df)

    # 測試用：只跑 5 trials
    study.optimize(lambda trial: objective(trial, train_sets), n_trials=5)

    print("\n🔥 測試完成，最佳參數：", study.best_params)