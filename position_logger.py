import csv
from datetime import datetime

def log_positions(positions, metrics_dict, filename="position_log.csv"):
    """
    positions: list of symbols（持倉幣種）
    metrics_dict: dict，key = symbol，value = 回測績效 dict（含 sharpe, pnl, drawdown）
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for symbol in positions:
        metrics = metrics_dict.get(symbol, {})
        row = {
            "timestamp": timestamp,
            "symbol": symbol,
            "sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 3),
            "total_pnl": round(metrics.get("total_pnl", 0), 2),
            "max_drawdown": round(metrics.get("max_drawdown", 0), 3)
        }
        rows.append(row)

    with open(filename, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if f.tell() == 0:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\n📘 已記錄持倉快照：{filename}")