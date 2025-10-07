from signal_combiner import combine_signals_rule, combine_signals_weight

# === 策略配置表 ===
STRATEGY_CONFIGS = {
    # 趨勢追隨型：用趨勢指標為核心
    "trend_mix": {
        "mode": "weight",
        "weights": {
            "adx": 0.3,       # 趨勢強度
            "macd": 0.3,      # 趨勢方向
            "atr": 0.2,       # 波動率過濾
            "obv": 0.2        # 成交量確認
        },
        "threshold": 0.25
    },

    # 震盪反轉型：用震盪指標為核心
    "osc_mix": {
        "mode": "weight",
        "weights": {
            "rsi": 0.3,       # 超買超賣
            "stoch": 0.3,     # 隨機震盪
            "boll": 0.2,      # 布林帶上下軌
            "roc": 0.2        # 價格動能
        },
        "threshold": 0.2
    },

    # 混合型：多維度均衡
    "hybrid_mix": {
        "mode": "weight",
        "weights": {
            "adx": 0.2,       # 趨勢
            "rsi": 0.2,       # 震盪
            "mom": 0.2,       # 動能
            "stddev": 0.2,    # 波動
            "vwap": 0.2       # 成交量加權
        },
        "threshold": 0.2
    }
}

def run_strategy(strategy_name, sigs):
    cfg = STRATEGY_CONFIGS.get(strategy_name)
    if not cfg:
        raise ValueError(f"未知策略: {strategy_name}")

    if cfg["mode"] == "rule":
        return combine_signals_rule(sigs, cfg["ruleset"])
    elif cfg["mode"] == "weight":
        return combine_signals_weight(sigs, cfg["weights"], cfg["threshold"])
    else:
        return 0