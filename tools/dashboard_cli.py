# dashboard_cli.py (加強版：自訂事件觸發通知)
import json
import time
import os
import csv
import threading
import requests
from pathlib import Path
from datetime import datetime
from binance.client import Client
import matplotlib.pyplot as plt
from collections import deque

CONFIG_FILE = Path(__file__).parent / "config.json"
LOG_FILE = Path(__file__).parent / "dashboard_log.csv"

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
REFRESH_INTERVAL = 10
MAX_POINTS = 50
PNL_ALERT_THRESHOLD = 50  # 超過 ±50 USDT 就推播

# Telegram Bot 設定 (請填入你自己的 Token 和 Chat ID)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# 自訂事件條件 (symbol, operator, price, message)
CUSTOM_EVENTS = [
    {"symbol": "BTCUSDT", "operator": "<", "price": 100000, "message": "⚠️ BTC 跌破 100,000 USDT"},
    {"symbol": "ETHUSDT", "operator": ">", "price": 5000, "message": "🚀 ETH 漲破 5,000 USDT"},
]

# 用 deque 儲存即時數據
price_history = {s: deque(maxlen=MAX_POINTS) for s in SYMBOLS}
pnl_history = {s: deque(maxlen=MAX_POINTS) for s in SYMBOLS}
time_history = deque(maxlen=MAX_POINTS)

latest_tickers = {}
latest_pnl_data = {}
last_order_ids = set()
lock = threading.Lock()

def load_keys():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        return cfg.get("API_KEY"), cfg.get("API_SECRET")
    else:
        raise FileNotFoundError("找不到 config.json")

def init_csv():
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["timestamp"]
            for symbol in SYMBOLS:
                header += [f"{symbol}_price", f"{symbol}_position", f"{symbol}_avg_price", f"{symbol}_pnl"]
            writer.writerow(header)

def telegram_notify(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    except Exception as e:
        print("⚠️ Telegram 推播失敗:", e)

def fetch_tickers(client):
    return {s: float(client.get_symbol_ticker(symbol=s)["price"]) for s in SYMBOLS}

def fetch_portfolio(client):
    account_info = client.get_account()
    balances = account_info["balances"]
    return {b["asset"]: float(b["free"]) + float(b["locked"]) for b in balances if float(b["free"]) > 0 or float(b["locked"]) > 0}

def calc_pnl(client, tickers, portfolio):
    pnl_data = {}
    for symbol in SYMBOLS:
        base = symbol.replace("USDT", "")
        if base not in portfolio or portfolio[base] == 0:
            pnl_data[symbol] = (0, 0, 0)
            continue

        trades = client.get_my_trades(symbol=symbol, limit=50)
        buys = [t for t in trades if t["isBuyer"]]
        if not buys:
            pnl_data[symbol] = (portfolio[base], 0, 0)
            continue

        total_qty = sum(float(t["qty"]) for t in buys)
        total_cost = sum(float(t["qty"]) * float(t["price"]) for t in buys)
        avg_price = total_cost / total_qty if total_qty > 0 else 0

        current_price = tickers[symbol]
        position_size = portfolio[base]
        pnl = position_size * (current_price - avg_price)

        pnl_data[symbol] = (position_size, avg_price, pnl)
    return pnl_data

def log_to_csv(tickers, pnl_data):
    row = [datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")]
    for symbol in SYMBOLS:
        price = tickers.get(symbol, 0)
        pos, avg, pnl = pnl_data.get(symbol, (0, 0, 0))
        row += [price, pos, avg, pnl]
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def check_custom_events(tickers):
    for event in CUSTOM_EVENTS:
        symbol, op, price, msg = event["symbol"], event["operator"], event["price"], event["message"]
        current_price = tickers.get(symbol, 0)
        if op == "<" and current_price < price:
            telegram_notify(msg + f" (現價 {current_price})")
        elif op == ">" and current_price > price:
            telegram_notify(msg + f" (現價 {current_price})")

def cli_loop(client):
    global latest_tickers, latest_pnl_data, last_order_ids
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=== 📊 Binance Testnet Dashboard (CLI + Chart + Telegram + Events) ===")

        tickers = fetch_tickers(client)
        portfolio = fetch_portfolio(client)
        pnl_data = calc_pnl(client, tickers, portfolio)
        log_to_csv(tickers, pnl_data)

        # CLI 輸出
        print("\n💹 即時行情：")
        for s in SYMBOLS:
            print(f"  {s}: {tickers[s]}")
        print("\n📈 浮動盈虧 (PnL)：")
        for s in SYMBOLS:
            pos, avg, pnl = pnl_data[s]
            print(f"  {s}: 持倉={pos:.6f}, 平均買入價={avg:.2f}, 現價={tickers[s]:.2f}, PnL={pnl:.2f} USDT")
            if abs(pnl) >= PNL_ALERT_THRESHOLD:
                telegram_notify(f"⚠️ {s} PnL 達到 {pnl:.2f} USDT (持倉 {pos:.6f})")

        # 檢查自訂事件
        check_custom_events(tickers)

        with lock:
            latest_tickers = tickers
            latest_pnl_data = pnl_data

        print(f"\n⏳ {REFRESH_INTERVAL} 秒後刷新 (Ctrl+C 停止)")
        time.sleep(REFRESH_INTERVAL)

def chart_loop():
    plt.ion()
    while True:
        with lock:
            if not latest_tickers or not latest_pnl_data:
                time.sleep(1)
                continue
            now = datetime.utcnow().strftime("%H:%M:%S")
            time_history.append(now)
            for s in SYMBOLS:
                price_history[s].append(latest_tickers[s])
                pnl_history[s].append(latest_pnl_data[s][2])

        plt.clf()
        plt.subplot(2, 1, 1)
        for s in SYMBOLS:
            plt.plot(time_history, price_history[s], label=f"{s} Price")
        plt.title("即時價格")
        plt.legend()
        plt.xticks(rotation=45)

        plt.subplot(2, 1, 2)
        for s in SYMBOLS:
            plt.plot(time_history, pnl_history[s], label=f"{s} PnL")
        plt.title("浮動盈虧 (PnL)")
        plt.legend()
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.pause(0.05)

def main():
    api_key, api_secret = load_keys()
    client = Client(api_key, api_secret)
    client.API_URL = 'https://testnet.binance.vision/api'
    init_csv()

    t1 = threading.Thread(target=cli_loop, args=(client,), daemon=True)
    t2 = threading.Thread(target=chart_loop, daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 已停止 Dashboard 監控")

if __name__ == "__main__":
    main()