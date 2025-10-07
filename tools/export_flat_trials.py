# tools/export_flat_trials.py
import sys
import pathlib
import pandas as pd

# 把專案根加入 sys.path （檔案位置 -> ../.. -> Desktop\v_infinity）
this_file = pathlib.Path(__file__).resolve()
project_root = this_file.parents[2]  # ...\adaptive_dca_ai\tools -> parents[2] = Desktop\v_infinity
sys.path.insert(0, str(project_root))

# 直接 import 你的 module
from adaptive_dca_ai.code import model_selector

OUTDIR = pathlib.Path(__file__).parent / "outputs"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTCSV = OUTDIR / "flat_trials.csv"

def main():
    df = None
    # 優先使用 enriched study（會自動合併 param_* 欄位）
    try:
        df = model_selector.get_enriched_study()
    except Exception:
        df = None

    # 若 enriched result 看起來是原始 trials table或為空，嘗試用 study_to_dataframe 轉換
    try:
        if (df is None) or (not isinstance(df, pd.DataFrame)) or df.empty:
            raw = model_selector.get_study()
            if hasattr(model_selector, "study_to_dataframe"):
                df = model_selector.study_to_dataframe(raw)
            else:
                df = pd.DataFrame()
    except Exception:
        try:
            df = model_selector.study_to_dataframe(model_selector.get_study())
        except Exception:
            df = pd.DataFrame()

    # 若仍沒有 pnl 欄位，嘗試由 get_all_candidates 建立
    if "pnl" not in df.columns:
        try:
            cands = model_selector.get_all_candidates(limit=1000)
            if cands:
                df2 = pd.DataFrame(cands)
                # expand params dict into param_* columns if present
                if "params" in df2.columns:
                    params_df = pd.json_normalize(df2["params"].fillna({})).add_prefix("param_")
                    df2 = pd.concat([df2.drop(columns=["params"]), params_df], axis=1)
                df = df2
        except Exception:
            pass

    # 最後寫出 CSV（即使沒有 pnl 也會寫出，方便檢查）
    try:
        df.to_csv(OUTCSV, index=False)
        print(f"Saved flat CSV: {OUTCSV}")
    except Exception as e:
        print("Failed to write flat CSV:", e)

if __name__ == "__main__":
    main()