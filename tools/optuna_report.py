# adaptive_dca_ai/tools/optuna_report.py
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import matplotlib.pyplot as plt
import pandas as pd
import os

from v_infinity.adaptive_dca_ai.code import model_selector

def generate_optuna_report(output_dir=None):
    study = model_selector.get_study()
    df = model_selector.study_to_dataframe(study)

    if df.empty:
        print("❌ 沒有 trial 資料可分析")
        return

    outdir = output_dir or os.path.join(pathlib.Path(__file__).parent, "outputs")
    os.makedirs(outdir, exist_ok=True)

    # 散佈圖：Sharpe vs PnL
    plt.figure(figsize=(10,6))
    plt.scatter(df["sharpe"], df["pnl"], c="blue", alpha=0.6)
    plt.xlabel("Sharpe Ratio")
    plt.ylabel("PnL")
    plt.title("Optuna Trial 分布圖")
    plt.grid(True)
    plt.tight_layout()
    png_path = os.path.join(outdir, "optuna_report.png")
    plt.savefig(png_path)
    print(f"📊 Trial 分布圖已儲存：{png_path}")
    plt.show()

    # 顯示參數影響（前幾個 trial）
    print("\n📈 超參數影響（前幾個 trial）：")
    print(df[["trial_id", "pnl", "sharpe", "maxdd"] + df.columns[df.columns.str.startswith("param_")].tolist()].head(10))

if __name__ == "__main__":
    generate_optuna_report()
    import optuna
import pandas as pd

def get_study(storage_path="sqlite:///adaptive_dca_ai/data/optuna_trials.db", study_name="va_al_study"):
    try:
        study = optuna.load_study(study_name=study_name, storage=storage_path)
        return study
    except Exception as e:
        print(f"❌ 無法載入 study：{e}")
        return None

def study_to_dataframe(study):
    if study is None:
        return pd.DataFrame()
    trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    rows = []
    for t in trials:
        row = {
            "trial_id": t.number,
            "pnl": t.value.get("pnl") if isinstance(t.value, dict) else None,
            "sharpe": t.value.get("sharpe") if isinstance(t.value, dict) else None,
            "maxdd": t.value.get("maxdd") if isinstance(t.value, dict) else None,
        }
        for k, v in t.params.items():
            row[f"param_{k}"] = v
        rows.append(row)
    return pd.DataFrame(rows)