# adaptive_dca_ai/code/model_selector.py
import os
import sqlite3
import json
import pandas as pd
import datetime
import logging
from typing import List, Dict, Any

_log = logging.getLogger("adaptive_dca_ai.model_selector")
if not _log.handlers:
    _log.addHandler(logging.StreamHandler())
_log.setLevel(logging.INFO)

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "dca_study.db")
RESULTS_CSV = os.path.join(BASE_DIR, "results", "best_trials.csv")

# Score weights
WIN_RATE_W = 0.6
SHARPE_W = 0.3
PNL_W = 0.1


def _connect_db(path: str = DB_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Optuna DB not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _read_trials_table(conn: sqlite3.Connection) -> pd.DataFrame:
    q = "SELECT * FROM trials"
    try:
        df = pd.read_sql(q, conn)
        return df
    except Exception:
        try:
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
            for t in tables["name"].tolist():
                if "trial" in t.lower():
                    try:
                        return pd.read_sql(f"SELECT * FROM {t}", conn)
                    except Exception:
                        continue
        except Exception:
            pass
        return pd.DataFrame()


def _parse_json_field(val):
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        try:
            return json.loads(s.replace("'", '"'))
        except Exception:
            return None


def _normalize_row(row: pd.Series) -> Dict[str, Any]:
    params = {}
    values = None
    user_attrs = {}
    created_at = None
    trial_id = None

    for candidate_key in ("trial_id", "id", "number", "trial_number"):
        if candidate_key in row.index:
            trial_id = row.get(candidate_key)
            break

    for key in row.index:
        lk = key.lower()
        if "params" in lk:
            p = _parse_json_field(row[key])
            if isinstance(p, dict):
                params.update(p)
        if lk.startswith("value") or lk.startswith("values"):
            v = _parse_json_field(row[key])
            if v is None:
                try:
                    values = float(row[key])
                except Exception:
                    values = None
            else:
                values = v
        if "user_attr" in lk or "user_attributes" in lk:
            ua = _parse_json_field(row[key])
            if isinstance(ua, dict):
                user_attrs.update(ua)
        if lk in ("datetime_start", "start_time", "created_at", "created"):
            created_at = row[key]

    if not params:
        for key in ("note", "system_attrs", "attrs"):
            if key in row.index:
                p = _parse_json_field(row[key])
                if isinstance(p, dict):
                    params.update(p)

    try:
        trial_id = int(trial_id) if trial_id is not None else None
    except Exception:
        trial_id = None

    return {
        "trial_id": trial_id,
        "params": params,
        "values": values,
        "user_attrs": user_attrs,
        "created_at": created_at,
        "raw": dict(row),
    }


def _estimate_metrics_from_row(norm: Dict[str, Any]) -> Dict[str, Any]:
    params = norm.get("params") or {}
    values = norm.get("values")
    user = norm.get("user_attrs") or {}

    pnl = None
    maxdd = None
    sharpe = None
    win_rate = None

    if isinstance(values, (list, tuple)):
        try:
            pnl = float(values[0])
            maxdd = float(values[1]) if len(values) > 1 else None
            sharpe = float(values[2]) if len(values) > 2 else None
        except Exception:
            pass
    elif isinstance(values, (int, float)):
        try:
            pnl = float(values)
        except Exception:
            pnl = None

    for k in list(user.keys()):
        lk = k.lower()
        if "pnl" in lk and pnl is None:
            try:
                pnl = float(user[k])
            except Exception:
                pass
        if ("maxdd" in lk or "drawdown" in lk) and maxdd is None:
            try:
                maxdd = float(user[k])
            except Exception:
                pass
        if "sharpe" in lk and sharpe is None:
            try:
                sharpe = float(user[k])
            except Exception:
                pass
        if ("win_rate" in lk or "winrate" in lk) and win_rate is None:
            try:
                win_rate = float(user[k])
            except Exception:
                pass

    if win_rate is None:
        trades = None
        for src in (params, user):
            if isinstance(src, dict) and "trades_list" in src:
                trades = src.get("trades_list")
                break
        if trades and isinstance(trades, (list, tuple)):
            wins = sum(1 for t in trades if (t.get("pnl", 0) > 0))
            total = len(trades)
            win_rate = (wins / total) if total > 0 else None

    if win_rate is None:
        if pnl is not None:
            win_rate = 1.0 if pnl > 0 else 0.0
        elif sharpe is not None:
            win_rate = 1.0 if sharpe > 1.0 else 0.0
        else:
            win_rate = 0.0

    try:
        pnl = float(pnl) if pnl is not None else 0.0
    except Exception:
        pnl = 0.0
    try:
        maxdd = float(maxdd) if maxdd is not None else 0.0
    except Exception:
        maxdd = 0.0
    try:
        sharpe = float(sharpe) if sharpe is not None else 0.0
    except Exception:
        sharpe = 0.0
    try:
        win_rate = float(win_rate)
    except Exception:
        win_rate = 0.0

    return {
        "pnl": pnl,
        "maxdd": maxdd,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "params": params,
        "strategy_name": params.get("strategy_name")
        or user.get("strategy_name")
        or params.get("strategy", "TD13+RSI"),
        "mode": params.get("mode")
        or user.get("mode")
        or params.get("trade_mode")
        or "spot",
        "ltf_interval": params.get("ltf_interval")
        or user.get("ltf")
        or user.get("ltf_interval")
        or "5m",
        "recommended_amount": params.get("recommended_amount")
        or params.get("capital")
        or params.get("initial_capital")
        or 50,
    }


def _normalize_score(metrics: Dict[str, float], pnl_list):
    try:
        pnl_scale = (max(abs(x) for x in pnl_list) if pnl_list else 1.0)
    except Exception:
        pnl_scale = 1.0
    return (
        metrics.get("win_rate", 0.0) * WIN_RATE_W
        + (metrics.get("sharpe", 0.0) * SHARPE_W)
        + ((metrics.get("pnl", 0.0) / max(1.0, pnl_scale)) * PNL_W)
    )


def get_all_candidates(limit: int = 200) -> List[Dict[str, Any]]:
    try:
        conn = _connect_db()
    except FileNotFoundError as e:
        _log.warning(str(e))
        return []
    try:
        df = _read_trials_table(conn)
        if df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            try:
                norm = _normalize_row(r)
                metrics = _estimate_metrics_from_row(norm)
                candidate = {
                    "id": norm.get("trial_id"),
                    "params": metrics.get("params"),
                    "mode": metrics.get("mode"),
                    "recommended_amount": metrics.get("recommended_amount"),
                    "pnl": metrics.get("pnl"),
                    "maxdd": metrics.get("maxdd"),
                    "sharpe": metrics.get("sharpe"),
                    "win_rate": metrics.get("win_rate"),
                    "strategy_name": metrics.get("strategy_name"),
                    "ltf_interval": metrics.get("ltf_interval"),
                    "created_at": norm.get("created_at"),
                    "raw_row": norm.get("raw"),
                }
                rows.append(candidate)
            except Exception:
                continue
        rows_sorted = sorted(
            rows,
            key=lambda x: (x.get("win_rate", 0), x.get("sharpe", 0), x.get("pnl", 0)),
            reverse=True,
        )
        return rows_sorted[:limit]
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_top_k_candidates(k: int = 3) -> List[Dict[str, Any]]:
    cands = get_all_candidates(limit=500)
    if not cands:
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        sample = {
            "id": 1,
            "params": {},
            "mode": "spot",
            "recommended_amount": 50,
            "pnl": 0.0,
            "maxdd": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "strategy_name": "TD13+RSI",
            "ltf_interval": "5m",
            "created_at": now,
            "raw_row": {
                "trial_id": 1,
                "number": 0,
                "study_id": 1,
                "state": "COMPLETE",
                "datetime_start": now,
                "datetime_complete": now,
            },
            "score": 0.0,
        }
        return [sample] * max(1, k)
    pnls = [c.get("pnl", 0.0) for c in cands]
    for c in cands:
        try:
            c["score"] = _normalize_score(
                {"win_rate": c.get("win_rate", 0.0), "sharpe": c.get("sharpe", 0.0), "pnl": c.get("pnl", 0.0)},
                pnls,
            )
        except Exception:
            c["score"] = 0.0
    cands = sorted(cands, key=lambda x: x.get("score", 0.0), reverse=True)
    topk = cands[:k]
    try:
        os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
        pd.DataFrame(topk).to_csv(RESULTS_CSV, index=False)
    except Exception:
        pass
    return topk


def get_candidate_by_id(trial_id: int) -> Dict[str, Any]:
    allc = get_all_candidates(limit=1000)
    for c in allc:
        try:
            if c.get("id") == int(trial_id):
                return c
        except Exception:
            continue
    return {}


def get_study() -> pd.DataFrame:
    try:
        conn = _connect_db()
        df = _read_trials_table(conn)
        conn.close()
        return df
    except Exception as e:
        _log.error(f"❌ 無法讀取自訂 trial 資料庫：{e}")
        return pd.DataFrame()


def study_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        norm = _normalize_row(row)
        metrics = _estimate_metrics_from_row(norm)
        flat = {
            "trial_id": norm.get("trial_id"),
            "created_at": norm.get("created_at"),
            "pnl": metrics.get("pnl"),
            "sharpe": metrics.get("sharpe"),
            "maxdd": metrics.get("maxdd"),
            "win_rate": metrics.get("win_rate"),
            "raw_row": norm.get("raw"),
        }
        for k, v in norm.get("params", {}).items():
            flat[f"param_{k}"] = v
        rows.append(flat)
    return pd.DataFrame(rows)


# DB introspection + enrichment helper
def _find_candidate_tables(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    tbls = {}
    try:
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        for t in tables["name"].tolist():
            try:
                cols = pd.read_sql(f"PRAGMA table_info('{t}')", conn)
                tbls[t] = cols["name"].tolist()
            except Exception:
                tbls[t] = []
    except Exception:
        pass
    return tbls


def _read_table_as_df(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    try:
        return pd.read_sql(f"SELECT * FROM {table}", conn)
    except Exception:
        return pd.DataFrame()


def get_enriched_study() -> pd.DataFrame:
    try:
        conn = _connect_db()
    except FileNotFoundError as e:
        _log.warning(str(e))
        return pd.DataFrame()

    try:
        trials_df = _read_trials_table(conn)
        if trials_df.empty:
            return trials_df

        tables = _find_candidate_tables(conn)
        candidate_details = []
        for tbl, cols in tables.items():
            if tbl.lower().startswith("trials"):
                continue
            lc = [c.lower() for c in cols]
            if any(k in " ".join(lc) for k in ("param", "params", "user", "attr", "value", "name", "key", "note", "attrs")):
                df_tbl = _read_table_as_df(conn, tbl)
                if not df_tbl.empty:
                    candidate_details.append((tbl, df_tbl))

        extras = pd.DataFrame(index=trials_df.index)

        for tbl, df_tbl in candidate_details:
            join_key = None
            lower_cols = {c.lower(): c for c in df_tbl.columns}
            for jk in ("trial_id", "number", "trial_number", "id"):
                if jk in lower_cols:
                    join_key = lower_cols[jk]
                    break
            if join_key is None:
                continue

            key_col = None
            val_col = None
            for c in df_tbl.columns:
                lc = c.lower()
                if lc in ("key", "name", "param_key", "param_name"):
                    key_col = c
                if lc in ("value", "val", "param_value", "param_val"):
                    val_col = c

            if key_col and val_col:
                try:
                    df_pivot = df_tbl[[join_key, key_col, val_col]].dropna(subset=[key_col])
                    # safe numeric conversion
                    try:
                        df_pivot[join_key] = pd.to_numeric(df_pivot[join_key])
                    except Exception:
                        # keep original if conversion fails
                        pass
                    df_wide = df_pivot.pivot_table(index=join_key, columns=key_col, values=val_col, aggfunc="first")
                    df_wide.columns = [f"param_{str(c)}" for c in df_wide.columns]
                    df_wide = df_wide.reset_index().rename(columns={join_key: "join_key_val"}).set_index("join_key_val")
                    for idx, row in df_wide.iterrows():
                        if "trial_id" in trials_df.columns:
                            mask = trials_df["trial_id"].astype(str) == str(idx)
                        elif "number" in trials_df.columns:
                            mask = trials_df["number"].astype(str) == str(idx)
                        else:
                            continue
                        for col in row.index:
                            extras.loc[mask, col] = row[col]
                except Exception:
                    continue
            else:
                for c in df_tbl.columns:
                    lc = c.lower()
                    if "params" in lc or "user_attr" in lc or "user" in lc or "attrs" in lc or "note" in lc:
                        try:
                            tmp = df_tbl[[join_key, c]].copy()
                            try:
                                tmp[join_key] = pd.to_numeric(tmp[join_key])
                            except Exception:
                                pass
                            for _, r in tmp.iterrows():
                                keyv = r[c]
                                parsed = None
                                if isinstance(keyv, dict):
                                    parsed = keyv
                                else:
                                    try:
                                        parsed = json.loads(str(keyv))
                                    except Exception:
                                        parsed = None
                                if isinstance(parsed, dict):
                                    for pk, pv in parsed.items():
                                        col_name = f"param_{pk}"
                                        if "trial_id" in trials_df.columns:
                                            mask = trials_df["trial_id"].astype(str) == str(r[join_key])
                                        elif "number" in trials_df.columns:
                                            mask = trials_df["number"].astype(str) == str(r[join_key])
                                        else:
                                            mask = pd.Series([False] * len(trials_df))
                                        if mask.any():
                                            extras.loc[mask, col_name] = pv
                        except Exception:
                            continue

        if not extras.empty:
            extras = extras.reset_index(drop=True)
            trials_df = pd.concat([trials_df.reset_index(drop=True), extras.reset_index(drop=True)], axis=1)

        return trials_df
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        top = get_top_k_candidates(5)
        print(f"Top {len(top)} candidates loaded")
        for t in top:
            print(
                f"ID={t.get('id')} mode={t.get('mode')} win_rate={t.get('win_rate'):.3f} pnl={t.get('pnl'):.2f} sharpe={t.get('sharpe'):.3f}"
            )
    except Exception as e:
        print("ModelSelector error:", e)