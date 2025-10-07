import numpy as np

def ai_predict_trend(symbol, timeframe):
    # Stub: 用 EMA 判斷 + 隨機信心
    signal = "bullish" if np.random.rand() > 0.5 else "bearish"
    confidence = np.random.rand()
    return signal, confidence