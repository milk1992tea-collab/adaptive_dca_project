# dashboard.py
import streamlit as st
import json
from pathlib import Path
from backtester import Backtester
import optuna
import pandas as pd
import datetime

# === 檔案路徑 ===
BEST_PARAMS_FILE = Path(__file__).parent / "best_params.json"
HISTORY_FILE = Path(__file__).parent / "best_params_history.json"

# === 預設參數 ===
DEFAULT_PARAMS = {
    "rsi_buy": 30,
    "kdj_buy": 30,
    "rsi_sell": 70,
    "kdj_sell": 70,
    "td_trigger": 9,
    "stop_loss": 0.95,
    "take_profit": 1.05,
    "trailing_stop": 0.05
}

def load_best_params():
    if BEST_PARAMS_FILE.exists():
        with open(BEST_PARAMS_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_PARAMS

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(params, result):
    history = load_history()
    entry = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "params": params,
        "pnl": result["pnl"],
        "sharpe": result["sharpe"],
        "maxdd": result["maxdd"]
    }
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# === Optuna 目標函數 ===
def objective(trial):
    params = {
        "rsi_buy": trial.suggest_int("rsi_buy", 20, 40),
        "kdj_buy": trial.suggest_int("kdj_buy", 20, 40),
        "rsi_sell": trial.suggest_int("rsi_sell", 60, 80),
        "kdj_sell": trial.suggest_int("kdj_sell", 60, 80),
        "td_trigger": trial.suggest_categorical("td_trigger", [9, 13]),
        "stop_loss": trial.suggest_float("stop_loss", 0.90, 0.99),
        "take_profit": trial.suggest_float("take_profit", 1.01, 1.20),
        "trailing_stop": trial.suggest_float("trailing_stop", 0.01, 0.10)
    }
    bt = Backtester("BTCUSDT", initial_balance=1000, fee_rate=0.001, slippage=0.0005, leverage=3)
    result = bt.run(params, lookback=2000)
    return result["pnl"], result["sharpe"], -result["maxdd"]

def save_best_params(study):
    best_trial = study.best_trials[0]
    with open(BEST_PARAMS_FILE, "w") as f:
        json.dump(best_trial.params, f, indent=2)
    return best_trial.params

# === Streamlit 介面 ===
st.set_page_config(page_title="VA-AL Dashboard", layout="wide")
st.title("📊 VA-AL Trading Dashboard")

# 選擇參數來源
mode = st.radio("選擇參數來源", ["預設參數", "最佳參數 (Optuna)"])
params = DEFAULT_PARAMS if mode == "預設參數" else load_best_params()
st.json(params)

# 回測設定
symbol = st.text_input("交易對 (symbol)", "BTCUSDT")
lookback = st.slider("回測資料長度 (K線數)", min_value=500, max_value=5000, value=2000, step=500)

if st.button("執行回測"):
    bt = Backtester(symbol, initial_balance=1000, fee_rate=0.001, slippage=0.0005, leverage=3)
    result = bt.run(params, lookback=lookback, save_report=False, label=mode)

    st.subheader("📈 回測結果")
    col1, col2, col3 = st.columns(3)
    col1.metric("PnL", f"{result['pnl']:.2f} USDT")
    col2.metric("Sharpe Ratio", f"{result['sharpe']:.2f}")
    col3.metric("Max Drawdown", f"{result['maxdd']:.2f}")

    st.line_chart(result["equity_curve"])

# === 一鍵觸發 Optuna 優化 ===
st.subheader("⚡ Optuna 優化")
n_trials = st.slider("優化迭代次數 (trials)", min_value=10, max_value=200, value=50, step=10)

if st.button("開始優化"):
    with st.spinner("正在進行 Optuna 優化，請稍候..."):
        study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
        study.optimize(objective, n_trials=n_trials)
        best_params = save_best_params(study)

    st.success("✅ 優化完成，最佳參數已更新！")
    st.json(best_params)

    # 自動回測最佳參數
    bt = Backtester(symbol, initial_balance=1000, fee_rate=0.001, slippage=0.0005, leverage=3)
    result = bt.run(best_params, lookback=lookback, save_report=False, label="optuna_best")

    # 儲存到歷史紀錄
    save_history(best_params, result)

    st.subheader("📊 最佳參數回測結果")
    col1, col2, col3 = st.columns(3)
    col1.metric("PnL", f"{result['pnl']:.2f} USDT")
    col2.metric("Sharpe Ratio", f"{result['sharpe']:.2f}")
    col3.metric("Max Drawdown", f"{result['maxdd']:.2f}")

    st.line_chart(result["equity_curve"])

# === 歷史最佳參數比較 ===
st.subheader("📜 歷史最佳參數紀錄")
history = load_history()
if history:
    df = pd.DataFrame(history)
    st.dataframe(df[["date", "pnl", "sharpe", "maxdd"]])

    # 讓使用者選擇某一筆紀錄
    selected_date = st.selectbox("選擇一筆歷史紀錄回測", df["date"].tolist())
    if selected_date:
        selected_entry = next(item for item in history if item["date"] == selected_date)
        st.json(selected_entry["params"])

        if st.button("重跑這組參數回測"):
            bt = Backtester(symbol, initial_balance=1000, fee_rate=0.001, slippage=0.0005, leverage=3)
            result = bt.run(selected_entry["params"], lookback=lookback, save_report=False, label="history_retest")

            st.subheader(f"📊 {selected_date} 回測結果")
            col1, col2, col3 = st.columns(3)
            col1.metric("PnL", f"{result['pnl']:.2f} USDT")
            col2.metric("Sharpe Ratio", f"{result['sharpe']:.2f}")
            col3.metric("Max Drawdown", f"{result['maxdd']:.2f}")

            st.line_chart(result["equity_curve"])
else:
    st.info("目前沒有歷史紀錄")