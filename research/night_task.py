import os
import requests
import optuna
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# === 基本設定 ===
base_dir = "D:/crypto_data"
os.makedirs(os.path.join(base_dir, "klines"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "plots"), exist_ok=True)

# === 參數與保護 ===
MIN_BARS = 50          # 少於此根數的資料直接跳過，避免指標不穩/NaN過多
INITIAL_CAPITAL = 1000 # 初始資金
INTERVAL = "1h"        # K線週期
LIMIT = 500            # 每幣種抓取 K 線根數

# === 抓取 Binance K 線資料 ===
def get_binance_klines(symbol, interval=INTERVAL, limit=LIMIT, base_dir=None):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = requests.get(url, params=params, timeout=20).json()
    if isinstance(data, dict) and "code" in data:
        raise Exception(f"Binance API error: {data}")
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","num_trades","taker_base","taker_quote","ignore"
    ])
    # 型別轉換
    for col in ["open","high","low","close","volume"]:
        df[col] = df[col].astype(float)
    # 可選：存檔到本地
    if base_dir:
        path = os.path.join(base_dir, f"{symbol}_{interval}.csv")
        df.to_csv(path, index=False)
    return df[["open","high","low","close","volume"]]

# === 切分訓練/測試集 ===
def split_train_test(df, ratio=0.8):
    split_idx = int(len(df) * ratio)
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()

# === 抓取前 N 個成交量最高的幣種 ===
def get_top_volume_symbols(limit=50, quote="USDT"):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url, timeout=20).json()
    usdt_pairs = [d for d in data if isinstance(d, dict) and d.get("symbol","").endswith(quote)]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x.get("quoteVolume", 0.0)), reverse=True)
    return [d["symbol"] for d in sorted_pairs[:limit]]

# === 策略組合清單（15 種） ===
strategy_combos = [
    "RSI+MACD", "RSI+DCA", "RSI+BBANDS", "RSI+TD13", "RSI+SKDJ",
    "MACD+DCA", "MACD+BBANDS", "MACD+TD13", "MACD+SKDJ",
    "DCA+BBANDS", "DCA+TD13", "DCA+SKDJ",
    "BBANDS+TD13", "BBANDS+SKDJ",
    "TD13+SKDJ"
]

# === 指標欄位自動偵測工具 ===
def pick_col(prefix_list, columns):
    # 從 columns 中找到第一個包含任一 prefix 的欄位
    for p in prefix_list:
        for c in columns:
            if p in c:
                return c
    return None

# === 策略執行 ===
def run_strategy_combo(strategy_combo, df, params):
    # 防呆：資料不足直接回傳初始資金
    if df is None or len(df) < MIN_BARS:
        return INITIAL_CAPITAL

    df = df.copy()
    close = df["close"]

    # RSI
    try:
        df["rsi"] = ta.rsi(close, length=params.get("rsi_period", 14))
    except Exception:
        df["rsi"] = np.nan

    # MACD（欄位名因版本可能不同，動態抓）
    try:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            macd_col = pick_col(["MACD_"], macd_df.columns)       # MACD line
            macds_col = pick_col(["MACDs_"], macd_df.columns)     # signal line
            df["macd"] = macd_df[macd_col] if macd_col else np.nan
            df["macdsignal"] = macd_df[macds_col] if macds_col else np.nan
        else:
            df["macd"] = np.nan
            df["macdsignal"] = np.nan
    except Exception:
        df["macd"] = np.nan
        df["macdsignal"] = np.nan

    # BBANDS（欄位名動態抓）
    try:
        bbands = ta.bbands(close, length=20, std=2)
        if bbands is not None and not bbands.empty:
            upper_col = pick_col(["BBU_"], bbands.columns)
            lower_col = pick_col(["BBL_"], bbands.columns)
            df["upper"] = bbands[upper_col] if upper_col else np.nan
            df["lower"] = bbands[lower_col] if lower_col else np.nan
        else:
            df["upper"] = np.nan
            df["lower"] = np.nan
    except Exception:
        df["upper"] = np.nan
        df["lower"] = np.nan

    # TD13（簡化版，需最少資料才有意義）
    try:
        df["td_seq"] = (df["close"] > df["close"].shift(4)).astype(int).rolling(13, min_periods=1).sum()
    except Exception:
        df["td_seq"] = np.nan

    # DCA（固定間隔）
    try:
        interval = max(1, int(params.get("dca_interval", 10)))
        df["dca_signal"] = (np.arange(len(df)) % interval == 0)
    except Exception:
        df["dca_signal"] = False

    # SKDJ（用 KD 近似，欄位名動態抓）
    try:
        stoch = ta.stoch(df["high"], df["low"], df["close"])
        if stoch is not None and not stoch.empty:
            slowk_col = pick_col(["STOCHk"], stoch.columns)
            slowd_col = pick_col(["STOCHd"], stoch.columns)
            df["slowk"] = stoch[slowk_col] if slowk_col else np.nan
            df["slowd"] = stoch[slowd_col] if slowd_col else np.nan
        else:
            df["slowk"] = np.nan
            df["slowd"] = np.nan
    except Exception:
        df["slowk"] = np.nan
        df["slowd"] = np.nan

    # === 組合判斷（對 NaN 做保護） ===
    def nz(series):
        # True/False 條件用，將 NaN 當 False
        return series.fillna(False)

    def lt(a, v):  # a < v with NaN→False
        return (a < v).fillna(False)

    def gt(a, v):  # a > v with NaN→False
        return (a > v).fillna(False)

    if strategy_combo == "RSI+MACD":
        buy = nz(lt(df["rsi"], params["rsi_buy"]) & gt(df["macd"], df["macdsignal"]))
        sell = nz(gt(df["rsi"], params["rsi_sell"]) & lt(df["macd"], df["macdsignal"]))

    elif strategy_combo == "RSI+BBANDS":
        buy = nz(lt(df["rsi"], params["rsi_buy"]) & lt(df["close"], df["lower"]))
        sell = nz(gt(df["rsi"], params["rsi_sell"]) & gt(df["close"], df["upper"]))

    elif strategy_combo == "RSI+TD13":
        buy = nz(lt(df["rsi"], params["rsi_buy"]) & (df["td_seq"].fillna(0) >= 13))
        sell = nz(gt(df["rsi"], params["rsi_sell"]) & (df["td_seq"].fillna(0) <= 0))

    elif strategy_combo == "RSI+SKDJ":
        buy = nz(lt(df["rsi"], params["rsi_buy"]) & gt(df["slowk"], df["slowd"]))
        sell = nz(gt(df["rsi"], params["rsi_sell"]) & lt(df["slowk"], df["slowd"]))

    elif strategy_combo == "RSI+DCA":
        buy = nz(lt(df["rsi"], params["rsi_buy"]) & df["dca_signal"])
        sell = nz(gt(df["rsi"], params["rsi_sell"]) & df["dca_signal"])

    elif strategy_combo == "MACD+BBANDS":
        buy = nz(gt(df["macd"], df["macdsignal"]) & lt(df["close"], df["lower"]))
        sell = nz(lt(df["macd"], df["macdsignal"]) & gt(df["close"], df["upper"]))

    elif strategy_combo == "MACD+TD13":
        buy = nz(gt(df["macd"], df["macdsignal"]) & (df["td_seq"].fillna(0) >= 13))
        sell = nz(lt(df["macd"], df["macdsignal"]) & (df["td_seq"].fillna(0) <= 0))

    elif strategy_combo == "MACD+SKDJ":
        buy = nz(gt(df["macd"], df["macdsignal"]) & gt(df["slowk"], df["slowd"]))
        sell = nz(lt(df["macd"], df["macdsignal"]) & lt(df["slowk"], df["slowd"]))

    elif strategy_combo == "MACD+DCA":
        buy = nz(gt(df["macd"], df["macdsignal"]) & df["dca_signal"])
        sell = nz(lt(df["macd"], df["macdsignal"]) & df["dca_signal"])

    elif strategy_combo == "DCA+BBANDS":
        buy = nz(df["dca_signal"] & lt(df["close"], df["lower"]))
        sell = nz(df["dca_signal"] & gt(df["close"], df["upper"]))

    elif strategy_combo == "DCA+TD13":
        buy = nz(df["dca_signal"] & (df["td_seq"].fillna(0) >= 13))
        sell = nz(df["dca_signal"] & (df["td_seq"].fillna(0) <= 0))

    elif strategy_combo == "DCA+SKDJ":
        buy = nz(df["dca_signal"] & gt(df["slowk"], df["slowd"]))
        sell = nz(df["dca_signal"] & lt(df["slowk"], df["slowd"]))

    elif strategy_combo == "BBANDS+TD13":
        buy = nz(lt(df["close"], df["lower"]) & (df["td_seq"].fillna(0) >= 13))
        sell = nz(gt(df["close"], df["upper"]) & (df["td_seq"].fillna(0) <= 0))

    elif strategy_combo == "BBANDS+SKDJ":
        buy = nz(lt(df["close"], df["lower"]) & gt(df["slowk"], df["slowd"]))
        sell = nz(gt(df["close"], df["upper"]) & lt(df["slowk"], df["slowd"]))

    elif strategy_combo == "TD13+SKDJ":
        buy = nz((df["td_seq"].fillna(0) >= 13) & gt(df["slowk"], df["slowd"]))
        sell = nz((df["td_seq"].fillna(0) <= 0) & lt(df["slowk"], df["slowd"]))

    else:
        buy = sell = pd.Series(False, index=df.index)

    # === 簡單回測邏輯（單次全倉進出） ===
    position = 0.0
    capital = float(INITIAL_CAPITAL)
    for i in range(len(df)):
        price = df["close"].iloc[i]
        if price <= 0 or np.isnan(price):
            continue
        if buy.iloc[i] and position == 0.0:
            position = capital / price
            capital = 0.0
        elif sell.iloc[i] and position > 0.0:
            capital = position * price
            position = 0.0
    if position > 0.0:
        last_price = df["close"].iloc[-1]
        if last_price > 0 and not np.isnan(last_price):
            capital = position * last_price
            position = 0.0

    return float(capital)

# === Optuna 目標函數 ===
def objective(trial, train_sets):
    if not train_sets:
        return 0.0
    strategy_combo = trial.suggest_categorical("strategy_combo", strategy_combos)
    params = {
        "rsi_period": trial.suggest_int("rsi_period", 7, 21),
        "rsi_buy": trial.suggest_int("rsi_buy", 20, 40),
        "rsi_sell": trial.suggest_int("rsi_sell", 60, 80),
        "dca_interval": trial.suggest_int("dca_interval", 5, 30),
    }
    total_capital = 0.0
    valid_sets = 0
    for df in train_sets:
        if df is None or len(df) < MIN_BARS:
            continue
        total_capital += run_strategy_combo(strategy_combo, df, params)
        valid_sets += 1
    if valid_sets == 0:
        return 0.0
    return total_capital / valid_sets

# === 合併結果 + 繪圖 ===
def merge_and_plot(base_dir):
    results_dir = os.path.join(base_dir, "results")
    plot_dir = os.path.join(base_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    all_files = [f for f in os.listdir(results_dir) if f.startswith("optuna_results_") and f.endswith(".csv")]
    if not all_files:
        print("⚠️ 沒有找到結果檔案")
        return

    df_list = []
    for f in all_files:
        try:
            df = pd.read_csv(os.path.join(results_dir, f))
            df["run"] = f
            df_list.append(df)
        except Exception as e:
            print(f"⚠️ 無法讀取 {f}: {e}")

    if not df_list:
        print("⚠️ 沒有可用的結果資料")
        return

    merged = pd.concat(df_list, ignore_index=True)
    merged.to_csv(os.path.join(results_dir, "optuna_results_all.csv"), index=False)

    avg_capital = merged.groupby("run")["final_capital"].mean()
    plt.figure(figsize=(10, 5))
    avg_capital.plot(marker="o")
    plt.title("Optuna Performance Over Time")
    plt.xlabel("Run")
    plt.ylabel("Average Final Capital")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "optuna_performance_curve.png"))
    plt.close()
    print(f"✅ 已更新合併結果與績效圖 → {plot_dir}")

# === 主程式 ===
if __name__ == "__main__":
    storage = f"sqlite:///{base_dir}/optuna_study.db"
    study = optuna.create_study(
        direction="maximize",
        storage=storage,
        study_name="multi_strategy",
        load_if_exists=True
    )

    symbols = get_top_volume_symbols(limit=50)
    train_sets, test_sets = [], {}
    for sym in symbols:
        try:
            df = get_binance_klines(sym, interval=INTERVAL, limit=LIMIT, base_dir=os.path.join(base_dir, "klines"))
            if df is None or len(df) < MIN_BARS:
                print(f"⚠️ {sym} 資料過短（{len(df)}），跳過")
                continue
            train_df, test_df = split_train_test(df)
            train_sets.append(train_df)
            test_sets[sym] = test_df
            print(f"✅ 已抓取 {sym}，資料長度 {len(df)}")
        except Exception as e:
            print(f"⚠️ {sym} 抓取失敗: {e}")

    if not train_sets:
        raise RuntimeError("❌ 沒有任何訓練資料，請檢查 API 或網路連線")

    # 可先小跑，確認流程無誤後改大
    # study.optimize(lambda trial: objective(trial, train_sets), n_trials=1000)
    study.optimize(lambda trial: objective(trial, train_sets), n_trials=200)

    best_params = study.best_params
    print(f"\n🔥 跨幣種最佳參數: {best_params}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    result_file = os.path.join(base_dir, "results", f"optuna_results_{timestamp}.csv")
    results = []
    for sym, test_df in test_sets.items():
        final_capital = run_strategy_combo(best_params["strategy_combo"], test_df, best_params)
        results.append({"symbol": sym, "final_capital": final_capital})
    pd.DataFrame(results).to_csv(result_file, index=False)

    merge_and_plot(base_dir)
    print(f"✅ 測試集結果已輸出 → {result_file}")