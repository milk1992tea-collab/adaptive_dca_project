# volume_scanner.py
import ccxt

# ========= 可調參數（如需） =========
DEFAULT_FALLBACK = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT"]
QUOTE = "USDT"  # 只選 USDT 報價
EXCLUDE = {"USDT/USDT"}  # 排除不合法或無意義的交易對

def _ensure_exchange(exchange=None):
    """
    建立或沿用 exchange 實例，並嘗試載入 markets。
    """
    if exchange is None:
        exchange = ccxt.bybit({"enableRateLimit": True})
    try:
        exchange.load_markets()
    except Exception:
        # 某些環境即使未載入 markets，fetch_tickers 仍可工作
        pass
    return exchange

def _is_valid_symbol(symbol, markets):
    """
    僅保留 quote=USDT 且 base≠USDT，且市場存在（若可查），排除 EXCLUDE。
    """
    if symbol in EXCLUDE:
        return False
    m = markets.get(symbol) if markets else None
    if m:
        return (m.get("quote") == QUOTE) and (m.get("base") != QUOTE)
    # 若 markets 不可用，退化判斷字串模式
    return symbol.endswith(f"/{QUOTE}") and not symbol.startswith(f"{QUOTE}/")

def _score_symbol(symbol, tickers, markets):
    """
    以成交量為主的打分：
    - 優先用 quoteVolume
    - 其次 baseVolume
    - 再退化為 last * baseVolume 或 0
    """
    t = tickers.get(symbol, {})
    qv = t.get("quoteVolume")
    bv = t.get("baseVolume")
    last = t.get("last") or t.get("close") or 0

    if qv is not None:
        return float(qv)
    if bv is not None and last:
        # 將 baseVolume 轉為 quote 規模
        return float(bv) * float(last)
    if bv is not None:
        return float(bv)
    return 0.0

def get_top_volume_symbols(limit=50, exchange=None, exclude=None, min_score=0.0, fallback=None):
    """
    回傳成交量排名靠前的合法 USDT 交易對。
    - 僅保留 quote=USDT 且 base≠USDT
    - 依成交量（quoteVolume/baseVolume 估算）排序
    - 支援排除清單、最小分數過濾與白名單回退
    """
    exchange = _ensure_exchange(exchange)
    try:
        markets = exchange.markets or exchange.load_markets()
    except Exception:
        markets = {}

    try:
        tickers = exchange.fetch_tickers()
    except Exception:
        tickers = {}

    # 合法集合
    symbols = []
    # 若 markets 可用，從 markets 遍歷；否則從 tickers 遍歷
    source = markets.keys() if markets else tickers.keys()
    for s in source:
        if exclude and s in exclude:
            continue
        if _is_valid_symbol(s, markets):
            symbols.append(s)

    # 打分與排序
    scored = []
    for s in symbols:
        score = _score_symbol(s, tickers, markets)
        if score >= min_score:
            scored.append((s, score))
    scored.sort(key=lambda x: x[1], reverse=True)

    out = [s for s, _ in scored[:limit]]

    # 白名單回退（當無資料或全部低於門檻）
    if not out:
        base_fallback = fallback or DEFAULT_FALLBACK
        # 若 markets 可用，過濾掉不存在的 fallback
        if markets:
            out = [s for s in base_fallback if s in markets and _is_valid_symbol(s, markets)]
        else:
            out = [s for s in base_fallback if _is_valid_symbol(s, markets)]
        out = out[:limit]

    return out

# 兼容舊介面（若呼叫不傳參數）
def get_symbols_safe(limit=50):
    return get_top_volume_symbols(limit=limit)