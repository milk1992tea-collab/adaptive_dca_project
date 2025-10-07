import json
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# ✅ 字型設定，避免中文亂碼與負號顯示錯誤
matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # Windows 中文字型
matplotlib.rcParams['axes.unicode_minus'] = False

# 檔案路徑
PARAMS_FILE = Path(__file__).parent.parent / "configs" / "strategy_params_list.json"
BEST_PARAM_FILE = Path(__file__).parent.parent / "configs" / "strategy_params.json"
DATA_FILES = {
    "BTCUSDT": Path(__file__).parent / "btc_usdt_1h.csv",
    "ETHUSDT": Path(__file__).parent / "eth_usdt_1h.csv",
    "BNBUSDT": Path(__file__).parent / "bnb_usdt_1h.csv"
}
SUMMARY_FILE = Path(__file__).parent / "backtest_summary.csv"
PARETO_FILE = Path(__file__).parent / "pareto_front.json"

def load_params_list():
    print(f"[INFO] 嘗試讀取參數檔案: {PARAMS_FILE.resolve()}")
    with open(PARAMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_data(symbol):
    print(f"[INFO] 載入數據檔案: {DATA_FILES[symbol].resolve()}")
    return pd.read_csv(DATA_FILES[symbol], parse_dates=["time"])

def backtest(df, params):
    buy_threshold = params["buy_threshold"]
    sell_threshold = params["sell_threshold"]
    position_size = params["position_size"]

    balance = 10000
    position = 0
    trades = []
    equity_curve = []

    for i in range(1, len(df)):
        price_prev = df.loc[i-1, "close"]
        price_now = df.loc[i, "close"]
        change = (price_now - price_prev) / price_prev

        if change <= -buy_threshold and balance > 0:
            position = balance / price_now
            balance = 0
            trades.append(("BUY", price_now, df.loc[i, "time"]))

        elif change >= sell_threshold and position > 0:
            balance = position * price_now
            position = 0
            trades.append(("SELL", price_now, df.loc[i, "time"]))

        equity = balance + position * price_now
        equity_curve.append(equity)

    final_value = balance + position * df.iloc[-1]["close"]
    equity_curve.append(final_value)

    # ✅ Debug 訊息
    total_return = (final_value / 10000 - 1) * 100
    print(f"[DEBUG] Params={params} | 交易次數={len(trades)} | "
          f"前幾筆交易={trades[:3]} | 最終資產={final_value:.2f} | 報酬率={total_return:.2f}%")

    return final_value, trades, equity_curve

def calc_metrics(equity_curve):
    equity = np.array(equity_curve)
    returns = np.diff(equity) / equity[:-1]

    total_return = (equity[-1] / equity[0] - 1) * 100
    running_max = np.maximum.accumulate(equity)
    drawdowns = (equity - running_max) / running_max
    max_drawdown = drawdowns.min() * 100
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

    return total_return, max_drawdown, sharpe_ratio

def is_pareto_efficient(points):
    is_efficient = np.ones(points.shape[0], dtype=bool)
    for i, c in enumerate(points):
        if is_efficient[i]:
            is_efficient[is_efficient] = np.any(points[is_efficient] > c, axis=1) | np.all(points[is_efficient] == c, axis=1)
            is_efficient[i] = True
    return is_efficient

def plot_pareto(summary_df, pareto_df, best):
    plt.figure(figsize=(10,8))
    # 所有點
    plt.scatter(summary_df["max_drawdown(%)"], summary_df["total_return(%)"], 
                c="gray", alpha=0.6, label="All Strategies")
    # Pareto Front
    plt.scatter(pareto_df["max_drawdown(%)"], pareto_df["total_return(%)"], 
                c="red", marker="o", s=100, label="Pareto Front")

    # 標記每個點的 param_set 編號 & Sharpe Ratio
    for _, row in summary_df.iterrows():
        label = f"{row['param_set']}|S:{row['sharpe_ratio']:.2f}"
        plt.text(row["max_drawdown(%)"], row["total_return(%)"], 
                 label, fontsize=7, ha="center", va="bottom")

    # ★ 標記最佳參數 (避免字型警告)
    plt.scatter(best["max_drawdown(%)"], best["total_return(%)"], 
                c="gold", marker="*", s=350, edgecolors="black", label="Best Param ★")

    plt.xlabel("Max Drawdown (%) (越小越好)")
    plt.ylabel("Total Return (%) (越大越好)")
    plt.title("Pareto Front: Return vs Drawdown (含參數編號 & Sharpe Ratio & 最佳★)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    print("=== Backtest 開始 ===")
    params_list = load_params_list()
    print(f"共載入 {len(params_list)} 組參數，將計算 Pareto Front")

    summary = []

    for idx, params in enumerate(params_list, start=1):
        for symbol in DATA_FILES.keys():
            df = load_data(symbol)
            final_value, trades, equity_curve = backtest(df, params)
            total_return, max_drawdown, sharpe_ratio = calc_metrics(equity_curve)

            summary.append({
                "param_set": idx,
                "symbol": symbol,
                "final_value": final_value,
                "total_return(%)": total_return,
                "max_drawdown(%)": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "trades": len(trades),
                "params": params
            })

    # 輸出總結表格
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(SUMMARY_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ 已輸出完整績效矩陣到 {SUMMARY_FILE}")

    # 構建 Pareto Front (Return 最大化、Drawdown 最小化)
    points = summary_df[["total_return(%)", "max_drawdown(%)"]].to_numpy()
    points[:,1] = -points[:,1]  # drawdown 越小越好 → 取負值
    mask = is_pareto_efficient(points)
    pareto_df = summary_df[mask]

    # 輸出 Pareto Front
    pareto_df.to_json(PARETO_FILE, orient="records", indent=4, force_ascii=False)
    print(f"\n🏆 已輸出 Pareto Front 到 {PARETO_FILE}")
    print(pareto_df[["symbol","total_return(%)","max_drawdown(%)","sharpe_ratio","params"]])

    # 選出 Pareto Front 中 Sharpe Ratio 最高的作為最佳參數
    best = pareto_df.sort_values(by="sharpe_ratio", ascending=False).iloc[0]
    best_params = best["params"]
    best_params["symbol"] = best["symbol"]

    # 繪製 Pareto 散點圖 (含參數編號 & Sharpe Ratio & 最佳★)
    plot_pareto(summary_df, pareto_df, best)

    # 更新 strategy_params.json
    with open(BEST_PARAM_FILE, "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=4, ensure_ascii=False)

    print(f"\n✅ 已將 Pareto Front 中 Sharpe 最高的參數更新到 {BEST_PARAM_FILE}")
    print("=== Backtest 結束 ===")
    import optuna

def objective(trial):
    # 1. 定義參數搜尋空間
    params = {
        "buy_threshold": trial.suggest_float("buy_threshold", 0.0005, 0.05),
        "sell_threshold": trial.suggest_float("sell_threshold", 0.0005, 0.05),
        "position_size": trial.suggest_float("position_size", 0.001, 0.01),
    }

    # 2. 載入資料 (這裡先用 BTCUSDT 做示範)
    df = load_data("BTCUSDT")

    # 3. 執行回測
    final_value, trades, equity_curve = backtest(df, params)

    # 4. 計算績效
    total_return, max_drawdown, sharpe_ratio = calc_metrics(equity_curve)

    # 5. 回傳目標值 (多目標)
    return total_return, -max_drawdown
 
if __name__ == "__main__":
    main()