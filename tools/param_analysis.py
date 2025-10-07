import pathlib
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

this_file = pathlib.Path(__file__).resolve()
OUTDIR = this_file.parent / "outputs"
OUTDIR.mkdir(parents=True, exist_ok=True)

# 優先讀取 enriched CSV
ENRICHED = OUTDIR / "flat_trials_enriched.csv"
FLAT = OUTDIR / "flat_trials.csv"

if ENRICHED.exists():
    infile = ENRICHED
else:
    infile = FLAT

print(f"Loading data from: {infile}")
df = pd.read_csv(infile)

# 過濾數值欄位
numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
exclude = {"trial_id", "number", "study_id"}
numeric_cols = [c for c in numeric_cols if c not in exclude]

perf_cols = ["pnl", "sharpe", "maxdd", "win_rate"]
param_cols = [c for c in numeric_cols if c not in perf_cols]

if len(param_cols) == 0:
    print("找不到可用的參數欄位，無法分析。")
    exit()

# === 相關性矩陣 ===
corr = df[numeric_cols].corr()

# 熱力圖 (靜態)
heatmap_file = OUTDIR / "correlation_heatmap.png"
plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", cbar=True)
plt.title("Correlation Heatmap: Params vs Performance", fontsize=14)
plt.tight_layout()
plt.savefig(heatmap_file)
plt.close()
print(f"Saved heatmap: {heatmap_file}")

# === 散點圖 (靜態) ===
scatter_files = []
for p in param_cols:
    for m in perf_cols:
        if m in df.columns:
            plt.figure(figsize=(6, 4))
            sns.scatterplot(x=df[p], y=df[m])
            sns.regplot(x=df[p], y=df[m], scatter=False, color="red")
            plt.xlabel(p)
            plt.ylabel(m)
            plt.title(f"{p} vs {m}")
            plt.tight_layout()
            fname = OUTDIR / f"scatter_{p}_vs_{m}.png"
            plt.savefig(fname)
            plt.close()
            scatter_files.append(fname)
print("Saved scatter plots for all param ↔ metric pairs.")

# === 數值相關性表格 ===
results = []
for p in param_cols:
    for m in perf_cols:
        if m in corr and p in corr:
            results.append((p, m, corr.loc[p, m]))

out_df = pd.DataFrame(results, columns=["param", "metric", "correlation"])
out_df = out_df.sort_values(by="correlation", key=abs, ascending=False)

OUTCSV = OUTDIR / "param_correlations.csv"
out_df.to_csv(OUTCSV, index=False)
print(f"Saved correlations to: {OUTCSV}")

# === Top 3 最相關參數 ===
top3 = out_df.groupby("param")["correlation"].apply(lambda x: x.abs().max()).sort_values(ascending=False).head(3)

# === 生成 HTML 報告（含 Plotly 互動圖） ===
html_file = OUTDIR / "param_analysis_report.html"
with open(html_file, "w", encoding="utf-8") as f:
    f.write("<html><head><meta charset='utf-8'><title>參數分析報告</title></head><body>")
    f.write("<h1>參數分析報告</h1>")
    f.write(f"<p>來源資料: <b>{infile.name}</b></p>")
    f.write("<h2>Top 3 最相關參數</h2><ul>")
    for param, corr_val in top3.items():
        f.write(f"<li><b>{param}</b> → 最大相關性 = {corr_val:.3f}</li>")
    f.write("</ul>")

    f.write("<h2>相關性熱力圖 (靜態)</h2>")
    f.write(f"<img src='{heatmap_file.name}' width='600'><br>")

    f.write("<h2>互動式散點圖 (Plotly)</h2>")
    for p in param_cols:
        for m in perf_cols:
            if m in df.columns:
                fig = px.scatter(df, x=p, y=m, trendline="ols",
                                 title=f"{p} vs {m}",
                                 labels={p: p, m: m})
                plot_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
                f.write(plot_html)
                f.write("<br><br>")

    f.write("<h2>完整相關性表格 (前20筆)</h2>")
    f.write(out_df.head(20).to_html(index=False))
    f.write("<p>(完整表格已輸出到 param_correlations.csv)</p>")
    f.write("</body></html>")

print(f"HTML report with interactive charts saved to: {html_file}")