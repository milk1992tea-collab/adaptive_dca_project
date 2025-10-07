# research/optimize.py
import optuna
import json
from pathlib import Path
import random

PARAMS_FILE = Path(__file__).parent.parent / "configs" / "strategy_params.json"

# 假設的模擬策略績效函數 (用隨機數模擬)
def simulate_strategy(buy_threshold, sell_threshold, position_size):
    # 在真實情境中，這裡應該用歷史數據回測
    # 例如計算收益率、夏普比率、最大回撤等
    # 這裡用隨機數模擬績效
    profit = random.uniform(-1, 1)  # 模擬收益率
    risk_penalty = abs(buy_threshold - sell_threshold) * 0.1
    return profit - risk_penalty

def objective(trial):
    # 定義要優化的參數空間
    buy_threshold = trial.suggest_float("buy_threshold", 0.01, 0.05)
    sell_threshold = trial.suggest_float("sell_threshold", 0.01, 0.05)
    position_size = trial.suggest_float("position_size", 0.001, 0.01)

    # 模擬策略績效
    score = simulate_strategy(buy_threshold, sell_threshold, position_size)
    return score

def main():
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=30)  # 跑 30 次實驗

    best_params = study.best_params
    best_params["symbol"] = "BTCUSDT"  # 固定交易對 (可改成動態)

    print("最佳參數:", best_params)

    # 輸出到 strategy_params.json
    PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PARAMS_FILE, "w") as f:
        json.dump(best_params, f, indent=4)

    print(f"✅ 已將最佳參數存到 {PARAMS_FILE}")

if __name__ == "__main__":
    main()