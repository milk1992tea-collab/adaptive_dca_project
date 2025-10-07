import os
import itertools
import optuna
import pandas as pd
from datetime import datetime

# === 1. 定義週期與策略 ===
timeframes = ["15m", "1h", "4h", "1d"]
strategies = ["RSI", "MACD", "BBANDS", "SKDJ", "TD9", "TD13", "DCA"]

# 自動生成所有兩兩組合
strategy_combos = ["+".join(c) for c in itertools.combinations(strategies, 2)]

# === 2. 模擬抓資料函數 (你要替換成實際 fetch_data) ===
def fetch_data(symbol, timeframe="1h", limit=500):
    # TODO: 這裡換成你的資料下載邏輯
    # 回傳 DataFrame，至少要有 close 價
    import numpy as np
    import pandas as pd
    data = pd.DataFrame({
        "close": np.random.normal(100, 5, limit)  # 假資料
    })
    return data

# === 3. 策略模擬 (簡化版，實際要換成你的策略邏輯) ===
def run_strategy(df, strategy_combo, params):
    # TODO: 這裡放 RSI、MACD、TD9 等實際計算
    # 目前先隨機模擬績效
    import random
    return 1000 + random.uniform(-100, 200)

# === 4. Optuna 目標函數 ===
def objective(trial, timeframe):
    strategy_combo = trial.suggest_categorical("strategy_combo", strategy_combos)
    rsi_period = trial.suggest_int("rsi_period", 7, 21)
    rsi_buy = trial.suggest_int("rsi_buy", 20, 40)
    rsi_sell = trial.suggest_int("rsi_sell", 60, 80)
    dca_interval = trial.suggest_int("dca_interval", 5, 30)

    # 抓資料 (示範用 BTCUSDT)
    df = fetch_data("BTCUSDT", timeframe=timeframe, limit=500)
    final_capital = run_strategy(df, strategy_combo, {
        "rsi_period": rsi_period,
        "rsi_buy": rsi_buy,
        "rsi_sell": rsi_sell,
        "dca_interval": dca_interval
    })
    return final_capital

# === 5. 主程式 ===
results = []
for tf in timeframes:
    study_name = f"multi_strategy_{tf}"
    study = optuna.create_study(
        study_name=study_name,
        direction="maximize",
        storage="sqlite:///D:/crypto_data/optuna_study.db",
        load_if_exists=True
    )
    study.optimize(lambda trial: objective(trial, tf), n_trials=50)  # 先跑50次測試

    best_params = study.best_params
    best_value = study.best_value

    results.append({
        "timeframe": tf,
        "best_strategy": best_params["strategy_combo"],
        "rsi_period": best_params["rsi_period"],
        "rsi_buy": best_params["rsi_buy"],
        "rsi_sell": best_params["rsi_sell"],
        "dca_interval": best_params["dca_interval"],
        "final_capital": best_value
    })

# === 6. 輸出結果 ===
df_results = pd.DataFrame(results)
out_path = f"D:/crypto_data/results/multi_timeframe_results_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
df_results.to_csv(out_path, index=False, encoding="utf-8-sig")

print("✅ 多週期最佳策略表已輸出:", out_path)
print(df_results)