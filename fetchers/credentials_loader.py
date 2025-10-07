# fetchers/credentials_loader.py
import os
import json
import pathlib

CFG = pathlib.Path(__file__).resolve().parents[1] / "config" / "credentials.json"

def load_credentials():
    creds = {}
    # environment overrides
    if os.environ.get("BINANCE_API_KEY"):
        creds.setdefault("binance", {})["api_key"] = os.environ.get("BINANCE_API_KEY")
    if os.environ.get("BINANCE_API_SECRET"):
        creds.setdefault("binance", {})["api_secret"] = os.environ.get("BINANCE_API_SECRET")
    # file fallback
    if CFG.exists():
        with open(CFG, "r", encoding="utf8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k not in creds:
                creds[k] = v
            else:
                for kk, vv in v.items():
                    creds[k].setdefault(kk, vv)
    return creds
