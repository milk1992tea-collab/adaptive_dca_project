import sqlite3, pathlib, pandas as pd

this_file = pathlib.Path(__file__).resolve()
OUTDIR = this_file.parent / "outputs"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTCSV = OUTDIR / "flat_trials_enriched.csv"

DB = str(this_file.parents[1] / "dca_study.db")

def main():
    conn = sqlite3.connect(DB)

    # trials 基本資訊
    trials = pd.read_sql_query(
        "SELECT trial_id, number, study_id, state, datetime_start, datetime_complete FROM trials",
        conn
    )

    # trial_values → pivot 成績效欄位
    values = pd.read_sql_query("SELECT trial_id, objective, value FROM trial_values", conn)
    pivot_vals = values.pivot(index="trial_id", columns="objective", values="value").reset_index()
    pivot_vals = pivot_vals.rename(columns={0: "pnl", 1: "maxdd", 2: "sharpe"})

    # trial_params → pivot 成參數欄位
    params = pd.read_sql_query("SELECT trial_id, param_name, param_value FROM trial_params", conn)
    pivot_params = params.pivot(index="trial_id", columns="param_name", values="param_value").reset_index()

    # 合併 trials + values + params
    df = pd.merge(trials, pivot_vals, on="trial_id", how="left")
    df = pd.merge(df, pivot_params, on="trial_id", how="left")

    # win_rate 不在 DB，先填 0
    df["win_rate"] = 0.0

    df.to_csv(OUTCSV, index=False)
    print("Wrote enriched CSV:", OUTCSV)
    print(df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()