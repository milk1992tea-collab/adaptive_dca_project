# auto_trader.py
import json
from pathlib import Path
from binance.client import Client

CONFIG_FILE = Path(__file__).parent.parent / "tools" / "config.json"
PARAMS_FILE = Path(__file__).parent.parent / "configs" / "strategy_params.json"

def load_keys():
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    return cfg["API_KEY"], cfg["API_SECRET"]

def load_params():
    with open(PARAMS_FILE, "r") as f:
        return json.load(f)

def main():
    api_key, api_secret = load_keys()
    client = Client(api_key, api_secret)
    client.API_URL = "https://testnet.binance.vision/api"

    params = load_params()
    symbol = params["symbol"]
    position_size = params["position_size"]

    ticker = float(client.get_symbol_ticker(symbol=symbol)["price"])
    print(f"現價 {symbol}: {ticker}")

    # 簡單範例：當價格低於某條件就買
    if ticker < 100000:  # 這裡用固定條件，實際應用用 params["buy_threshold"]
        order = client.create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=position_size
        )
        print("✅ 已下單:", order)

if __name__ == "__main__":
    main()