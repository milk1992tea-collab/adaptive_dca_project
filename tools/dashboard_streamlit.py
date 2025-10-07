# adaptive_dca_ai/tools/dashboard_streamlit.py
import pathlib
import pandas as pd
import streamlit as st
import plotly.express as px

# === 基本設定 ===
st.set_page_config(page_title="VA-AL 控制台", layout="wide")
st.title("📊 VA‑AL 策略分析面板")

# === 載入資料 ===
OUTDIR = pathlib.Path(__file__).parent / "outputs"
CSV = OUTDIR / "flat_trials_enriched.csv"

if not CSV.exists():
    st.error(f"找不到資料檔案: {CSV}")
    st.stop()

df = pd.read_csv(CSV)

# === Top 策略表格 ===
st.subheader("🏆 Top 策略 (依 Sharpe 排序)")
top_df = df.sort_values(by="sharpe", ascending=False).head(10)
st.dataframe(
    top_df[
        ["trial_id", "pnl", "sharpe", "maxdd",
         "rsi_threshold", "dca_ratio", "dca_spacing",
         "dca_max_steps", "td_confirm"]
    ],
    use_container_width=True
)

# === 參數 vs 績效 散點圖 ===
st.subheader("📈 參數與績效關係")
param = st.selectbox("選擇參數", ["rsi_threshold", "dca_ratio", "dca_spacing", "dca_max_steps", "td_confirm"])
metric = st.selectbox("選擇績效指標", ["pnl", "sharpe", "maxdd", "win_rate"])

fig = px.scatter(
    df, x=param, y=metric, color="sharpe",
    hover_data=["trial_id"],
    title=f"{param} vs {metric}"
)
st.plotly_chart(fig, use_container_width=True)

# === 績效分布圖 ===
st.subheader("📊 績效分布")
metric2 = st.selectbox("選擇要查看的績效分布", ["pnl", "sharpe", "maxdd"])
fig2 = px.histogram(df, x=metric2, nbins=30, title=f"{metric2} 分布")
st.plotly_chart(fig2, use_container_width=True)

# === Top 3 最相關參數 (簡單計算) ===
st.subheader("🔍 Top 3 最相關參數")
numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
perf_cols = ["pnl", "sharpe", "maxdd", "win_rate"]
param_cols = [c for c in numeric_cols if c not in perf_cols and c not in ["trial_id", "number", "study_id"]]

if param_cols:
    corr = df[numeric_cols].corr()
    results = []
    for p in param_cols:
        for m in perf_cols:
            if m in corr and p in corr:
                results.append((p, m, corr.loc[p, m]))
    out_df = pd.DataFrame(results, columns=["param", "metric", "correlation"])
    top3 = out_df.groupby("param")["correlation"].apply(lambda x: x.abs().max()).sort_values(ascending=False).head(3)
    st.table(top3)
else:
    st.info("目前沒有可用的參數欄位做相關性分析。")