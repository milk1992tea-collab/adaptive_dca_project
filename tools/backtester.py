# backtester.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from data_pipeline import build_dataset
from strategy_triggers import evaluate_signals

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

class Backtester:
    def __init__(self, symbol="BTCUSDT", initial_balance=1000, fee_rate=0.001, slippage=0.0005, leverage=1):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.leverage = leverage

    def run(self, params, lookback=2000, save_report=False, label="test"):
        df = build_dataset(self.symbol, "5m", lookback)
        signals = evaluate_signals(df, params)

        balance = self.initial_balance
        equity_curve = [balance]
        position = None
        entry_price = 0

        # === 資金分配策略 ===
        allocation_mode = params.get("allocation_mode", 0)  # 0=固定金額, 1=固定比例
        allocation_value = params.get("allocation_value", 0.05)  # 預設 5% 或 50 USDT

        for i in range(len(df)):
            price = df["close"].iloc[i] * (1 + self.slippage)
            sig = signals[i]

            # === 平倉檢查 ===
            if position == "LONG":
                if price <= entry_price * params["stop_loss"]:
                    balance *= (price / entry_price) * self.leverage * (1 - self.fee_rate)
                    position = None
                elif price >= entry_price * params["take_profit"]:
                    balance *= (price / entry_price) * self.leverage * (1 - self.fee_rate)
                    position = None
                elif price <= df["high"].iloc[:i+1].max() * (1 - params["trailing_stop"]):
                    balance *= (price / entry_price) * self.leverage * (1 - self.fee_rate)
                    position = None

            elif position == "SHORT":
                if price >= entry_price * (2 - params["stop_loss"]):
                    balance *= (entry_price / price) * self.leverage * (1 - self.fee_rate)
                    position = None
                elif price <= entry_price * (2 - params["take_profit"]):
                    balance *= (entry_price / price) * self.leverage * (1 - self.fee_rate)
                    position = None
                elif price >= df["low"].iloc[:i+1].min() * (1 + params["trailing_stop"]):
                    balance *= (entry_price / price) * self.leverage * (1 - self.fee_rate)
                    position = None

            # === 開倉 ===
            if position is None:
                if sig == "LONG":
                    position = "LONG"
                    entry_price = price
                elif sig == "SHORT":
                    position = "SHORT"
                    entry_price = price

            equity_curve.append(balance)

        pnl = balance - self.initial_balance
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252*24*12)
        maxdd = np.max(np.maximum.accumulate(equity_curve) - equity_curve)

        # === 資金分配策略標註 ===
        alloc_label = "固定金額" if allocation_mode == 0 else "固定比例"
        alloc_value = f"{allocation_value*100:.1f}%" if allocation_mode == 1 else f"{allocation_value*1000:.0f} USDT"

        result = {
            "pnl": pnl,
            "sharpe": sharpe,
            "maxdd": maxdd,
            "equity_curve": equity_curve,
            "allocation_mode": alloc_label,
            "allocation_value": alloc_value
        }

        # === 輸出報告 ===
        if save_report:
            report_file = REPORTS_DIR / f"report_{label}.csv"
            pd.DataFrame({"equity": equity_curve}).to_csv(report_file, index=False)

            plt.figure(figsize=(10,5))
            plt.plot(equity_curve, label=f"{label} | {alloc_label}={alloc_value} | PnL={pnl:.2f}, Sharpe={sharpe:.2f}, MaxDD={maxdd:.2f}")
            plt.title(f"Backtest Report - {self.symbol}")
            plt.xlabel("Steps")
            plt.ylabel("Equity")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(REPORTS_DIR / f"report_{label}.png")
            plt.close()

        return result

if __name__ == "__main__":
    params = {
        "rsi_buy": 30,
        "kdj_buy": 30,
        "rsi_sell": 70,
        "kdj_sell": 70,
        "td_trigger": 9,
        "stop_loss": 0.95,
        "take_profit": 1.10,
        "trailing_stop": 0.05,
        "allocation_mode": 1,   # 0=固定金額, 1=固定比例
        "allocation_value": 0.05
    }
    bt = Backtester("BTCUSDT")
    result = bt.run(params, save_report=True, label="demo")
    print("回測結果:", result)