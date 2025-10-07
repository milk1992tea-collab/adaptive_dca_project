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

# === 抓取 Binance K 線資料 ===
def get_binance_klines(symbol, interval="1h", limit=500):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = requests.get(url, params=params).json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","num_trades","taker_base","taker_quote","ignore"
    ])
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df[["open","high","low","close","volume"]]

# === 策略（RSI+MACD） ===
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
    storage = f"sqlite:///{base_dir}/optuna_study_quick_real.db"
    study = optuna.create_study(direction="maximize", storage=storage, study_name="quick_test_real", load_if_exists=True)

    # 測試用：只抓 3 個幣種
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    train_sets = []
    for sym in symbols:
        try:
            df = get_binance_klines(sym, interval="1h", limit=500)
            train_sets.append(df)
            print(f"✅ 已抓取 {sym} K線資料，共 {len(df)} 根")
        except Exception as e:
            print(f"⚠️ {sym} 抓取失敗: {e}")

    # 測試用：只跑 5 trials
    study.optimize(lambda trial: objective(trial, train_sets), n_trials=5)

    print("\n🔥 測試完成，最佳參數：", study.best_params)