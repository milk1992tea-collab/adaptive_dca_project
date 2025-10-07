# vaal_optuna.py
import optuna
import json
from pathlib import Path
from backtester import Backtester

# 儲存最佳參數的檔案
BEST_PARAMS_FILE = Path(__file__).parent / "best_params.json"

# === Optuna 目標函數 ===
def objective(trial):
    params = {
        # 指標閾值（供均值回歸 & 基本風控）
        "rsi_buy": trial.suggest_int("rsi_buy", 20, 40),
        "rsi_sell": trial.suggest_int("rsi_sell", 60, 80),
        "kdj_buy": trial.suggest_int("kdj_buy", 20, 40),
        "kdj_sell": trial.suggest_int("kdj_sell", 60, 80),
        "td_trigger": trial.suggest_categorical("td_trigger", [9, 13]),

        # 風控
        "stop_loss": trial.suggest_float("stop_loss", 0.90, 0.99),
        "take_profit": trial.suggest_float("take_profit", 1.01, 1.20),
        "trailing_stop": trial.suggest_float("trailing_stop", 0.01, 0.10),

        # 多週期 / 過濾器
        "use_multi_timeframe": trial.suggest_categorical("use_multi_timeframe", [0, 1]),
        "use_breakout_filter": trial.suggest_categorical("use_breakout_filter", [0, 1]),

        # 多策略組合開關
        "use_breakout": trial.suggest_categorical("use_breakout", [0, 1]),
        "use_mean_reversion": trial.suggest_categorical("use_mean_reversion", [0, 1]),
        "use_trend_follow": trial.suggest_categorical("use_trend_follow", [0, 1]),

        # 多策略權重
        "weight_breakout": trial.suggest_float("weight_breakout", 0.2, 2.0),
        "weight_mean": trial.suggest_float("weight_mean", 0.2, 2.0),
        "weight_trend": trial.suggest_float("weight_trend", 0.2, 2.0),
        "vote_mode": trial.suggest_categorical("vote_mode", ["weighted", "majority"]),

        # 資金分配
        "allocation_mode": trial.suggest_categorical("allocation_mode", [0, 1]),  # 0=固定金額, 1=固定比例
        "allocation_value": trial.suggest_float("allocation_value", 0.01, 0.20),

        # 動態資金分配
        "use_dynamic_allocation": trial.suggest_categorical("use_dynamic_allocation", [0, 1]),
        "dynamic_target_pct": trial.suggest_float("dynamic_target_pct", 0.02, 0.10),  # 2%~10%
        "dynamic_cap_pct": trial.suggest_float("dynamic_cap_pct", 0.10, 0.30),        # 10%~30%
        "alloc_alpha": trial.suggest_float("alloc_alpha", 0.2, 0.8),                  # 成交額權重
        "account_balance": 1000  # 回測用固定值；實盤請由外部注入
    }

    # 呼叫完整回測模組
    bt = Backtester("BTCUSDT", initial_balance=1000, fee_rate=0.001, slippage=0.0005, leverage=3)
    result = bt.run(params, lookback=2000)

    # 多目標優化：最大化 PnL & Sharpe，最小化 MaxDD
    return result["pnl"], result["sharpe"], -result["maxdd"]

def save_best_params(study):
    """將最佳參數存成 JSON"""
    best_trial = study.best_trials[0]
    with open(BEST_PARAMS_FILE, "w") as f:
        json.dump(best_trial.params, f, indent=2)
    print(f"最佳參數已儲存到 {BEST_PARAMS_FILE}")
    return best_trial.params

if __name__ == "__main__":
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    study.optimize(objective, n_trials=50)

    print("最佳參數:")
    for t in study.best_trials:
        print(t.values, t.params)

    save_best_params(study)