import optuna
import numpy as np
from strategies import STRATEGY_CONFIGS, run_strategy
from signal_generator import generate_signal

# 假設你有一個回測函數
def backtest(strategy_name, weights, threshold, df_1m, df_15m, df_1h):
    """
    回測策略績效
    return: 總收益率 或 Sharpe Ratio
    """
    # 更新策略配置
    STRATEGY_CONFIGS[strategy_name]["weights"] = weights
    STRATEGY_CONFIGS[strategy_name]["threshold"] = threshold

    balance = 10000
    position = 0
    pnl_history = []

    for i in range(50, len(df_1m)):  # 從第50根開始，避免指標計算不完整
        sigs = generate_signal(df_1m.iloc[:i], df_15m.iloc[:i//15], df_1h.iloc[:i//60])
        decision = run_strategy(strategy_name, sigs)

        price = df_1m["close"].iloc[i]

        if decision == 1 and position == 0:
            position = balance / price
            balance = 0
        elif decision == -1 and position > 0:
            balance = position * price
            pnl_history.append(balance)
            position = 0

    # 最後平倉
    if position > 0:
        balance = position * df_1m["close"].iloc[-1]

    # 總收益率
    total_return = (balance - 10000) / 10000
    # 簡單 Sharpe Ratio
    if len(pnl_history) > 1:
        returns = np.diff(pnl_history) / pnl_history[:-1]
        sharpe = np.mean(returns) / (np.std(returns) + 1e-9)
    else:
        sharpe = total_return

    return sharpe

# Optuna 目標函數
def objective(trial):
    strategy_name = trial.suggest_categorical("strategy", ["trend_mix", "osc_mix", "hybrid_mix"])

    # 動態生成權重
    weights = {}
    for ind in STRATEGY_CONFIGS[strategy_name]["weights"].keys():
        weights[ind] = trial.suggest_float(f"w_{ind}", 0.0, 1.0)

    threshold = trial.suggest_float("threshold", 0.1, 0.5)

    # 假設你已經有 df_1m, df_15m, df_1h
    score = backtest(strategy_name, weights, threshold, df_1m, df_15m, df_1h)
    return score

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)

    print("最佳參數:", study.best_params)
    print("最佳績效:", study.best_value)