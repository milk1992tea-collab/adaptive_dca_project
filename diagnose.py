import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from itertools import product, combinations

from volume_scanner import get_top_volume_symbols
from portfolio_manager import PortfolioManager
from position_logger import log_positions
from report_generator import generate_report
from execution_engine import ExecutionEngine
from backtester import (
    backtest,
    backtest_multi_tf,
    backtest_multi_tf_hybrid,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    trend_strategy,
    osc_strategy,
    hybrid_strategy
)
from config import STRATEGIES, TIMEFRAMES, PARAM_GRID, MULTI_TF_CONFIG

# 強制 stdout/stderr 為 UTF-8，避免 CP950 無法輸出 emoji 導致的 UnicodeEncodeError
import sys
try:
    # Python 3.7+ 可用
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    # 退回方案：重包裝原有的 buffer
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# ========== 策略分派 ==========
def run_backtest(symbol, strategy, timeframe, params):
    if strategy == "trend_mix":
        return backtest(symbol, strategy="trend_mix", timeframe=timeframe, limit=1000)
    elif strategy == "osc_mix":
        return backtest(symbol, strategy="osc_mix", timeframe=timeframe, limit=1000)
    elif strategy == "hybrid_mix":
        return backtest(symbol, strategy="hybrid_mix", timeframe=timeframe, limit=1000)
    elif strategy == "multi_tf_trend":
        return backtest_multi_tf(
            symbol,
            strategy_func=trend_strategy,
            higher_tf=MULTI_TF_CONFIG["higher_tf"],
            lower_tf=MULTI_TF_CONFIG["lower_tf"],
            limit=1000
        )
    elif strategy == "multi_tf_hybrid":
        return backtest_multi_tf_hybrid(
            symbol,
            higher_tf=MULTI_TF_CONFIG["higher_tf"],
            lower_tf=MULTI_TF_CONFIG["lower_tf"],
            limit=1000
        )
    else:
        return backtest(symbol, strategy="trend_mix", timeframe=timeframe, limit=1000)


# ========== 批次回測 ==========
def batch_backtest(symbols):
    results = {}
    param_combos = list(product(*PARAM_GRID.values()))
    param_keys = list(PARAM_GRID.keys())

    for symbol in symbols:
        for strategy in STRATEGIES:
            for timeframe in TIMEFRAMES:
                for i, combo in enumerate(param_combos):
                    param_dict = dict(zip(param_keys, combo))
                    key = (symbol, strategy, timeframe, f"param_{i}")

                    result = run_backtest(symbol, strategy, timeframe, param_dict)
                    result["equity_curve"] = result.get("equity_curve", [])
                    results[key] = result

    return pd.DataFrame(results).T


# ========== 結果解讀 ==========
def interpret_results(df):
    print("\n=== 快速解讀 ===")
    for idx, row in df.iterrows():
        symbol, strat, tf, pid = idx
        trades = row.get("trades", 0)
        pnl = row.get("total_pnl", 0.0)
        dd = row.get("max_drawdown", 0.0)
        sharpe = row.get("sharpe_ratio", 0.0)
        comment = "樣本少" if trades < 5 else "活躍" if trades > 50 else f"{int(trades)} 筆"
        print(f"{symbol}-{strat}-{tf}-{pid}: {comment}；PnL={pnl}；DD={dd}；Sharpe={sharpe}")


# ========== 策略組合推薦 ==========
def find_complementary_combos(df, top_n=5):
    print("\n=== 自動推薦互補策略組合 ===")
    combos = list(combinations(df.index, 2))
    results = []

    for a, b in combos:
        curve_a = df.loc[a].get("equity_curve", [])
        curve_b = df.loc[b].get("equity_curve", [])
        if not curve_a or not curve_b:
            continue

        min_len = min(len(curve_a), len(curve_b))
        if min_len == 0:
            continue

        combo_curve = [(curve_a[i] + curve_b[i]) / 2 for i in range(min_len)]
        pnl = combo_curve[-1] - combo_curve[0]
        dd = calculate_max_drawdown(combo_curve)
        sharpe = calculate_sharpe_ratio(combo_curve)

        results.append({
            "combo": f"{a} + {b}",
            "pnl": round(pnl, 2),
            "drawdown": round(dd, 3),
            "sharpe": round(sharpe, 2)
        })

    df_combo = pd.DataFrame(results).sort_values(by="sharpe", ascending=False).head(top_n)
    print(df_combo if not df_combo.empty else "（無可用組合）")
    return df_combo


def optimize_combos(df, max_group_size=3, top_n=5):
    print(f"\n=== 最佳策略組合推薦 (最多 {max_group_size} 策略) ===")
    candidates = [idx for idx in df.index if isinstance(df.loc[idx].get("equity_curve", []), list)]
    results = []

    for r in range(2, max_group_size + 1):
        for group in combinations(candidates, r):
            curves = [df.loc[g].get("equity_curve", []) for g in group]
            lens = [len(c) for c in curves if c]
            if not lens:
                continue
            min_len = min(lens)
            if min_len == 0:
                continue

            curves = [np.array(c[:min_len]) for c in curves]
            combo_curve = sum(curves) / len(curves)

            pnl = combo_curve[-1] - combo_curve[0]
            dd = calculate_max_drawdown(combo_curve)
            sharpe = calculate_sharpe_ratio(combo_curve)

            results.append({
                "combo": " + ".join([str(g) for g in group]),
                "pnl": round(pnl, 2),
                "drawdown": round(dd, 3),
                "sharpe": round(sharpe, 2)
            })

    df_opt = pd.DataFrame(results).sort_values(by="sharpe", ascending=False).head(top_n)
    print(df_opt if not df_opt.empty else "（無最佳組合）")
    return df_opt


# ========== 分析與報告 ==========
def analyze_results(df, pm):
    if "sharpe_ratio" in df.columns:
        df["rank_sharpe"] = df["sharpe_ratio"].rank(ascending=False, method="min").astype(int)
    else:
        df["rank_sharpe"] = np.nan
    if "total_pnl" in df.columns:
        df["rank_pnl"] = df["total_pnl"].rank(ascending=False, method="min").astype(int)
    else:
        df["rank_pnl"] = np.nan

    print("\n=== Top 5 策略 (依 Sharpe Ratio) ===")
    try:
        print(df.sort_values(by="sharpe_ratio", ascending=False).head(5))
    except Exception:
        print("（資料不足）")

    print("\n=== Top 5 策略 (依 Total PnL) ===")
    try:
        print(df.sort_values(by="total_pnl", ascending=False).head(5))
    except Exception:
        print("（資料不足）")

    interpret_results(df)

    print("\n=== 多週期混合共振專區 (multi_tf_hybrid) ===")
    try:
        mask_hybrid = [idx[1] == "multi_tf_hybrid" for idx in df.index]
        hybrid_df = df[mask_hybrid]
        if not hybrid_df.empty:
            print(
                hybrid_df[["total_pnl", "sharpe_ratio", "max_drawdown", "trades"]]
                .sort_values(by="sharpe_ratio", ascending=False)
                .head(10)
            )
        else:
            print("尚無 multi_tf_hybrid 結果")
    except Exception:
        print("（資料不足）")

    complement_df = find_complementary_combos(df)
    combo_df = optimize_combos(df, max_group_size=3)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.name = f"diagnostic_results_{timestamp}.csv"
    df.to_csv(df.name, encoding="utf-8-sig")
    print(f"\n✅ 結果已存檔: {df.name}")

    held = pm.get_current_positions()
    metrics = {idx[0]: df.loc[idx] for idx in df.index if idx[0] in held}
    log_positions(held, metrics)

    generate_report(df, held_symbols=held, combo_df=combo_df, complement_df=complement_df)


# ========== 主程式 ==========
def _valid_symbol_filter(symbols):
    import ccxt
    exchange = ccxt.bybit({"enableRateLimit": True})
    try:
        markets = exchange.load_markets()
    except Exception:
        markets = {}
    valid = []
    for s in symbols:
        m = markets.get(s)
        if m and m.get("quote") == "USDT" and m.get("base") != "USDT":
            valid.append(s)
    if not valid:
        fallback = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
        valid = [s for s in fallback if s in markets] if markets else fallback
    return valid


if __name__ == "__main__":
    top_symbols_raw = get_top_volume_symbols(limit=50)
    top_symbols = _valid_symbol_filter(top_symbols_raw)

    pm = PortfolioManager(max_positions=10, mode="replace", trigger="sharpe")

    selected = []
    for symbol in top_symbols:
        try:
            result = backtest(symbol, strategy="trend_mix", limit=1000)
            if pm.can_enter(symbol, result):
                print(f"✅ 進場候選：{symbol}")
                selected.append(symbol)
            else:
                print(f"❌ 排除：{symbol}")
        except Exception as e:
            print(f"⚠️ 略過 {symbol}（回測錯誤: {e}）")

    print("\n📌 候選清單：")
    print(selected)

    df = batch_backtest(selected)
    analyze_results(df, pm)

    engine = ExecutionEngine(mode="simulate", base_capital=10000, stop_loss=0.05, take_profit=0.1)

    for symbol in pm.get_current_positions():
        try:
            last_price = df.loc[(symbol, STRATEGIES[0], TIMEFRAMES[0], "param_0")]["equity_curve"][-1]
            engine.execute_signal(symbol, "buy", last_price)
        except Exception:
            print(f"（無法取得 {symbol} 價格，略過進場）")

    for symbol in pm.get_current_positions():
        try:
            curve = df.loc[(symbol, STRATEGIES[0], TIMEFRAMES[0], "param_0")]["equity_curve"]
            for price in curve:
                engine.risk_check(symbol, price)
        except Exception:
            print(f"（無法取得 {symbol} 曲線，略過風控）")

    current_prices = {}
    for s in pm.get_current_positions():
        try:
            current_prices[s] = df.loc[(s, STRATEGIES[0], TIMEFRAMES[0], "param_0")]["equity_curve"][-1]
        except Exception:
            current_prices[s] = None
    engine.close_all_positions(current_prices)
    engine.export_trades("trade_log.csv")

    plt.show()