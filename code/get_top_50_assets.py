from .binance_api import fetch_24h_volume

def get_top_50_assets_by_volume():
    volumes = fetch_24h_volume()
    sorted_syms = sorted(volumes.items(), key=lambda kv: kv[1], reverse=True)
    return [symbol for symbol, vol in sorted_syms[:50]]