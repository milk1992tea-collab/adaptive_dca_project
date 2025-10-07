# main.py
import time, csv, json
from pathlib import Path
from market_scanner import scan_market
import trader
import portfolio_manager as pm

# === 全域設定 ===
SCAN_INTERVAL = 300  # 每 5 分鐘掃描一次
USDT_BUDGET = 50     # 單筆下單金額 (僅在 allocation_mode=0 時使用)
DRY_RUN = True       # True=模擬, False=實單

# 預設參數 (若 best_params.json 沒有，才用這些)
DEFAULT_PARAMS = {
    "rsi_buy": 30,
    "kdj_buy": 30,
    "rsi_sell": 70,
    "kdj_sell": 70,
    "td_trigger": 9,
    "stop_loss": 0.95,
    "take_profit": 1.05,
    "trailing_stop": 0.05,
    "use_multi_timeframe": 1,
    "use_breakout": 1,
    "allocation_mode": 0,     # 0=固定金額, 1=固定比例
    "allocation_value": 0.05  # 0.05=50 USDT 或 5%
}

# 檔案路徑
BEST_PARAMS_FILE = Path(__file__).parent / "best_params.json"
LOG_FILE = Path(__file__).parent / "log.csv"

def load_best_params():
    """讀取 Optuna 儲存的最佳參數"""
    if BEST_PARAMS_FILE.exists():
        with open(BEST_PARAMS_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_PARAMS

def log_trade(result):
    """把交易結果寫入 CSV"""
    headers = [
        "time", "status", "symbol", "side", "price", "qty", "reason",
        "allocation_mode", "allocation_value"
    ]
    write_header = not LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if write_header:
            writer.writeheader()
        row = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": result.get("status"),
            "symbol": result.get("symbol"),
            "side": result.get("side", ""),
            "price": result.get("price", ""),
            "qty": result.get("qty", ""),
            "reason": result.get("reason", ""),
            "allocation_mode": result.get("allocation_mode", ""),
            "allocation_value": result.get("allocation_value", "")
        }
        writer.writerow(row)

def run_cycle():
    print("=== 開始市場掃描 ===")
    market = scan_market(50)

    # 載入最佳參數
    params = load_best_params()
    print("使用參數:", params)

    # 現貨 + 永續合約
    symbols = list(market["spot"]["symbol"]) + list(market["futures"]["symbol"])

    for symbol in symbols:
        print(f"\n檢查標的: {symbol}")
        result = trader.trade_once(
            symbol=symbol,
            params=params,
            usdt_budget=USDT_BUDGET,
            dry_run=DRY_RUN,
            stop_loss=params["stop_loss"],
            take_profit=params["take_profit"],
            trailing_stop=params["trailing_stop"]
        )
        print("交易結果:", result)
        log_trade(result)

    print("\n=== 當前持倉 ===")
    print(pm.list_positions())

if __name__ == "__main__":
    while True:
        run_cycle()
        print(f"\n等待 {SCAN_INTERVAL} 秒後再次掃描...\n")
        time.sleep(SCAN_INTERVAL)