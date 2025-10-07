import optuna
import json
from backtest import load_data, backtest, calc_metrics

# === Optuna 目標函式 ===
def objective(trial):
    # 1. 定義參數搜尋空間
    params = {
        "buy_threshold": trial.suggest_float("buy_threshold", 0.0005, 0.05),
        "sell_threshold": trial.suggest_float("sell_threshold", 0.0005, 0.05),
        "position_size": trial.suggest_float("position_size", 0.001, 0.01),
    }

    # 2. 多資產回測 (BTC/ETH/BNB)
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    total_returns, max_drawdowns = [], []

    for symbol in symbols:
        df = load_data(symbol)
        final_value, trades, equity_curve = backtest(df, params)
        total_return, max_drawdown, sharpe_ratio = calc_metrics(equity_curve)

        total_returns.append(total_return)
        max_drawdowns.append(max_drawdown)

    # 3. 計算平均績效
    avg_return = sum(total_returns) / len(total_returns)
    avg_drawdown = sum(max_drawdowns) / len(max_drawdowns)

    # 4. 回傳多目標 (最大化報酬率、最小化回撤)
    return avg_return, -avg_drawdown


if __name__ == "__main__":
    # 建立多目標 study
    study = optuna.create_study(directions=["maximize", "maximize"])
    study.optimize(objective, n_trials=100)

    # 輸出 Pareto Front
    print("\n=== Pareto Front Trials ===")
    for t in study.best_trials:
        print(f"Values={t.values}, Params={t.params}")

    # 儲存最佳參數 (以第一個 Pareto 解為例)
    best_params = study.best_trials[0].params
    with open("../configs/strategy_params.json", "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=4, ensure_ascii=False)

    print("\n✅ 已將最佳參數更新到 configs/strategy_params.json")