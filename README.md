# AdaptiveDCA-AI

一個結合 Optuna + AI + DCA 的自我進化交易系統骨架。

## 快速開始

1. 在 `config/platforms.json` 填入 Binance & OKX 的 API 金鑰。  
2. 把你的 5m/4h OHLCV CSV 放到 `data/ohlcv/5m/` 與 `data/ohlcv/4h/`。  
3. 放入 `data/volume_24h.csv` 或確認 Binance API 可正常抓到成交額。  
4. 安裝套件：