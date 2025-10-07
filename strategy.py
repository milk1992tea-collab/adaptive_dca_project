from typing import List, Dict, Any, Tuple
import math

def dca_simulate(
    prices: List[float],
    step: float,
    base_qty: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    max_position_qty: float = 1000.0
) -> Dict[str, Any]:
    """
    DCA 模擬 + TP/SL：
    - 當價格較上次買入價下降超過 step → 加倉 base_qty（USDT 名義）
    - 當浮動報酬率 >= take_profit_pct → 全平
    - 當浮動報酬率 <= stop_loss_pct → 全平
    - 最大持倉限制 max_position_qty（防守）
    回傳包含 PnL、交易次數、最大回撤、Sharpe 等績效指標。
    """
    if not prices or len(prices) < 2:
        return {"pnl": 0.0, "trades": 0, "max_drawdown": 0.0, "sharpe": 0.0, "closed_rounds": 0}

    last_buy_price = None
    position_qty = 0.0
    cost = 0.0
    entry_price = None
    trades = 0
    closed_rounds = 0

    # 計算報酬率序列用於 Sharpe
    returns = []
    peak_equity = 0.0
    max_drawdown = 0.0

    for i, price in enumerate(prices):
        # 加倉邏輯
        if last_buy_price is None or price <= last_buy_price - step:
            if position_qty + base_qty <= max_position_qty:
                position_qty += base_qty
                cost += base_qty * price
                last_buy_price = price
                if entry_price is None:
                    entry_price = price
                trades += 1

        # 浮動盈虧與止盈止損
        equity = position_qty * price
        pnl_pct = 0.0 if (entry_price is None or entry_price == 0) else (price - entry_price) / entry_price

        # 更新最大回撤（使用等權估值）
        peak_equity = max(peak_equity, equity)
        dd = 0.0 if peak_equity == 0 else (peak_equity - equity) / peak_equity
        max_drawdown = max(max_drawdown, dd)

        # 記錄逐步報酬率（用差分近似）
        if i > 0 and prices[i-1] != 0:
            returns.append((price - prices[i-1]) / prices[i-1])

        # 觸發 TP/SL 則全平
        if entry_price and position_qty > 0 and (pnl_pct >= take_profit_pct or pnl_pct <= stop_loss_pct):
            closed_rounds += 1
            # 全平後重置持倉
            position_qty = 0.0
            cost = 0.0
            entry_price = None
            last_buy_price = None

    # 最終估值與 PnL（若持倉仍在）
    final_value = position_qty * prices[-1]
    pnl = final_value - cost

    # Sharpe（簡化：均值/標準差 * sqrt(N)）
    if returns:
        mean_r = sum(returns) / len(returns)
        var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std_r = math.sqrt(var_r)
        sharpe = 0.0 if std_r == 0 else (mean_r / std_r) * math.sqrt(len(returns))
    else:
        sharpe = 0.0

    return {
        "pnl": pnl,
        "trades": trades,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "closed_rounds": closed_rounds
    }


def composite_score(metrics: Dict[str, Any]) -> float:
    """
    複合目標分數：
    - 目標最大化：PnL + 100 * Sharpe
    - 目標最小化：回撤（以懲罰形式扣分）
    - 保障：若交易次數過低（<= 1），給大幅扣分避免空轉
    """
    pnl = metrics["pnl"]
    sharpe = metrics["sharpe"]
    mdd = metrics["max_drawdown"]
    trades = metrics["trades"]
    closed_rounds = metrics["closed_rounds"]

    if trades <= 1 and closed_rounds == 0:
        return -1e6  # 幾乎沒動作，直接打槍

    score = pnl + 100.0 * sharpe - 500.0 * mdd
    return score