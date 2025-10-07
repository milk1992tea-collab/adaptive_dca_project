import os
import requests
import pandas as pd
import time
import optuna
from datetime import datetime
import matplotlib.pyplot as plt
import platform

# 🔑 自動偵測系統字型（確保中文正常顯示）
system = platform.system()
if system == "Windows":
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 微軟正黑體
elif system == "Darwin":  # macOS
    plt.rcParams['font.sans-serif'] = ['PingFang TC', 'Heiti TC', 'Arial Unicode MS']
else:  # Linux
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'WenQuanYi Micro Hei', 'SimHei']

plt.rcParams['axes.unicode_minus'] = False  # 避免負號顯示錯誤

# ========== 抓取成交額前N幣種 ==========
def get_top_volume_symbols(limit=10):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "volume_desc", "per_page": limit, "page": 1}
    resp = requests.get(url, params=params)
    data = resp.json()
    symbols = [coin["symbol"].upper() + "USDT" for coin in data]
    return symbols

# ========== 抓取歷史K線 ==========
def get_binance_klines(symbol, interval="1h", start="2022-01-01", end="2025-08-31", base_dir="D:/crypto_data"):
    url = "https://api.binance.com/api/v3/klines"
    folder = os.path.join(base_dir, symbol)
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{symbol}_{interval}_{start}_to_{end}.csv")

    start_ts = int(pd.Timestamp(start).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end).timestamp() * 1000)
    all_data = []
    limit = 1000

    while True:
        params = {"symbol": symbol, "interval": interval, "startTime": start_ts, "endTime": end_ts, "limit": limit}
        resp = requests.get(url, params=params)
        data = resp.json()
        if not data:
            break
        all_data.extend(data)
        last_time = data[-1][0]
        start_ts = last_time + 1
        time.sleep(0.5)
        if start_ts > end_ts:
            break

    df = pd.DataFrame(all_data, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","quote_asset_volume","trades","taker_base_vol","taker_quote_vol","ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    df.to_csv(filename, index=False)
    return df

# ========== 分割訓練/測試 ==========
def split_train_test(df, split_date="2025-01-01"):
    train = df[df["timestamp"] < split_date]
    test = df[df["timestamp"] >= split_date]
    return train, test

# ========== 策略模擬器（含交易費用） ==========
def backtest(df, buy_threshold, sell_threshold, position_size, fee_rate=0.001):
    """
    fee_rate: 交易費用比例 (例如 0.001 = 0.1%)
    """
    capital = 10000
    for i in range(1, len(df)):
        change = (df["close"].iloc[i] - df["close"].iloc[i-1]) / df["close"].iloc[i-1]
        if change > buy_threshold:
            capital *= (1 + position_size * change)
            capital *= (1 - fee_rate)  # 扣除手續費
        elif change < -sell_threshold:
            capital *= (1 - position_size * abs(change))
            capital *= (1 - fee_rate)  # 扣除手續費
    return capital

# ========== Optuna 目標函數（跨幣種） ==========
def objective(trial, train_sets):
    buy_threshold = trial.suggest_float("buy_threshold", 0.001, 0.05)
    sell_threshold = trial.suggest_float("sell_threshold", 0.001, 0.05)
    position_size = trial.suggest_float("position_size", 0.001, 0.01)

    results = []
    for df in train_sets:
        final_capital = backtest(df, buy_threshold, sell_threshold, position_size, fee_rate=0.001)
        results.append(final_capital)
    return sum(results) / len(results)  # 平均績效

# ========== 合併歷史結果 + 繪圖 ==========
def merge_and_plot(base_dir="D:/crypto_data"):
    all_files = [f for f in os.listdir(base_dir) if f.startswith("optuna_results_") and f.endswith(".csv") and "all" not in f]
    if not all_files:
        print("⚠️ 沒有找到歷史結果檔")
        return
    dfs = []
    for f in all_files:
        df = pd.read_csv(os.path.join(base_dir, f))
        df["run_file"] = f
        dfs.append(df)
    merged = pd.concat(dfs, ignore_index=True)
    merged_file = os.path.join(base_dir, "optuna_results_all.csv")
    merged.to_csv(merged_file, index=False)
    print(f"📑 已合併 {len(all_files)} 個結果檔 → {merged_file}")

    # 計算每次 run 的平均績效
    avg_results = merged.groupby("run_file")["final_capital"].mean().reset_index()

    # 繪製折線圖
    plt.figure(figsize=(10,6))
    plt.plot(avg_results["run_file"], avg_results["final_capital"], marker="o", linestyle="-", color="blue")
    plt.xticks(rotation=45, ha="right")
    plt.title("跨幣種策略績效隨時間變化")
    plt.xlabel("執行批次 (時間戳)")
    plt.ylabel("平均最終資產")
    plt.tight_layout()
    chart_file = os.path.join(base_dir, "optuna_performance_curve.png")
    plt.savefig(chart_file)
    print(f"📈 績效曲線已生成: {chart_file}")

# ========== 主程式 ==========
if __name__ == "__main__":
    base_dir = "D:/crypto_data"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    result_file = os.path.join(base_dir, f"optuna_results_{timestamp}.csv")

    # 🔑 如果今天已經有結果檔，就直接跳過回測
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    existing_files = [f for f in os.listdir(base_dir) if f.startswith(f"optuna_results_{today_prefix}")]
    if existing_files:
        print(f"⚡ 偵測到今天已有回測結果 → {existing_files[-1]}，跳過重新回測")
        merge_and_plot(base_dir)
        exit(0)

    symbols = get_top_volume_symbols(limit=10)  # 測試先跑前10個
    train_sets, test_sets = [], {}

    for sym in symbols:
        try:
            df = get_binance_klines(sym)
            train_df, test_df = split_train_test(df)
            train_sets.append(train_df)
            test_sets[sym] = test_df
        except Exception as e:
            print(f"⚠️ {sym} 抓取失敗: {e}")

    # Optuna 優化（跨幣種）
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, train_sets), n_trials=30)

    best_params = study.best_params
    print(f"\n🔥 跨幣種最佳參數: {best_params}")

    # 測試集驗證 + 紀錄結果
    results = []
    for sym, test_df in test_sets.items():
        final_capital = backtest(test_df, best_params["buy_threshold"], best_params["sell_threshold"], best_params["position_size"], fee_rate=0.001)
        print(f"📊 {sym} 測試集結果: 最終資產={final_capital:.2f}")
        results.append({"symbol": sym, "final_capital": final_capital})

    # 存到 CSV（帶時間戳）
    df_results = pd.DataFrame(results)
    df_results["buy_threshold"] = best_params["buy_threshold"]
    df_results["sell_threshold"] = best_params["sell_threshold"]
    df_results["position_size"] = best_params["position_size"]
    df_results["fee_rate"] = 0.
    import os
import requests
import pandas as pd
import time
import optuna
from datetime import datetime
import matplotlib.pyplot as plt
import platform

# 🔑 自動偵測系統字型（確保中文正常顯示）
system = platform.system()
if system == "Windows":
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 微軟正黑體
elif system == "Darwin":  # macOS
    plt.rcParams['font.sans-serif'] = ['PingFang TC', 'Heiti TC', 'Arial Unicode MS']
else:  # Linux
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'WenQuanYi Micro Hei', 'SimHei']

plt.rcParams['axes.unicode_minus'] = False  # 避免負號顯示錯誤

# ========== 抓取成交額前N幣種 ==========
def get_top_volume_symbols(limit=10):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "volume_desc", "per_page": limit, "page": 1}
    resp = requests.get(url, params=params)
    data = resp.json()
    symbols = [coin["symbol"].upper() + "USDT" for coin in data]
    return symbols

# ========== 抓取歷史K線 ==========
def get_binance_klines(symbol, interval="1h", start="2022-01-01", end="2025-08-31", base_dir="D:/crypto_data"):
    url = "https://api.binance.com/api/v3/klines"
    folder = os.path.join(base_dir, symbol)
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{symbol}_{interval}_{start}_to_{end}.csv")

    start_ts = int(pd.Timestamp(start).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end).timestamp() * 1000)
    all_data = []
    limit = 1000

    while True:
        params = {"symbol": symbol, "interval": interval, "startTime": start_ts, "endTime": end_ts, "limit": limit}
        resp = requests.get(url, params=params)
        data = resp.json()
        if not data:
            break
        all_data.extend(data)
        last_time = data[-1][0]
        start_ts = last_time + 1
        time.sleep(0.5)
        if start_ts > end_ts:
            break

    df = pd.DataFrame(all_data, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","quote_asset_volume","trades","taker_base_vol","taker_quote_vol","ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    df.to_csv(filename, index=False)
    return df

# ========== 分割訓練/測試 ==========
def split_train_test(df, split_date="2025-01-01"):
    train = df[df["timestamp"] < split_date]
    test = df[df["timestamp"] >= split_date]
    return train, test

# ========== 策略模擬器（含交易費用） ==========
def backtest(df, buy_threshold, sell_threshold, position_size, fee_rate=0.001):
    """
    fee_rate: 交易費用比例 (例如 0.001 = 0.1%)
    """
    capital = 10000
    for i in range(1, len(df)):
        change = (df["close"].iloc[i] - df["close"].iloc[i-1]) / df["close"].iloc[i-1]
        if change > buy_threshold:
            capital *= (1 + position_size * change)
            capital *= (1 - fee_rate)  # 扣除手續費
        elif change < -sell_threshold:
            capital *= (1 - position_size * abs(change))
            capital *= (1 - fee_rate)  # 扣除手續費
    return capital

# ========== Optuna 目標函數（跨幣種） ==========
def objective(trial, train_sets):
    buy_threshold = trial.suggest_float("buy_threshold", 0.001, 0.05)
    sell_threshold = trial.suggest_float("sell_threshold", 0.001, 0.05)
    position_size = trial.suggest_float("position_size", 0.001, 0.01)

    results = []
    for df in train_sets:
        final_capital = backtest(df, buy_threshold, sell_threshold, position_size, fee_rate=0.001)
        results.append(final_capital)
    return sum(results) / len(results)  # 平均績效

# ========== 合併歷史結果 + 繪圖 ==========
def merge_and_plot(base_dir="D:/crypto_data"):
    all_files = [f for f in os.listdir(base_dir) if f.startswith("optuna_results_") and f.endswith(".csv") and "all" not in f]
    if not all_files:
        print("⚠️ 沒有找到歷史結果檔")
        return
    dfs = []
    for f in all_files:
        df = pd.read_csv(os.path.join(base_dir, f))
        df["run_file"] = f
        dfs.append(df)
    merged = pd.concat(dfs, ignore_index=True)
    merged_file = os.path.join(base_dir, "optuna_results_all.csv")
    merged.to_csv(merged_file, index=False)
    print(f"📑 已合併 {len(all_files)} 個結果檔 → {merged_file}")

    # 計算每次 run 的平均績效
    avg_results = merged.groupby("run_file")["final_capital"].mean().reset_index()

    # 繪製折線圖
    plt.figure(figsize=(10,6))
    plt.plot(avg_results["run_file"], avg_results["final_capital"], marker="o", linestyle="-", color="blue")
    plt.xticks(rotation=45, ha="right")
    plt.title("跨幣種策略績效隨時間變化")
    plt.xlabel("執行批次 (時間戳)")
    plt.ylabel("平均最終資產")
    plt.tight_layout()
    chart_file = os.path.join(base_dir, "optuna_performance_curve.png")
    plt.savefig(chart_file)
    print(f"📈 績效曲線已生成: {chart_file}")

# ========== 主程式 ==========
if __name__ == "__main__":
    base_dir = "D:/crypto_data"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    result_file = os.path.join(base_dir, f"optuna_results_{timestamp}.csv")

    # 🔑 如果今天已經有結果檔，就直接跳過回測
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    existing_files = [f for f in os.listdir(base_dir) if f.startswith(f"optuna_results_{today_prefix}")]
    if existing_files:
        print(f"⚡ 偵測到今天已有回測結果 → {existing_files[-1]}，跳過重新回測")
        merge_and_plot(base_dir)
        exit(0)

    symbols = get_top_volume_symbols(limit=10)  # 測試先跑前10個
    train_sets, test_sets = [], {}

    for sym in symbols:
        try:
            df = get_binance_klines(sym)
            train_df, test_df = split_train_test(df)
            train_sets.append(train_df)
            test_sets[sym] = test_df
        except Exception as e:
            print(f"⚠️ {sym} 抓取失敗: {e}")

    # Optuna 優化（跨幣種）
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, train_sets), n_trials=30)

    best_params = study.best_params
    print(f"\n🔥 跨幣種最佳參數: {best_params}")

    # 測試集驗證 + 紀錄結果
    results = []
    for sym, test_df in test_sets.items():
        final_capital = backtest(
            test_df,
            best_params["buy_threshold"],
            best_params["sell_threshold"],
            best_params["position_size"],
            fee_rate=0.001
        )
        print(f"📊 {sym} 測試集結果: 最終資產={final_capital:.2f}")
        results.append({"symbol": sym, "final_capital": final_capital})

    # 存到 CSV（帶時間戳）
    df_results = pd.DataFrame(results)
    df_results["buy_threshold"] = best_params["buy_threshold"]
    df_results["sell_threshold"] = best_params["sell_threshold"]
    df_results["position_size"] = best
        # 存到 CSV（帶時間戳）
    df_results = pd.DataFrame(results)
    df_results["buy_threshold"] = best_params["buy_threshold"]
    df_results["sell_threshold"] = best_params["sell_threshold"]
    df_results["position_size"] = best_params["position_size"]
    df_results["fee_rate"] = 0.001  # 記錄交易費用
    df_results.to_csv(result_file, index=False)
    print(f"\n✅ 結果已存檔: {result_file}")

    # 合併所有歷史結果 + 繪圖
    merge_and_plot(base_dir)