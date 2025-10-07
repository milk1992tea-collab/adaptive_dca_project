# config_loader.py
import json
import math
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "strategy_config.json")

def load_config(path=None):
    path = path or DEFAULT_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg

def compute_allocation(cfg, total_usdt_override=None):
    """
    回傳 dict:
      {
        'total_usdt': float,
        'usable_usdt': float,
        'per_asset_budget': float,
        'initial_order': float,
        'add_sequence': [a0, a1, ...],
        'sum_sequence': float,
        'notes': str
      }
    """
    total_usdt = float(total_usdt_override) if total_usdt_override is not None else float(cfg.get("total_usdt", 0))
    usable_ratio = float(cfg.get("usable_ratio", 0.8))
    max_holdings = int(cfg.get("max_holdings", 10))
    max_adds = int(cfg.get("max_adds", 3))
    r = float(cfg.get("amount_multiplier", 1.3))
    min_order_size = float(cfg.get("min_order_size", 10))
    reserve_ratio = float(cfg.get("reserve_ratio", 0.2))

    usable_usdt = total_usdt * usable_ratio
    # Per-asset budget before rounding
    per_asset_budget = usable_usdt / max_holdings if max_holdings > 0 else 0.0

    # geometric series sum S = sum_{i=0..max_adds} r^i
    S = sum((r ** i) for i in range(0, max_adds + 1))
    if S <= 0:
        raise ValueError("Invalid multiplicative series sum")

    # initial order A (pre-rounding)
    A = per_asset_budget / S if S > 0 else 0.0

    # round initial order A up to meet min_order_size
    if A < min_order_size:
        # If calculated A below exchange min, try to reduce max_holdings (informal): compute minimal feasible max_holdings
        # But here we enforce A >= min_order_size by scaling per_asset_budget if possible.
        # We'll try to compute required per_asset_budget to satisfy min_order_size:
        required_per_asset = min_order_size * S
        feasible = True
        if required_per_asset > usable_usdt:
            feasible = False
        if not feasible:
            # cannot satisfy min_order_size with current total_usdt and params
            # return values with flag for UI to notify
            notes = ("INSUFFICIENT_FUNDS_FOR_MIN_ORDER: "
                     f"required_per_asset={required_per_asset:.2f} > usable_usdt={usable_usdt:.2f}")
            logger.warning(notes)
            return {
                "total_usdt": total_usdt,
                "usable_usdt": usable_usdt,
                "per_asset_budget": per_asset_budget,
                "initial_order": A,
                "add_sequence": [],
                "sum_sequence": per_asset_budget,
                "feasible": False,
                "notes": notes
            }
        # else scale per_asset_budget up to required_per_asset (effectively reduce max_holdings)
        per_asset_budget = required_per_asset
        A = min_order_size

    # build add sequence and ensure each entry respects rounding and min_order_size
    seq = []
    for i in range(0, max_adds + 1):
        val = A * (r ** i)
        # round to 2 decimals (USDT)
        val = math.ceil(val * 100) / 100.0
        if val < min_order_size:
            val = min_order_size
        seq.append(val)

    sum_seq = sum(seq)

    # if rounding pushed sum_seq above per_asset_budget by a lot, warn / adjust initial order downward if necessary
    if sum_seq > per_asset_budget * 1.005:  # tolerance 0.5%
        notes = (f"Rounding increased per-asset sum to {sum_seq:.2f} > budget {per_asset_budget:.2f}. "
                 "Consider increasing total_usdt or reducing max_holdings.")
        logger.warning(notes)
    else:
        notes = "OK"

    return {
        "total_usdt": total_usdt,
        "usable_usdt": usable_usdt,
        "per_asset_budget": per_asset_budget,
        "initial_order": seq[0],
        "add_sequence": seq,
        "sum_sequence": sum_seq,
        "feasible": True,
        "notes": notes
    }

if __name__ == "__main__":
    # quick local test using strategy_config.json in same dir
    cfg = load_config()
    res = compute_allocation(cfg)
    print(json.dumps(res, indent=2))