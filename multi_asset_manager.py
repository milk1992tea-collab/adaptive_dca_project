import ccxt
import json
import random

# === 初始化交易所 (Binance) ===
exchange = ccxt.binance({
    "enableRateLimit": True
})

# === 抓取成交額前 50 幣種 ===
def get_top_50_symbols():
    tickers = exchange.fetch_tickers()
    # 計算成交額 = close * quoteVolume
    volumes = []
    for symbol, data in tickers.items():
        if "/USDT" in symbol:  # 只取 USDT 交易對
            try:
                vol = data["quoteVolume"]
                volumes.append((symbol, vol))
            except:
                continue
    # 排序取前 50
    top50 = sorted(volumes, key=lambda x: x[1], reverse=True)[:50]
    return [s[0] for s in top50]

# === 模擬績效評分 (未來可替換成回測結果) ===
def score_symbols(symbols):
    scored = [(s, random.random()) for s in symbols]  # 0~1 隨機分數
    top10 = sorted(scored, key=lambda x: x[1], reverse=True)[:10]
    return [s[0] for s in top10]

# === 更新 config.json ===
def update_config(selected_symbols):
    config_path = "C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    config["symbols"] = selected_symbols  # 新增 symbols 欄位

    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

    print("✅ 已更新 config.json，選出幣種：", selected_symbols)

# === 主程式 ===
if __name__ == "__main__":
    top50 = get_top_50_symbols()
    print("📊 成交額前 50 幣種：", top50)

    selected = score_symbols(top50)
    print("🏆 選出前 10 幣種：", selected)

    update_config(selected)