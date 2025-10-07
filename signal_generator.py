import pandas as pd
import numpy as np
import talib

# === 單一指標信號 ===
def signal_macd(df):
    macd, signal, hist = talib.MACD(df['close'], 12, 26, 9)
    return 1 if macd.iloc[-1] > signal.iloc[-1] else -1

def signal_rsi(df, period=14):
    rsi = talib.RSI(df['close'], timeperiod=period)
    if rsi.iloc[-1] < 30: return 1
    if rsi.iloc[-1] > 70: return -1
    return 0

def signal_bollinger(df, period=20, nbdev=2):
    upper, mid, lower = talib.BBANDS(df['close'], timeperiod=period, nbdevup=nbdev, nbdevdn=nbdev)
    if df['close'].iloc[-1] > upper.iloc[-1]: return -1
    if df['close'].iloc[-1] < lower.iloc[-1]: return 1
    return 0

def signal_atr(df, period=14):
    return talib.ATR(df['high'], df['low'], df['close'], timeperiod=period).iloc[-1]

def signal_adx(df, period=14):
    adx = talib.ADX(df['high'], df['low'], df['close'], timeperiod=period)
    return 1 if adx.iloc[-1] > 25 else 0

def signal_stochastic(df, k=14, d=3):
    slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'],
                               fastk_period=k, slowk_period=d, slowd_period=d)
    if slowk.iloc[-1] > slowd.iloc[-1]: return 1
    if slowk.iloc[-1] < slowd.iloc[-1]: return -1
    return 0

def signal_skdj(df, k_period=9, d_period=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=d_period-1).mean()
    d = k.ewm(com=d_period-1).mean()
    return 1 if k.iloc[-1] > d.iloc[-1] else -1

def signal_td(df, length=9):
    count = 0
    for i in range(len(df)-length, len(df)):
        if df['close'].iloc[i] < df['close'].iloc[i-4]:
            count += 1
        else:
            count = 0
    return 1 if count >= length else 0

def signal_roc(df, period=10):
    roc = talib.ROC(df['close'], timeperiod=period)
    return 1 if roc.iloc[-1] > 0 else -1

def signal_mom(df, period=10):
    mom = talib.MOM(df['close'], timeperiod=period)
    return 1 if mom.iloc[-1] > 0 else -1

def signal_stddev(df, period=20):
    return talib.STDDEV(df['close'], timeperiod=period).iloc[-1]

def signal_obv(df):
    obv = talib.OBV(df['close'], df['volume'])
    return 1 if obv.iloc[-1] > obv.iloc[-2] else -1

def signal_vwap(df):
    vwap = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    return 1 if df['close'].iloc[-1] > vwap.iloc[-1] else -1

def signal_ichimoku(df):
    high9 = df['high'].rolling(9).max()
    low9 = df['low'].rolling(9).min()
    tenkan = (high9 + low9) / 2
    high26 = df['high'].rolling(26).max()
    low26 = df['low'].rolling(26).min()
    kijun = (high26 + low26) / 2
    return 1 if tenkan.iloc[-1] > kijun.iloc[-1] else -1

def signal_kama(df, period=10):
    kama = talib.KAMA(df['close'], timeperiod=period)
    return 1 if df['close'].iloc[-1] > kama.iloc[-1] else -1

# === 多週期信號生成 ===
def generate_signal(dfs: dict):
    """
    dfs: dict { "1m": df, "15m": df, "1h": df, "4h": df, "1d": df }
    return: dict of signals
    """
    sigs = {}

    # 短週期 (1m)
    df = dfs["1m"]
    sigs["macd"] = signal_macd(df)
    sigs["rsi"] = signal_rsi(df)
    sigs["boll"] = signal_bollinger(df)
    sigs["skdj"] = signal_skdj(df)
    sigs["td9"] = signal_td(df, 9)
    sigs["td13"] = signal_td(df, 13)
    sigs["atr"] = signal_atr(df)
    sigs["adx"] = signal_adx(df)
    sigs["stoch"] = signal_stochastic(df)
    sigs["roc"] = signal_roc(df)
    sigs["mom"] = signal_mom(df)
    sigs["stddev"] = signal_stddev(df)
    sigs["obv"] = signal_obv(df)
    sigs["vwap"] = signal_vwap(df)
    sigs["ichimoku"] = signal_ichimoku(df)
    sigs["kama"] = signal_kama(df)

    # 中週期 (15m, 1h, 4h, 1d)
    for tf in ["15m", "1h", "4h", "1d"]:
        if tf in dfs:
            sigs[f"macd_{tf}"] = signal_macd(dfs[tf])
            sigs[f"rsi_{tf}"] = signal_rsi(dfs[tf])
            sigs[f"adx_{tf}"] = signal_adx(dfs[tf])

    return sigs