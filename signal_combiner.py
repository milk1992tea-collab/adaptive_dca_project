from signal_generator import (
    signal_macd, signal_rsi, signal_bollinger, signal_atr, signal_adx,
    signal_stochastic, signal_skdj, signal_td, signal_roc, signal_mom,
    signal_stddev, signal_obv, signal_vwap, signal_ichimoku, signal_kama
)

# === 技術指標分類 ===
TREND_INDICATORS = ["sma", "ema", "wma", "adx", "macd", "ichimoku", "kama"]
OSCILLATORS = ["rsi", "stoch", "skdj", "td9", "td13"]
MOMENTUM = ["roc", "mom"]
VOLATILITY = ["boll", "atr", "stddev"]
VOLUME = ["obv", "vwap"]

# === 規則模式 ===
def combine_signals_rule(sigs, ruleset):
    """
    sigs: dict, 各指標信號
    ruleset: list of tuples, 例如 [("macd",1), ("rsi",1)]
    return: 1=Buy, -1=Sell, 0=Hold
    """
    for ind, val in ruleset:
        if sigs.get(ind, 0) != val:
            return 0
    return 1 if all(v == 1 for _, v in ruleset) else -1

# === 權重模式 ===
def combine_signals_weight(sigs, weights, threshold=0.5):
    """
    sigs: dict, 各指標信號
    weights: dict, 例如 {"macd":0.3, "rsi":0.2, "adx":0.5}
    threshold: 分數閾值
    """
    score = 0
    total = sum(weights.values())
    for ind, w in weights.items():
        score += sigs.get(ind, 0) * w
    score = score / total if total > 0 else 0
    if score >= threshold: return 1
    if score <= -threshold: return -1
    return 0

# === 自動生成組合 (避免重複趨勢類) ===
def generate_combinations():
    combos = []
    for trend in TREND_INDICATORS:
        for osc in OSCILLATORS:
            for mom in MOMENTUM:
                for vol in VOLATILITY:
                    for volu in VOLUME:
                        combos.append([trend, osc, mom, vol, volu])
    return combos