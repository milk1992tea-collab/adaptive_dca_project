import os
import optuna
import numpy as np
import pandas as pd

from code.get_top_50_assets import get_top_50_assets_by_volume
from code.ai_predict_trend import ai_predict_trend
from code.simulate_dca_strategy import simulate_dca_strategy

def objective(trial):
    # 建議/優化參數
    rsi_threshold = trial.suggest_int("rsi_threshold", 20, 80)
    td_confirm    = trial.suggest_categorical("td_confirm", [True, False])
    dca_ratio     = trial.suggest_float("dca_ratio", 0.1, 0.5)
    dca_spacing   = trial.suggest_float("dca_spacing", 0.01, 0.05)
    dca_max_steps = trial.suggest_int("dca_max_steps", 1, 5)

    project_root = os.path.dirname(os.path.dirname(__file__))
    top_assets   = get_top_50_assets_by_volume()
    selected     = []

    # 選股
    for sym in top_assets:
        signal, conf = ai_predict_trend(sym, "4H")
        if signal == "bullish" and conf > 0.7:
            selected.append(sym.replace("/", "_"))
        if len(selected) >= 10:
            break

    pnls, maxdds, sharpes = [], [], []

    # 回測模擬
    for sym_file in selected:
        path_5m = os.path.join(project_root, "data", "ohlcv", f"{sym_file}_5m.csv")
        path_4h = os.path.join(project_root, "data", "ohlcv", f"{sym_file}_4h.csv")

        try:
            data_5m = pd.read_csv(path_5m, parse_dates=True, index_col="datetime")
            data_4h = pd.read_csv(path_4h, parse_dates=True, index_col="datetime")
        except FileNotFoundError:
            # 如果檔案不存在就跳過該資產
            continue

        pnl, maxdd, sharpe = simulate_dca_strategy(
            data_5m,
            rsi_threshold,
            td_confirm,
            dca_ratio,
            dca_spacing,
            dca_max_steps
        )
        pnls.append(pnl)
        maxdds.append(maxdd)
        sharpes.append(sharpe)

    # 如果都沒有回測到任何資料，視為失敗
    if not pnls:
        raise RuntimeError("No valid OHLCV CSV found for any selected asset.")

    return np.mean(pnls), np.mean(maxdds), np.mean(sharpes)


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(__file__))
    db_path      = os.path.join(project_root, "dca_study.db")
    storage_url  = f"sqlite:///{db_path}"

    study = optuna.create_study(
        directions=["maximize", "minimize", "maximize"],
        sampler=optuna.samplers.NSGAIISampler(),
        storage=storage_url,
        study_name="dca_study",
        load_if_exists=True
    )

    study.optimize(objective, n_trials=50, show_progress_bar=True)

    # 匯出最佳結果
    best    = study.best_trials
    records = []
    for t in best:
        rec = {
            "trial": t.number,
            "pnl": t.values[0],
            "maxdd": t.values[1],
            "sharpe": t.values[2],
            **t.params
        }
        records.append(rec)

    df     = pd.DataFrame(records)
    out_dir = os.path.join(project_root, "results")
    os.makedirs(out_dir, exist_ok=True)
    df.to_csv(os.path.join(out_dir, "best_trials.csv"), index=False)

    print("\n=== Best Trials (Pareto Front) ===")
    print(df.to_string(index=False))