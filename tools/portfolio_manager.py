# portfolio_manager.py
import json
from pathlib import Path

# === 設定 ===
MAX_POSITIONS = 10
PORTFOLIO_FILE = Path(__file__).parent / "portfolio.json"

# === 初始化投資組合檔案 ===
def init_portfolio():
    if not PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump({"positions": {}}, f)

# === 讀取投資組合 ===
def load_portfolio():
    init_portfolio()
    with open(PORTFOLIO_FILE, "r") as f:
        return json.load(f)

# === 儲存投資組合 ===
def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)

# === 檢查是否能開新倉 ===
def can_open_new(symbol):
    portfolio = load_portfolio()
    positions = portfolio["positions"]

    if symbol in positions:
        return True  # 已持有該幣，可以加倉或平倉

    if len(positions) < MAX_POSITIONS:
        return True  # 還沒滿 10 檔，可以新增

    return False  # 已滿 10 檔，不能新增

# === 新增/更新持倉 ===
def add_position(symbol, qty, entry_price):
    portfolio = load_portfolio()
    portfolio["positions"][symbol] = {
        "qty": qty,
        "entry_price": entry_price,
        "high_watermark": entry_price  # 初始化最高價
    }
    save_portfolio(portfolio)

# === 更新最高價 (用於移動停損/停利) ===
def update_high(symbol, price):
    portfolio = load_portfolio()
    if symbol in portfolio["positions"]:
        if price > portfolio["positions"][symbol]["high_watermark"]:
            portfolio["positions"][symbol]["high_watermark"] = price
            save_portfolio(portfolio)

# === 平倉 ===
def close_position(symbol):
    portfolio = load_portfolio()
    if symbol in portfolio["positions"]:
        del portfolio["positions"][symbol]
        save_portfolio(portfolio)

# === 查詢目前持倉 ===
def list_positions():
    portfolio = load_portfolio()
    return portfolio["positions"]

if __name__ == "__main__":
    init_portfolio()
    print("目前持倉:", list_positions())
    add_position("BTCUSDT", 0.01, 27000)
    print("新增後持倉:", list_positions())
    update_high("BTCUSDT", 28000)
    print("更新最高價:", list_positions())
    close_position("BTCUSDT")
    print("平倉後持倉:", list_positions())