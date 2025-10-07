import json, os, time, logging
logger = logging.getLogger(__name__)
SIGNALS_PATH = r"C:\Users\unive\Desktop\v_infinity\adaptive_dca_ai\signals_tmp.json"
MAX_EMPTY = 10
BACKOFF_BASE = 2

def safe_write_signals(signals, consec_empty_ref):
    tmp_path = SIGNALS_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(signals, f, ensure_ascii=False)
        os.replace(tmp_path, SIGNALS_PATH)
        logger.info("WROTE %d signals to %s", len(signals) if signals else 0, SIGNALS_PATH)
        consec_empty_ref[0] = 0
    except Exception:
        logger.exception("Failed writing signals file")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        # on failure, increment empty counter to trigger backoff outside

def maybe_backoff(consec_empty):
    if consec_empty > MAX_EMPTY:
        backoff = min(60, BACKOFF_BASE ** (consec_empty - MAX_EMPTY))
        logger.warning("No signals for %d cycles; backing off %s seconds", consec_empty, backoff)
        time.sleep(backoff)
