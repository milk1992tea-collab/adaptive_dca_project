# trader.py
from pathlib import Path
import numpy as np
from filters import multi_timeframe_filter, breakout_filter
from data_pipeline import build_dataset
from strategy_triggers import evaluate_signals

# Binance API
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET

# === 初始化 Binance Testnet API ===
# 請在 config.json 或環境變數裡存放 API_KEY / API_SECRET
import os, json

CONFIG_FILE = Path(__file__).parent / "config.json"
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    API_KEY = cfg.get("API_KEY")
    API_SECRET = cfg.get("API_SECRET")
else:
    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_API_SECRET")

client = None
if API_KEY and API_SECRET:
    client = Client(API_KEY, API_SECRET, testnet=True)  # 使用 Testnet

# === 工具函數 ===
def _estimate_volatility(df):
    ret = df["close"].pct_change()
    return ret.rolling(20).std(ddof=0)

def _estimate_dollar_volume(df):
    if "quote_volume" in df.columns:
        return df["quote_volume"].rolling(20).mean()
    elif "volume" in df.columns:
        return (df["close"] * df["volume"]).rolling(20).mean()
    else:
        return df["close"].rolling(20).mean()

def _dynamic_order_size(df_short, balance, params):
    vol = _estimate_volatility(df_short).iloc[-1]
    dv = _estimate_dollar_volume(df_short).iloc[-1]

    vol_series = _estimate_volatility(df_short).fillna(method="bfill").fillna(0)
    dv_series = _estimate_dollar_volume(df_short).fillna(method="bfill").fillna(0)

    vol_norm = 1.0 - (vol / (vol_series.max() + 1e-9))
    dv_norm = dv / (dv_series.max() + 1e-9)

    alpha = params.get("alloc_alpha", 0.5)
    score = alpha * dv_norm + (1 - alpha) * vol_norm

    target_pct = params.get("dynamic_target_pct", 0.05)
    cap_pct = params.get("dynamic_cap_pct", 0.20)
    pct = min(score * target_pct * 2.0, cap_pct)

    return max(pct * balance, 10)

# === 主交易函數 ===
def trade_once(symbol, params, usdt_budget, dry_run=True,
               stop_loss=0.95, take_profit=1.05, trailing_stop=0.05):

    # 短週期 (5m)
    df_short = build_dataset(symbol, "5m", 500)
    signals = evaluate_signals(df_short, params)
    signal = signals[-1]

    # 長週期 (1h)
    df_long = build_dataset(symbol, "1h", 500)

    # 過濾條件
    if params.get("use_multi_timeframe", 1) == 1:
        if not multi_timeframe_filter(df_short, df_long, signal):
            return {"status": "skip", "symbol": symbol, "reason": "多週期不一致"}

    if params.get("use_breakout_filter", 0) == 1:
        if not breakout_filter(df_short, signal):
            return {"status": "skip", "symbol": symbol, "reason": "未突破布林通道"}

    # 資金分配策略
    balance = params.get("account_balance", 1000)
    if params.get("allocation_mode", 0) == 0:
        order_size = params.get("allocation_value", 0.05) * 1000
    else:
        base_size = balance * params.get("allocation_value", 0.05)
        if params.get("use_dynamic_allocation", 1) == 1:
            dyn_size = _dynamic_order_size(df_short, balance, params)
            order_size = min(base_size, dyn_size)
        else:
            order_size = base_size

    price = df_short["close"].iloc[-1]
    qty = max(order_size / price, 0)

    # === 下單 ===
    if signal in ("LONG", "SHORT"):
        if dry_run or client is None:
            return {
                "status": "executed",
                "mode": "dry_run",
                "symbol": symbol,
                "side": signal,
                "price": price,
                "qty": qty,
                "reason": "模擬下單",
                "allocation_mode": "固定金額" if params.get("allocation_mode", 0) == 0 else "固定比例",
                "allocation_value": params.get("allocation_value", 0.05),
                "use_dynamic_allocation": params.get("use_dynamic_allocation", 1),
            }
        else:
            try:
                side = SIDE_BUY if signal == "LONG" else SIDE_SELL
                order = client.create_order(
                    symbol=symbol,
                    side=side,
                    type=ORDER_TYPE_MARKET,
                    quantity=round(qty, 6)  # 保留小數位
                )
                return {
                    "status": "executed",
                    "mode": "real_order",
                    "symbol": symbol,
                    "side": signal,
                    "price": price,
                    "qty": qty,
                    "reason": "實單下單成功",
                    "binance_order_id": order["orderId"],
                    "allocation_mode": "固定金額" if params.get("allocation_mode", 0) == 0 else "固定比例",
                    "allocation_value": params.get("allocation_value", 0.05),
                    "use_dynamic_allocation": params.get("use_dynamic_allocation", 1),
                }
            except Exception as e:
                return {"status": "error", "symbol": symbol, "error": str(e)}
    else:
        return {"status": "skip", "symbol": symbol, "reason": "無明確訊號"}