# config.py

# 可用策略清單（對齊 diagnose.py 的策略分派）
STRATEGIES = [
    "trend_mix",
    "osc_mix",
    "hybrid_mix",
    "multi_tf_trend",
    "multi_tf_hybrid",
]

# 單一週期回測用的時間框（multi_tf_* 由 MULTI_TF_CONFIG 控制）
TIMEFRAMES = ["1h", "4h"]

# 參數網格：未來可接入各策略（目前 diagnose.py 先傳遞占位）
PARAM_GRID = {
    "short_window": [10, 20],
    "long_window": [50, 100],
    "rsi_period": [14],
    "rsi_upper": [70],
    "rsi_lower": [30],
}

# 多週期配置（高/低週期）
MULTI_TF_CONFIG = {
    "higher_tf": "4h",
    "lower_tf": "15m",
}