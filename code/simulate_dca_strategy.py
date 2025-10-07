# adaptive_dca_ai/code/simulate_dca_strategy.py
from typing import Tuple, Any, List
import pandas as pd
import numpy as np
import logging
import os

_log = logging.getLogger("adaptive_dca_ai.simulate_dca_strategy")
if not _log.handlers:
    _log.addHandler(logging.StreamHandler())
_log.setLevel(logging.INFO)

def _load_df(df_or_path: Any) -> pd.DataFrame:
    if df_or_path is None:
        raise ValueError("No data provided")
    if isinstance(df_or_path, str):
        if not os.path.exists(df_or_path):
            raise FileNotFoundError(f"CSV not found: {df_or_path}")
        df = pd.read_csv(df_or_path, parse_dates=True)
    elif hasattr(df_or_path, "copy"):
        # assume DataFrame-like
        df = df_or_path.copy()
    else:
        raise TypeError("dataset must be path or DataFrame-like")
    # try to ensure 'close' column presence
    if "close" not in df.columns and "price" in df.columns:
        df = df.rename(columns={"price": "close"})
    if "close" not in df.columns:
        raise ValueError("DataFrame missing 'close' column")
    return df

def simulate_dca_strategy(
    df: Any,
    rsi_threshold: float = 50,
    td_confirm: bool = True,
    dca_ratio: float = 0.2,
    dca_spacing: float = 0.02,
    dca_max_steps: int = 3,
    mode: str = "spot",
    leverage: int = 1,
    funding_rate: float = 0.0,
    initial_capital: float = 1000.0,
    fee_taker: float = 0.0004,
    fee_maker: float = 0.0002,
) -> Tuple[float, float, float, List[float]]:
    """
    Minimal deterministic simulator for testing:
    - loads CSV or DataFrame,
    - computes a simple buy-and-hold PnL over the series scaled by initial_capital,
    - returns (pnl_usd, maxdd, sharpe, equity_list).
    This is NOT a production strategy, only for integration tests.
    """
    try:
        pdf = _load_df(df)
    except Exception as e:
        _log.exception("failed to load dataset")
        raise

    closes = pd.to_numeric(pdf["close"], errors="coerce").dropna().values
    if len(closes) < 2:
        raise ValueError("not enough price points in dataset")

    # simple equity: scale normalized price series to initial capital
    norm = closes / closes[0]
    equity = (norm * initial_capital).tolist()

    pnl_usd = equity[-1] - initial_capital
    # max drawdown simple calculation
    peak = -float("inf")
    maxdd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / max(1.0, peak)
        if dd > maxdd:
            maxdd = dd
    # simple sharpe approximation: mean return / std of returns * sqrt(252)
    rets = np.diff(equity) / np.maximum(equity[:-1], 1e-9)
    if rets.size > 1:
        sharpe = float((rets.mean() / (rets.std() + 1e-12)) * (252 ** 0.5))
    else:
        sharpe = 0.0

    return float(pnl_usd), float(maxdd), float(sharpe), equity