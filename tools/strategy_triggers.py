# strategy_triggers.py
import numpy as np
import pandas as pd

"""
需求假設：
- build_dataset 產出的 df 具備至少欄位：close, high, low, volume
- 若已有指標欄位（ema20, ema50, bb_upper, bb_lower, rsi, kdj_*），本模組會直接使用；
- 若缺少欄位，會在本模組中以簡化版計算最基本指標。

本模組提供 evaluate_signals(df, params)：
- 內含三種策略：breakout（突破）、mean_reversion（均值回歸）、trend_follow（趨勢跟隨）
- 以加權投票融合成單一訊號：LONG / SHORT / NONE
- 權重、啟用策略、投票模式由 params 控制
"""

def _ensure_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # EMA 20/50
    if "ema20" not in df.columns:
        df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    if "ema50" not in df.columns:
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # 布林通道（20期）
    if "bb_upper" not in df.columns or "bb_lower" not in df.columns:
        m = df["close"].rolling(20).mean()
        s = df["close"].rolling(20).std(ddof=0)
        df["bb_upper"] = m + 2 * s
        df["bb_lower"] = m - 2 * s

    # RSI（14）
    if "rsi" not in df.columns:
        delta = df["close"].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        rs = up.rolling(14).mean() / (down.rolling(14).mean() + 1e-9)
        df["rsi"] = 100 - (100 / (1 + rs))

    # KDJ（簡化版）
    if not {"kdj_k","kdj_d","kdj_j"}.issubset(df.columns):
        low_n = df["low"].rolling(9).min()
        high_n = df["high"].rolling(9).max()
        rsv = (df["close"] - low_n) / (high_n - low_n + 1e-9) * 100
        k = rsv.ewm(alpha=1/3).mean()
        d = k.ewm(alpha=1/3).mean()
        j = 3 * k - 2 * d
        df["kdj_k"], df["kdj_d"], df["kdj_j"] = k, d, j

    # 波動率（年化簡化）：用 20 期報酬標準差近似
    if "volatility" not in df.columns:
        ret = df["close"].pct_change()
        df["volatility"] = ret.rolling(20).std(ddof=0) * np.sqrt(252*24*12)  # 5m近似年化

    return df

# --- 單一策略訊號（每根K線回傳 "LONG"/"SHORT"/"NONE"） ---

def breakout_signals(df: pd.DataFrame, params: dict) -> list:
    """布林通道突破"""
    sigs = []
    for i in range(len(df)):
        c = df["close"].iloc[i]
        up = df["bb_upper"].iloc[i]
        lo = df["bb_lower"].iloc[i]
        if pd.isna(up) or pd.isna(lo):
            sigs.append("NONE")
            continue
        if c > up:
            sigs.append("LONG")
        elif c < lo:
            sigs.append("SHORT")
        else:
            sigs.append("NONE")
    return sigs

def mean_reversion_signals(df: pd.DataFrame, params: dict) -> list:
    """均值回歸：RSI 超買/超賣 + 乖離"""
    rsi_buy = params.get("rsi_buy", 30)
    rsi_sell = params.get("rsi_sell", 70)
    ema = df["ema20"]
    sigs = []
    for i in range(len(df)):
        c = df["close"].iloc[i]
        r = df["rsi"].iloc[i]
        e = ema.iloc[i]
        if pd.isna(r) or pd.isna(e):
            sigs.append("NONE")
            continue
        # 過度低估 → LONG；過度高估 → SHORT
        if r <= rsi_buy and c < e * 0.995:
            sigs.append("LONG")
        elif r >= rsi_sell and c > e * 1.005:
            sigs.append("SHORT")
        else:
            sigs.append("NONE")
    return sigs

def trend_follow_signals(df: pd.DataFrame, params: dict) -> list:
    """趨勢跟隨：EMA20/EMA50 多空"""
    sigs = []
    for i in range(len(df)):
        e20 = df["ema20"].iloc[i]
        e50 = df["ema50"].iloc[i]
        if pd.isna(e20) or pd.isna(e50):
            sigs.append("NONE")
            continue
        if e20 > e50:
            sigs.append("LONG")
        elif e20 < e50:
            sigs.append("SHORT")
        else:
            sigs.append("NONE")
    return sigs

# --- 融合邏輯 ---

def _vote(s_list: list[str], weights: list[float], mode: str = "weighted") -> str:
    """
    mode:
      - "weighted": LONG/SHORT 加權，NONE=0
      - "majority": 多數決（權重僅作為平票打破）
    """
    if len(s_list) == 0:
        return "NONE"

    if mode == "majority":
        long_w = sum(w for s, w in zip(s_list, weights) if s == "LONG")
        short_w = sum(w for s, w in zip(s_list, weights) if s == "SHORT")
        if long_w > short_w and long_w > 0:
            return "LONG"
        if short_w > long_w and short_w > 0:
            return "SHORT"
        return "NONE"

    # weighted
    score = 0.0
    for s, w in zip(s_list, weights):
        if s == "LONG":
            score += w
        elif s == "SHORT":
            score -= w
    if score > 1e-9:
        return "LONG"
    elif score < -1e-9:
        return "SHORT"
    return "NONE"

def evaluate_signals(df: pd.DataFrame, params: dict) -> list:
    """
    產生融合後的訊號序列。
    params 控制：
      - use_breakout, use_mean_reversion, use_trend_follow: 0/1
      - weight_breakout, weight_mean, weight_trend: 浮點
      - vote_mode: "weighted" / "majority"
    """
    df = _ensure_indicators(df)

    use_breakout = params.get("use_breakout", 1)
    use_mean = params.get("use_mean_reversion", 1)
    use_trend = params.get("use_trend_follow", 1)

    weight_breakout = params.get("weight_breakout", 1.0)
    weight_mean = params.get("weight_mean", 1.0)
    weight_trend = params.get("weight_trend", 1.0)

    vote_mode = params.get("vote_mode", "weighted")

    # 建立各策略序列
    series = []
    weights = []

    if use_breakout == 1:
        series.append(breakout_signals(df, params))
        weights.append(weight_breakout)

    if use_mean == 1:
        series.append(mean_reversion_signals(df, params))
        weights.append(weight_mean)

    if use_trend == 1:
        series.append(trend_follow_signals(df, params))
        weights.append(weight_trend)

    # 若沒有任何策略啟用
    if len(series) == 0:
        return ["NONE"] * len(df)

    # 逐根投票融合
    fused = []
    for i in range(len(df)):
        votes = [s[i] for s in series]
        fused.append(_vote(votes, weights, mode=vote_mode))

    return fused