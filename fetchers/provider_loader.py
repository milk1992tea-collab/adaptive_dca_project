import importlib
import logging
from typing import Optional

logger = logging.getLogger("provider_loader")

def load_provider(mod_path: str):
    try:
        mod = importlib.import_module(mod_path)
    except Exception as e:
        logger.warning("provider_loader: import failed %s: %s", mod_path, e)
        return None
    if not hasattr(mod, "get_turnover_top"):
        logger.warning("provider_loader: module %s missing get_turnover_top", mod_path)
        return None
    return mod
