# report_generator.py
import pandas as pd

def _df_to_markdown(df):
    """
    優先用 pandas 的 to_markdown；
    若環境沒安裝 markdown 依賴，退化為 CSV 包在程式碼區塊。
    """
    try:
        return df.to_markdown(index=True)
    except Exception:
        return "```\n" + df.to_csv(index=True) + "\n```"

def generate_report(df, held_symbols=None, combo_df=None, complement_df=None, filename="diagnostic_report.md"):
    """
    產生 Markdown 報告，包含：
    - 當前持倉
    - Top 策略（Sharpe、PnL）
    - 多週期混合共振（multi_tf_hybrid）專區
    - 互補策略組合推薦、最佳策略組合推薦
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 診斷報告\n\n")

        # 當前持倉
        f.write("## 當前持倉\n")
        if held_symbols:
            for s in held_symbols:
                f.write(f"- {s}\n")
        else:
            f.write("無持倉\n")
        f.write("\n")

        # Top 策略（Sharpe）
        f.write("## Top 策略（Sharpe）\n")
        try:
            top_sharpe = df.sort_values(by="sharpe_ratio", ascending=False).head(5)
            table = top_sharpe[["total_pnl", "sharpe_ratio", "max_drawdown", "trades"]]
            f.write(_df_to_markdown(table) + "\n\n")
        except Exception:
            f.write("資料不足\n\n")

        # Top 策略（PnL）
        f.write("## Top 策略（PnL）\n")
        try:
            top_pnl = df.sort_values(by="total_pnl", ascending=False).head(5)
            table = top_pnl[["total_pnl", "sharpe_ratio", "max_drawdown", "trades"]]
            f.write(_df_to_markdown(table) + "\n\n")
        except Exception:
            f.write("資料不足\n\n")

        # 多週期混合共振專區
        f.write("## 多週期混合共振（multi_tf_hybrid）\n")
        try:
            mask_hybrid = [idx[1] == "multi_tf_hybrid" for idx in df.index]
            hybrid_df = df[mask_hybrid]
            if not hybrid_df.empty:
                table = hybrid_df[["total_pnl", "sharpe_ratio", "max_drawdown", "trades"]] \
                    .sort_values(by="sharpe_ratio", ascending=False)
                f.write(_df_to_markdown(table) + "\n\n")
            else:
                f.write("尚無 multi_tf_hybrid 結果\n\n")
        except Exception:
            f.write("資料不足\n\n")

        # 互補策略組合推薦
        f.write("## 互補策略組合推薦\n")
        if complement_df is not None and not complement_df.empty:
            f.write(_df_to_markdown(complement_df) + "\n\n")
        else:
            f.write("無互補組合\n\n")

        # 最佳策略組合推薦
        f.write("## 最佳策略組合推薦\n")
        if combo_df is not None and not combo_df.empty:
            f.write(_df_to_markdown(combo_df) + "\n\n")
        else:
            f.write("無最佳組合\n\n")

    print(f"📁 報告已生成: {filename}")