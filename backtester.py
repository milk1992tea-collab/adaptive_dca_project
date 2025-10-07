# backtester.py
import numpy as np
import pandas as pd
import ccxt
import argparse
import json
from typing import Any, Dict, List, Optional

# ========== 鞈??? ==========
def fetch_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 1000, exchange: Optional[Any] = None) -> pd.DataFrame:
    if exchange is None:
        exchange = ccxt.bybit({"enableRateLimit": True})
    try:
        exchange.load_markets()
    except Exception:
        pass

    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception:
        ohlcv = []

    if not ohlcv:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df

# ========== 蝑嚗?釣?亙??賂? ==========
def trend_strategy(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> List[Optional[str]]:
    if df.empty:
        return []
    df = df.copy()
    df["ma_short"] = df["close"].rolling(short_window, min_periods=1).mean()
    df["ma_long"] = df["close"].rolling(long_window, min_periods=1).mean()

    ms = df["ma_short"].values
    ml = df["ma_long"].values

    signals = []
    for i in range(len(df)):
        if np.isnan(ms[i]) or np.isnan(ml[i]):
            signals.append(None)
        elif ms[i] > ml[i]:
            signals.append("up")
        elif ms[i] < ml[i]:
            signals.append("down")
        else:
            signals.append(None)
    return signals

def osc_strategy(df: pd.DataFrame, period: int = 14, upper: float = 70, lower: float = 30) -> List[Optional[str]]:
    if df.empty:
        return []
    df = df.copy()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=1, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    signals = []
    for rsi in df["rsi"]:
        if np.isnan(rsi):
            signals.append(None)
        elif rsi > upper:
            signals.append("sell")
        elif rsi < lower:
            signals.append("buy")
        else:
            signals.append(None)
    return signals

def hybrid_strategy(df: pd.DataFrame, short_window: int = 20, long_window: int = 50, period: int = 14, upper: float = 70, lower: float = 30) -> List[Optional[str]]:
    if df.empty:
        return []
    trend = trend_strategy(df, short_window=short_window, long_window=long_window)
    osc = osc_strategy(df, period=period, upper=upper, lower=lower)

    signals = []
    for t, o in zip(trend, osc):
        if t == "up" and o == "buy":
            signals.append("buy")
        elif t == "down" and o == "sell":
            signals.append("sell")
        else:
            signals.append(None)
    return signals

# ========== ??閮? ==========
def calculate_max_drawdown(equity_curve) -> float:
    """
    Calculate maximum drawdown of an equity curve.
    Accepts list-like objects and numpy arrays.
    Returns max drawdown as positive float (e.g., 0.15 for 15%).
    Defensive against None, empty, or non-numeric inputs.
    """
    if equity_curve is None:
        return 0.0
    try:
        arr = np.asarray(equity_curve, dtype=float)
    except Exception:
        try:
            arr = np.array(list(equity_curve), dtype=float)
        except Exception:
            return 0.0

    if arr.size == 0:
        return 0.0

    # compute running max and drawdowns
    running_max = np.maximum.accumulate(arr)
    # avoid division by zero where running_max == 0
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdowns = (running_max - arr) / np.where(running_max == 0, np.nan, running_max)
    # replace nan with 0 for cases where running_max was zero
    drawdowns = np.nan_to_num(drawdowns, nan=0.0, posinf=0.0, neginf=0.0)
    max_dd = float(np.max(drawdowns)) if drawdowns.size > 0 else 0.0
    return max_dd

def calculate_sharpe_ratio(equity_curve, periods_per_year: int = 252 * 24) -> float:
    """
    Calculate a simple Sharpe-like ratio from equity curve returns.
    periods_per_year default assumes hourly data approx (252 trading days * 24).
    Uses excess return over 0 and annualizes by sqrt.
    """
    if equity_curve is None:
        return 0.0
    try:
        arr = np.asarray(equity_curve, dtype=float)
    except Exception:
        try:
            arr = np.array(list(equity_curve), dtype=float)
        except Exception:
            return 0.0

    if arr.size < 2:
        return 0.0

    # period returns
    returns = np.diff(arr) / (arr[:-1] + 1e-12)
    if returns.size == 0:
        return 0.0

    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=1) if returns.size > 1 else 0.0
    if std_r == 0:
        return 0.0

    # annualize
    sharpe = (mean_r / std_r) * np.sqrt(periods_per_year)
    return float(sharpe)

# ========== 璅⊥鈭斗???==========
def simulate_trades(df: pd.DataFrame, signals: List[Optional[str]], initial_capital: float = 1000.0, allow_partial: bool = False) -> Dict[str, Any]:
    if df.empty or not signals:
        return {
            "trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "equity_curve": []
        }

    capital = float(initial_capital)
    position = 0.0
    equity_curve: List[float] = []

    for i in range(len(df)):
        price = float(df["close"].iloc[i])
        signal = signals[i] if i < len(signals) else None

        if signal == "buy" and position == 0 and capital > 0:
            position = capital / price
            capital = 0.0
        elif signal == "sell" and position > 0:
            capital = position * price
            position = 0.0

        equity = capital + position * price
        equity_curve.append(equity)

    trades = sum(1 for s in signals if s in ("buy", "sell"))
    total_pnl = equity_curve[-1] - initial_capital if equity_curve else 0.0
    max_dd = calculate_max_drawdown(equity_curve) if equity_curve else 0.0
    sharpe = calculate_sharpe_ratio(equity_curve) if equity_curve else 0.0

    result = {
        "trades": trades,
        "total_pnl": float(total_pnl),
        "max_drawdown": float(max_dd),
        "sharpe_ratio": float(sharpe),
        "equity_curve": equity_curve
    }
    return result

# ========== 蝯曹??葫隞嚗?游??豢釣?伐? ==========
def backtest(symbol: str, strategy: str, timeframe: str = "1h", limit: int = 1000, params: Optional[Dict[str, Any]] = None, exchange: Optional[Any] = None) -> Dict[str, Any]:
    params = params or {}
    df = fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, exchange=exchange)

    if df.empty:
        return simulate_trades(pd.DataFrame(), [])

    if strategy == "trend_mix":
        short = int(params.get("short_window", 20))
        long = int(params.get("long_window", 50))
        signals = trend_strategy(df, short_window=short, long_window=long)
    elif strategy == "osc_mix":
        period = int(params.get("rsi_period", 14))
        upper = float(params.get("rsi_upper", 70))
        lower = float(params.get("rsi_lower", 30))
        signals = osc_strategy(df, period=period, upper=upper, lower=lower)
    elif strategy == "hybrid_mix":
        short = int(params.get("short_window", 20))
        long = int(params.get("long_window", 50))
        period = int(params.get("rsi_period", 14))
        upper = float(params.get("rsi_upper", 70))
        lower = float(params.get("rsi_lower", 30))
        signals = hybrid_strategy(df, short_window=short, long_window=long, period=period, upper=upper, lower=lower)
    else:
        short = int(params.get("short_window", 20))
        long = int(params.get("long_window", 50))
        signals = trend_strategy(df, short_window=short, long_window=long)

    result = simulate_trades(df, signals, initial_capital=float(params.get("initial_capital", 1000)))
    # attach some context
    result["symbol"] = symbol
    result["strategy"] = strategy
    result["timeframe"] = timeframe
    result["params"] = params
    return result

# ========== 憭望?撠?撌亙 ==========
def _align_high_to_low_indices(ts_high, ts_low):
    """
    Align higher timeframe timestamps to lower timeframe timestamps.
    For each low timeframe point find last high timeframe index <= that time.
    Works with timezone-aware and naive pandas Series/Index.
    """
    sh = pd.Series(ts_high) if not isinstance(ts_high, pd.Series) else ts_high
    sl = pd.Series(ts_low) if not isinstance(ts_low, pd.Series) else ts_low

    def to_int64_array(s: pd.Series) -> np.ndarray:
        s_dt = pd.to_datetime(s)
        # if timezone-aware, convert to UTC and remove tz
        try:
            if getattr(s_dt.dt, "tz", None) is not None:
                s_dt = s_dt.dt.tz_convert("UTC").dt.tz_localize(None)
        except Exception:
            # ignore tz ops if not available
            pass
        return np.array(s_dt.astype("datetime64[ns]").astype(np.int64))

    hi = to_int64_array(sh)
    lo = to_int64_array(sl)
    idxs = np.searchsorted(hi, lo, side="right") - 1
    return idxs

# ========== 憭望??望嚗?蝑嚗?==========
def backtest_multi_tf(symbol: str, strategy_func=trend_strategy, higher_tf: str = "1h", lower_tf: str = "15m", limit: int = 1000, params: Optional[Dict[str, Any]] = None, exchange: Optional[Any] = None) -> Dict[str, Any]:
    params = params or {}
    df_high = fetch_ohlcv(symbol, timeframe=higher_tf, limit=limit, exchange=exchange)
    df_low = fetch_ohlcv(symbol, timeframe=lower_tf, limit=limit * 4, exchange=exchange)

    if df_high.empty or df_low.empty:
        return simulate_trades(pd.DataFrame(), [])

    signal_high = strategy_func(df_high)
    signal_low = strategy_func(df_low)

    hi_map = _align_high_to_low_indices(df_high["timestamp"], df_low["timestamp"])

    entries = []
    for i in range(len(df_low)):
        hi_idx = hi_map[i]
        if hi_idx < 0 or hi_idx >= len(signal_high):
            entries.append(None)
            continue

        hi_sig = signal_high[hi_idx]
        lo_sig = signal_low[i]

        if hi_sig == "up" and lo_sig == "up":
            entries.append("buy")
        elif hi_sig == "down" and lo_sig == "down":
            entries.append("sell")
        else:
            entries.append(None)

    result = simulate_trades(df_low, entries, initial_capital=float(params.get("initial_capital", 1000)))
    result["higher_tf"] = higher_tf
    result["lower_tf"] = lower_tf
    return result

# ========== 憭望?瘛瑕??望嚗?頞典 + 雿??迎? ==========
def backtest_multi_tf_hybrid(symbol: str, higher_tf: str = "1h", lower_tf: str = "15m", limit: int = 1000, params: Optional[Dict[str, Any]] = None, exchange: Optional[Any] = None) -> Dict[str, Any]:
    params = params or {}
    short_window = int(params.get("short_window", 20))
    long_window = int(params.get("long_window", 50))
    rsi_period = int(params.get("rsi_period", 14))
    rsi_upper = float(params.get("rsi_upper", 70))
    rsi_lower = float(params.get("rsi_lower", 30))

    df_high = fetch_ohlcv(symbol, timeframe=higher_tf, limit=limit, exchange=exchange)
    df_low = fetch_ohlcv(symbol, timeframe=lower_tf, limit=limit * 4, exchange=exchange)

    if df_high.empty or df_low.empty:
        return simulate_trades(pd.DataFrame(), [])

    high_trend = trend_strategy(df_high, short_window=short_window, long_window=long_window)
    low_osc = osc_strategy(df_low, period=rsi_period, upper=rsi_upper, lower=rsi_lower)

    hi_map = _align_high_to_low_indices(df_high["timestamp"], df_low["timestamp"])

    entries = []
    for i in range(len(df_low)):
        hi_idx = hi_map[i]
        if hi_idx < 0 or hi_idx >= len(high_trend):
            entries.append(None)
            continue

        hi_sig = high_trend[hi_idx]
        lo_sig = low_osc[i]

        if hi_sig == "up" and lo_sig == "buy":
            entries.append("buy")
        elif hi_sig == "down" and lo_sig == "sell":
            entries.append("sell")
        else:
            entries.append(None)

    result = simulate_trades(df_low, entries, initial_capital=float(params.get("initial_capital", 1000)))
    result["higher_tf"] = higher_tf
    result["lower_tf"] = lower_tf
    return result

# ========== CLI ?舀嚗內靘? ==========
def _parse_params(param_str: Optional[str]) -> Dict[str, Any]:
    if not param_str:
        return {}
    try:
        return json.loads(param_str)
    except Exception:
        # allow key=val;key2=val2 style
        out = {}
        for part in str(param_str).split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out

def main():
    parser = argparse.ArgumentParser(prog="backtester.py", description="Simple backtester utility")
    parser.add_argument("--symbol", type=str, required=False, help="Symbol (e.g. BTC/USDT:USDT)")
    parser.add_argument("--strategy", type=str, default="trend_mix", help="Strategy name")
    parser.add_argument("--tf", "--timeframe", dest="tf", type=str, default="1h", help="Timeframe e.g. 1h, 15m, 5m")
    parser.add_argument("--limit", type=int, default=1000, help="OHLCV fetch limit")
    parser.add_argument("--export_csv", type=str, default=None, help="Export single-result to CSV")
    parser.add_argument("--params", type=str, default=None, help="JSON string or key=val;... params")
    args = parser.parse_args()

    params = _parse_params(args.params)

    if not args.symbol:
        parser.print_help()
        return

    res = backtest(args.symbol, args.strategy, timeframe=args.tf, limit=args.limit, params=params)
    # print summary
    print(json.dumps({
        "symbol": res.get("symbol"),
        "strategy": res.get("strategy"),
        "timeframe": res.get("timeframe"),
        "total_pnl": res.get("total_pnl"),
        "max_drawdown": res.get("max_drawdown"),
        "sharpe_ratio": res.get("sharpe_ratio"),
        "trades": res.get("trades")
    }, ensure_ascii=False, indent=2))

    if args.export_csv:
        # make a tiny csv line with key metrics
        df_out = pd.DataFrame([{
            "symbol": res.get("symbol"),
            "strategy": res.get("strategy"),
            "timeframe": res.get("timeframe"),
            "total_pnl": res.get("total_pnl"),
            "max_drawdown": res.get("max_drawdown"),
            "sharpe_ratio": res.get("sharpe_ratio"),
            "trades": res.get("trades")
        }])
        df_out.to_csv(args.export_csv, index=False)

if __name__ == "__main__":
    main()
# ---------- PATCH START: inserted functions for sim_slippage and sim_delay ----------
import math
def parse_timeframe_to_seconds(tf: str) -> int:
    tf = str(tf).lower().strip()
    if tf.endswith("m"):
        return int(tf[:-1]) * 60
    if tf.endswith("h"):
        return int(tf[:-1]) * 3600
    if tf.endswith("d"):
        return int(tf[:-1]) * 86400
    try:
        return int(tf) * 60
    except Exception:
        return 3600

def simulate_trades(df, signals, initial_capital: float = 1000.0,
                    sim_slippage: float = 0.0, sim_delay: float = 0.0, timeframe: str = "1h"):
    if df is None or df.empty or not signals:
        return {
            "trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "equity_curve": []
        }
    bar_seconds = parse_timeframe_to_seconds(timeframe)
    delay_bars = int(math.ceil(float(sim_delay) / max(1, bar_seconds)))
    capital = float(initial_capital)
    position = 0.0
    equity_curve = []
    trades_count = 0
    prices = [float(x) for x in df["close"].values]
    n = len(prices)
    for i in range(n):
        price = prices[i]
        signal = signals[i] if i < len(signals) else None
        exec_index = min(n - 1, i + delay_bars)
        exec_price_base = prices[exec_index]
        if signal == "buy" and position == 0 and capital > 0:
            exec_price = exec_price_base * (1.0 + float(sim_slippage))
            position = capital / exec_price
            capital = 0.0
            trades_count += 1
        elif signal == "sell" and position > 0:
            exec_price = exec_price_base * (1.0 - float(sim_slippage))
            capital = position * exec_price
            position = 0.0
            trades_count += 1
        equity = capital + position * price
        equity_curve.append(equity)
    total_pnl = equity_curve[-1] - initial_capital if equity_curve else 0.0
    max_dd = calculate_max_drawdown(equity_curve) if equity_curve else 0.0
    sharpe = calculate_sharpe_ratio(equity_curve) if equity_curve else 0.0
    return {
        "trades": int(trades_count),
        "total_pnl": float(total_pnl),
        "max_drawdown": float(max_dd),
        "sharpe_ratio": float(sharpe),
        "equity_curve": equity_curve
    }

def backtest(symbol: str, strategy: str, timeframe: str = "1h", limit: int = 1000,
             params=None, exchange=None):
    params = params or {}
    df = fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, exchange=exchange)
    if df is None or df.empty:
        return simulate_trades(pd.DataFrame(), [], initial_capital=float(params.get("initial_capital", 1000.0)))
    sim_slippage = float(params.get("sim_slippage", 0.0))
    sim_delay = float(params.get("sim_delay", 0.0))
    if strategy == "trend_mix":
        short = int(params.get("short_window", 20))
        long = int(params.get("long_window", 50))
        signals = trend_strategy(df, short_window=short, long_window=long)
    elif strategy == "osc_mix":
        period = int(params.get("rsi_period", 14))
        upper = float(params.get("rsi_upper", 70))
        lower = float(params.get("rsi_lower", 30))
        signals = osc_strategy(df, period=period, upper=upper, lower=lower)
    elif strategy == "hybrid_mix":
        short = int(params.get("short_window", 20))
        long = int(params.get("long_window", 50))
        period = int(params.get("rsi_period", 14))
        upper = float(params.get("rsi_upper", 70))
        lower = float(params.get("rsi_lower", 30))
        signals = hybrid_strategy(df, short_window=short, long_window=long, period=period, upper=upper, lower=lower)
    else:
        short = int(params.get("short_window", 20))
        long = int(params.get("long_window", 50))
        signals = trend_strategy(df, short_window=short, long_window=long)
    result = simulate_trades(df, signals,
                             initial_capital=float(params.get("initial_capital", 1000.0)),
                             sim_slippage=sim_slippage,
                             sim_delay=sim_delay,
                             timeframe=timeframe)
    result["symbol"] = symbol
    result["strategy"] = strategy
    result["timeframe"] = timeframe
    result["params"] = params
    return result
# ---------- PATCH END ----------
