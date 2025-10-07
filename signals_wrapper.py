# signals_wrapper.py
import json, traceback
from pathlib import Path

CAND_FILE = "candidate_list.json"
OUT_FILE = "signals_tmp.json"
TIMEFRAMES = ["5m","15m","1h","4h"]

def load_candidates():
    p = Path(CAND_FILE)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, list) else []

def try_import_generate_signals():
    try:
        from signal_generator import generate_signals
        return generate_signals
    except Exception:
        return None

def fallback_signals(cands, timeframes):
    sigs=[]
    for s in cands:
        for tf in timeframes:
            sigs.append({
                "symbol": s,
                "timeframe": tf,
                "strategy": "hybrid_mix",
                "signal": "hold",
                "score": 0.0,
                "params": {}
            })
    return sigs

def main():
    cands = load_candidates()[:50]
    gen = try_import_generate_signals()
    if gen:
        try:
            sigs = gen(cands, timeframes=TIMEFRAMES, dry_run=True)
        except TypeError:
            try:
                sigs = gen(cands, TIMEFRAMES)
            except Exception:
                sigs = fallback_signals(cands, TIMEFRAMES)
        except Exception:
            sigs = fallback_signals(cands, TIMEFRAMES)
    else:
        sigs = fallback_signals(cands, TIMEFRAMES)
    Path(OUT_FILE).write_text(json.dumps(sigs, ensure_ascii=False, indent=2), encoding="utf8")
    print("WROTE", len(sigs), "signals to", OUT_FILE)

if __name__=="__main__":
    main()



