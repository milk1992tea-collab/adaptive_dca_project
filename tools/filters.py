# filters.py
import pandas as pd

def multi_timeframe_filter(df_short: pd.DataFrame, df_long: pd.DataFrame, signal: str) -> bool:
    """
    多週期過濾器：
    - 只有當短週期訊號與長週期趨勢一致時才通過
    - signal: "LONG" / "SHORT" / "NONE"
    """
    if signal == "LONG":
        return df_long["ema20"].iloc[-1] > df_long["ema50"].iloc[-1]
    elif signal == "SHORT":
        return df_long["ema20"].iloc[-1] < df_long["ema50"].iloc[-1]
    return False

def breakout_filter(df: pd.DataFrame, signal: str) -> bool:
    """
    突破過濾器：
    - LONG: 收盤價突破布林上軌
    - SHORT: 收盤價跌破布林下軌
    """
    close = df["close"].iloc[-1]
    bb_upper = df["bb_upper"].iloc[-1]
    bb_lower = df["bb_lower"].iloc[-1]

    if signal == "LONG" and close > bb_upper:
        return True
    elif signal == "SHORT" and close < bb_lower:
        return True
    return False