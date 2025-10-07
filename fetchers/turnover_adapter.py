# fetchers/turnover_adapter.py
import os
import logging
logger = logging.getLogger("turnover_adapter")
from fetchers.provider_loader import load_provider

def fetch_turnover_top(n=20):
    prov = os.environ.get("TURNOVER_PROVIDER")
    if not prov:
        logger.error("TURNOVER_PROVIDER not set")
        raise RuntimeError("TURNOVER_PROVIDER not set")
    mod = load_provider(prov)
    if mod is None:
        logger.error("failed to load provider %s", prov)
        raise RuntimeError(f"failed to load provider {prov}")
    if not hasattr(mod, "get_turnover_top"):
        logger.error("provider %s missing get_turnover_top", prov)
        raise RuntimeError(f"provider {prov} missing get_turnover_top")
    try:
        return mod.get_turnover_top(n)
    except Exception as e:
        logger.exception("provider %s get_turnover_top raised", prov)
        raise
