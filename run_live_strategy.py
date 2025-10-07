import json
import time
import csv
from typing import Dict, Any
from data_fetch import fetch_multi_timeframes
from bybit_utils import open_position, close_position, get_position, get_balance
from signal_generator import generate_signal
from strategies import run_strategy

BEST_PATH = "best_params.json"
SELECTED_PATH = "selected_strategy.json"
LOG_PATH = "live_trades.csv"

def load_params() -> Dict[str, Any]:
    """優先讀取 selected_strategy.json，否則退回 best_params.json"""
    try:
        with open(SELECTED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("params", {})
    except Exception:
        try:
            with open(BEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("params", {})
        except Exception:
            return {}

def append_log(row: Dict[str, Any]):
    header = ["timestamp", "action", "symbol", "price", "qty", "note"]
    try:
        file_exists = False
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as fr:
                file_exists = True
        except Exception:
            file_exists = False

        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception:
        pass

def run_live(symbol="BTCUSDT"):
    params = load_params()
    if not params:
        params = {
            "step": 5.0,
            "base_qty": 5.0,
            "take_profit_pct": 0.05,
            "stop_loss_pct": -0.03,
            "strategy": "trend_mix"
        }

    step = float(params["step"])
    base_qty = float(params["base_qty"])
    tp_pct = float(params.get("take_profit_pct", 0.05))
    sl_pct = float(params.get("stop_loss_pct", -0.03))
    strategy_name = params.get("strategy", "trend_mix")

    print(f"=== 模擬開始 (策略: {strategy_name}) ===")
    get_balance(accountType="UNIFIED")

    last_buy_price = None
    entry_price = None
    position_usdt = 0.0
    max_position_usdt = 1000.0

    dfs = fetch_multi_timeframes(symbol, limit=1000)
    df_1m = dfs["1m"]

    for i in range(len(df_1m)):
        ts = int(time.time())
        price = df_1m["close"].iloc[i]

        dfs_slice = {
            "1m": df_1m.iloc[:i+1],
            "15m": dfs["15m"].iloc[:i//15+1],
            "1h": dfs["1h"].iloc[:i//60+1],
            "4h": dfs["4h"].iloc[:i//240+1],
            "1d": dfs["1d"].iloc[:i//1440+1],
        }

        sigs = generate_signal(dfs_slice)
        decision = run_strategy(strategy_name, sigs)

        # === 加倉 ===
        if (last_buy_price is None or price <= last_buy_price - step) and decision == 1:
            if position_usdt + base_qty <= max_position_usdt:
                qty = round(base_qty / price, 3)
                open_position(symbol, str(qty), side="Buy", category="linear")
                position_usdt += base_qty
                last_buy_price = price
                if entry_price is None:
                    entry_price = price
                append_log({"timestamp": ts, "action": "BUY", "symbol": symbol,
                            "price": price, "qty": base_qty, "note": strategy_name})
                print(f"[{i}] BUY {base_qty} USDT @ {price:.2f}")
            else:
                print(f"[{i}] 持倉達上限，跳過加倉")

        # === 止盈/止損 ===
        if entry_price and position_usdt > 0:
            pnl_pct = (price - entry_price) / entry_price
            if pnl_pct >= tp_pct or pnl_pct <= sl_pct:
                action = "SELL_TP" if pnl_pct >= tp_pct else "SELL_SL"
                qty = round(position_usdt / price, 3)
                close_position(symbol, str(qty), side="Sell", category="linear")
                append_log({"timestamp": ts, "action": action, "symbol": symbol,
                            "price": price, "qty": position_usdt, "note": f"{pnl_pct:.4f}"})
                print(f"[{i}] {action} 全平 {position_usdt} USDT @ {price:.2f} (PnL {pnl_pct*100:.2f}%)")
                position_usdt, entry_price, last_buy_price = 0.0, None, None

        time.sleep(2)

    print("\n=== 模擬結束 ===")
    get_position(symbol, category="linear")
    get_balance(accountType="UNIFIED")

if __name__ == "__main__":
    run_live("BTCUSDT")