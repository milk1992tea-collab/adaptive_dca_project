import ccxt
import pandas as pd
import pandas_ta as ta
import json
import csv
import time
import os
from datetime import datetime
import platform

# === 讀取 config.json ===
with open("C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# === 讀取 allocation.json ===
with open("C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/allocation.json", "r", encoding="utf-8") as f:
    allocation = json.load(f)

exchange = ccxt.binance({
    "apiKey": config["apiKey"],
    "secret": config["secret"],
    "enableRateLimit": True,
    "options": {"defaultType": "future"} if config["mode"] == "futures" else {}
})

if config.get("testnet", False):
    exchange.set_sandbox_mode(True)

symbols = config["symbols"]
timeframe = config["timeframe"]
capital_usdt = config["capital_usdt"]
leverage = config["leverage"]
stop_loss_pct = config["stop_loss_pct"]
take_profit_pct = config["take_profit_pct"]
loop_interval = config.get("loop_interval", 60)
signal_mode_cfg = config.get("signal_mode", "RSI_MACD")
weights_cfg = config.get("weights", None)

# === 資金分配 ===
def get_capital_allocation(symbols, capital_usdt):
    mode = allocation["active_mode"]
    modes = allocation["modes"]
    if mode == "equal":
        return {s: capital_usdt / len(symbols) for s in symbols}
    elif mode == "weighted":
        import random
        scores = {s: random.random() for s in symbols}
        total = sum(scores.values())
        return {s: (scores[s] / total) * capital_usdt for s in symbols}
    elif mode == "custom":
        weights = modes["custom"]["weights"]
        return {s: weights.get(s, 0) * capital_usdt for s in symbols}
    else:
        raise ValueError(f"未知的 allocation_mode: {mode}")

# === 日誌紀錄 ===
def log_trade(data):
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/trade_log_{today}.csv"
    header = ["time", "mode", "symbol", "side", "amount", "price", "stop_loss", "take_profit"]
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(data)

# === 每日績效摘要 ===
def summarize_performance():
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/trade_log_{today}.csv"
    perf_file = f"C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/performance_{today}.csv"
    if not os.path.exists(log_file):
        return
    df = pd.read_csv(log_file)
    df["pnl"] = df.apply(lambda row: row["take_profit"] - row["price"] if row["side"]=="buy" else row["price"]-row["take_profit"], axis=1)
    summary = {
        "date": today,
        "total_trades": len(df),
        "buys": len(df[df["side"]=="buy"]),
        "sells": len(df[df["side"]=="sell"]),
        "total_pnl": round(df["pnl"].sum(),2),
        "avg_pnl": round(df["pnl"].mean(),2) if len(df)>0 else 0
    }
    pd.DataFrame([summary]).to_csv(perf_file, index=False)
    print("\n📊 當日績效摘要")
    for k,v in summary.items(): print(f"{k:12}: {v}")

# === 每小時績效摘要 ===
def summarize_hourly_performance():
    today = datetime.now().strftime("%Y-%m-%d")
    hour = datetime.now().strftime("%H")
    log_file = f"C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/trade_log_{today}.csv"
    perf_file = f"C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/performance_hourly_{today}.csv"
    if not os.path.exists(log_file):
        return
    df = pd.read_csv(log_file)
    df["time"] = pd.to_datetime(df["time"])
    df_hour = df[df["time"].dt.strftime("%H")==hour]
    df_hour["pnl"] = df_hour.apply(lambda row: row["take_profit"]-row["price"] if row["side"]=="buy" else row["price"]-row["take_profit"], axis=1)
    summary = {
        "date": today,
        "hour": hour,
        "total_trades": len(df_hour),
        "buys": len(df_hour[df_hour["side"]=="buy"]),
        "sells": len(df_hour[df_hour["side"]=="sell"]),
        "total_pnl": round(df_hour["pnl"].sum(),2),
        "avg_pnl": round(df_hour["pnl"].mean(),2) if len(df_hour)>0 else 0
    }
    write_header = not os.path.exists(perf_file)
    with open(perf_file,"a",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        if write_header: writer.writeheader()
        writer.writerow(summary)
    print("\n⏱ 小時績效摘要")
    for k,v in summary.items(): print(f"{k:12}: {v}")

# === 即時累積績效 ===
def show_realtime_performance():
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"C:/Users/unive/Desktop/v_infinity/adaptive_dca_ai/trade_log_{today}.csv"
    if not os.path.exists(log_file):
        print("💹 今日累積盈虧: 0 USDT"); return 0.0
    df = pd.read_csv(log_file)
    df["pnl"] = df.apply(lambda row: row["take_profit"]-row["price"] if row["side"]=="buy" else row["price"]-row["take_profit"], axis=1)
    total_pnl = round(df["pnl"].sum(),2)
    print(f"💹 今日累積盈虧: {total_pnl} USDT")
    return total_pnl

# === 策略函數 ===
def rsi_macd_signal(series):
    rsi = ta.rsi(series, length=14)
    macd = ta.macd(series, fast=12, slow=26, signal=9)
    if rsi.iloc[-1]<30 and macd["MACD_12_26_9"].iloc[-1]>macd["MACDs_12_26_9"].iloc[-1]:
        return "buy"
    elif rsi.iloc[-1]>70 and macd["MACD_12_26_9"].iloc[-1]<macd["MACDs_12_26_9"].iloc[-1]:
        return "sell"
    return None

def bollinger_signal(series):
    bb = ta.bbands(series, length=20, std=2)
    if series.iloc[-1] < bb["BBL_20_2.0"].iloc[-1]: return "buy"
    if series.iloc[-1] > bb["BBU_20_2.0"].iloc[-1]: return "sell"
    return None

def kdj_signal(series):
    kdj = ta.kdj(series, length=14, signal=3)
    k, d = kdj["K_14_3"], kdj["D_14_3"]
    if len(series)<2: return None
    if k.iloc[-1]<20 and d.iloc[-1]<20 and k.iloc[-2]<d.iloc[-2] and k.iloc[-1]>d.iloc[-1]:
        return "buy"
    if k.iloc[-1]>80 and d.iloc[-1]>80 and k.iloc[-2]>d.iloc[-2] and k.iloc[-1]<d.iloc[-1]:
        return "sell"
    return None

STRATEGIES = {
    "RSI_MACD": rsi_macd_signal,
    "BOLLINGER": bollinger_signal,
    "KDJ": kdj_signal
}

# === 訊號判斷 ===
def generate_signal(df, use_heikin_ashi=False, force_signal=None, signal_mode="RSI_MACD", weights=None):
    if force_signal in ["buy","sell"]:
        return force_signal

    # Heikin-Ashi 模式
    if use_heikin_ashi:
        ha_df = df.copy()
        ha_df["ha_close"] = (df["open"]+df["high"]+df["low"]+df["close"])/4
        ha_open = [(df["open"].iloc[0]+df["close"].iloc[0])/2]
        for i in range(1,len(df)):
            ha_open.append((ha_open[i-1]+ha_df["ha_close"].iloc[i-1])/2)
        ha_df["ha_open"] = ha_open
        ha_df["ha_high"] = ha_df[["high","ha_open","ha_close"]].max(axis=1)
        ha_df["ha_low"] = ha_df[["low","ha_open","ha_close"]].min(axis=1)
        price_series = ha_df["ha_close"]
    else:
        price_series = df["close"]

    # 單策略
    if signal_mode in STRATEGIES:
        return STRATEGIES[signal_mode](price_series)

    # COMBO：全部一致才下單
    elif signal_mode=="COMBO":
        sigs = [fn(price_series) for fn in STRATEGIES.values()]
        if all(s=="buy" for s in sigs if s is not None): return "buy"
        if all(s=="sell" for s in sigs if s is not None): return "sell"
        return None

    # WEIGHTED：加權投票
    elif signal_mode=="WEIGHTED":
        if weights is None:
            weights = {k:1/len(STRATEGIES) for k in STRATEGIES}
        score=0
        for name,fn in STRATEGIES.items():
            sig=fn(price_series)
            if sig=="buy": score+=weights.get(name,0)
            elif sig=="sell": score-=weights.get(name,0)
        if score>0.5: return "buy"
        elif score<-0.5: return "sell"
        return None

    return None

# === 抓取資料 ===
def fetch_data(symbol, timeframe="1h", limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# === 下單邏輯 ===
def place_order(symbol, signal, capital_share):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker["last"]

    if config["mode"]=="futures":
        if signal=="buy":
            amount=(capital_share*leverage)/price
            order=exchange.create_market_buy_order(symbol, amount)
            stop_loss=round(price*(1-stop_loss_pct),6)
            take_profit=round(price*(1+take_profit_pct),6)
            try:
                exchange.create_order(symbol,"STOP_MARKET","sell",amount,None,{"stopPrice":stop_loss})
                exchange.create_order(symbol,"TAKE_PROFIT_MARKET","sell",amount,None,{"stopPrice":take_profit})
            except Exception as e:
                print(f"⚠️ 止盈/止損掛單失敗: {e}")
            log_trade({"time":datetime.now(),"mode":"futures","symbol":symbol,
                       "side":"buy","amount":amount,"price":price,
                       "stop_loss":stop_loss,"take_profit":take_profit})
            play_alert()
            return order

        elif signal=="sell":
            amount=(capital_share*leverage)/price
            order=exchange.create_market_sell_order(symbol, amount)
            stop_loss=round(price*(1+stop_loss_pct),6)
            take_profit=round(price*(1-take_profit_pct),6)
            try:
                exchange.create_order(symbol,"STOP_MARKET","buy",amount,None,{"stopPrice":stop_loss})
                exchange.create_order(symbol,"TAKE_PROFIT_MARKET","buy",amount,None,{"stopPrice":take_profit})
            except Exception as e:
                print(f"⚠️ 止盈/止損掛單失敗: {e}")
            log_trade({"time":datetime.now(),"mode":"futures","symbol":symbol,
                       "side":"sell","amount":amount,"price":price,
                       "stop_loss":stop_loss,"take_profit":take_profit})
            play_alert()
            return order
    return None

# === 提示音效 ===
def play_alert():
    try:
        if platform.system()=="Windows":
            import winsound
            winsound.Beep(1000,500)  # 1000Hz, 0.5秒
        else:
            print("\a")  # Linux/macOS 用終端機蜂鳴
    except:
        pass

# === 主程式 ===
if __name__=="__main__":
    current_day=datetime.now().strftime("%Y-%m-%d")
    current_hour=datetime.now().strftime("%H")

    while True:
        today=datetime.now().strftime("%Y-%m-%d")
        hour=datetime.now().strftime("%H")

        if today!=current_day:
            summarize_performance()
            current_day=today
        if hour!=current_hour:
            summarize_hourly_performance()
            current_hour=hour

        print(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 檢查開始 ===")
        capital_allocation=get_capital_allocation(symbols, capital_usdt)

        last_signal="無"
        for sym in symbols:
            df=fetch_data(sym,timeframe)
            signal=generate_signal(
                df,
                use_heikin_ashi=config.get("use_heikin_ashi",False),
                force_signal=config.get("force_signal",None),
                signal_mode=signal_mode_cfg,
                weights=weights_cfg
            )
            if signal:
                result=place_order(sym,signal,capital_allocation[sym])
                status="已下單 ✅" if result else "下單失敗 ⚠️"
                last_signal=signal.upper()
                print(f"{sym} | 訊號: {signal.upper()} | 資金分配: {capital_allocation[sym]:.2f} USDT | {status}")
            else:
                print(f"{sym} | 訊號: ⏸ 無 | 資金分配: {capital_allocation[sym]:.2f} USDT")

        total_pnl=show_realtime_performance()

        print("----------------------------------------")
        print(f"⏳ 等待 {loop_interval} 秒後進行下一輪檢查...")

        # 倒數計時 + 狀態列
        for remaining in range(loop_interval,0,-1):
            status_line=f"模式: {signal_mode_cfg} | 今日盈虧: {total_pnl} USDT | 上次訊號: {last_signal} | 下一次檢查: {remaining} 秒"
            print(status_line,end="\r")
            time.sleep(1)
        print("\n")