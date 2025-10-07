#!/usr/bin/env python3
import os
import sys
import optuna

from code.data_loader import DataLoader
from code.real_ai_model import RealAIPredictor
from code.simulate_dca_strategy import simulate_dca_strategy
from v_infinity.orchestrator import Orchestrator

def objective(trial):
    # 1. 建議/優化參數
    rsi_threshold = trial.suggest_int("rsi_threshold", 20, 80)
    td_confirm    = trial.suggest_categorical("td_confirm", [True, False])
    dca_ratio     = trial.suggest_float("dca_ratio", 0.1, 0.5)
    dca_spacing   = trial.suggest_float("dca_spacing", 0.01, 0.05)
    dca_max_steps = trial.suggest_int("dca_max_steps", 1, 5)

    loader = DataLoader(root=os.path.dirname(os.path.dirname(__file__)))
    predictor = RealAIPredictor(model_path="models/trend_model.pt")

    pnls, maxdds, sharpes = [], [], []

    # 2. 讀真實 OHLCV 資料
    for sym in loader.top_symbols(limit=50):
        df_4h = loader.load(sym, timeframe="4h")
        signal, conf = predictor.predict(df_4h, sym, timeframe="4h")

        if signal != "bullish" or conf < 0.7:
            continue

        df_5m = loader.load(sym, timeframe="5m")
        pnl, maxdd, sharpe = simulate_dca_strategy(
            df_5m,
            rsi_threshold,
            td_confirm,
            dca_ratio,
            dca_spacing,
            dca_max_steps
        )

        pnls.append(pnl)
        maxdds.append(maxdd)
        sharpes.append(sharpe)
        if len(pnls) >= 10:
            break

    if not pnls:
        raise RuntimeError("No valid OHLCV data after filtering")

    return sum(pnls) / len(pnls), sum(maxdds) / len(maxdds), sum(sharpes) / len(sharpes)

def main():
    project_root = os.path.dirname(os.path.dirname(__file__))
    os.chdir(project_root)

    db_path     = os.path.join(project_root, "dca_study.db")
    storage_url = f"sqlite:///{db_path}"

    study = optuna.create_study(
        directions=["maximize", "minimize", "maximize"],
        sampler=optuna.samplers.NSGAIISampler(),
        storage=storage_url,
        study_name="dca_study",
        load_if_exists=True
    )
    study.optimize(objective, n_trials=50, show_progress_bar=True)

    # 3. 取出最優結果並呼叫 orchestrator 做實盤接入
    best_trials = study.best_trials
    best_params = [t.params for t in best_trials]
    Orchestrator().start_live(best_params)

if __name__ == "__main__":
    main()