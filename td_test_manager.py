print("RUN_TRACE: td_test_manager file load", __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ"))
# --- injected debug helpers (auto-inserted) ---
import logging, sys, time
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format="%(asctime)s %(levelname)s %(message)s")
def debug_log(*a, **k): logging.debug("TD_TEST_DBG " + " ".join(str(x) for x in a), **k)
debug_log("td_test_manager loaded")
# --- end injected debug helpers ---
import sqlite3, json, time, os
DB = 'td_test.db'
LOG = os.path.join('logs','td_test.log')
os.makedirs('logs', exist_ok=True)

def ensure():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS td_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        symbol TEXT,
        timeframe TEXT,
        strategy TEXT,
        price REAL,
        strength REAL,
        meta TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS td_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        order_id TEXT,
        symbol TEXT,
        side TEXT,
        qty REAL,
        price REAL,
        result TEXT
    )''')
    conn.commit()
    conn.close()

def _log(line):
    with open(LOG,'a',encoding='utf8') as f:
        f.write(line + "\\n")

def record_signal(s):
    try:
        ensure()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO td_signals (ts,symbol,timeframe,strategy,price,strength,meta) VALUES (?,?,?,?,?,?,?)",
            (time.strftime('%Y-%m-%dT%H:%M:%SZ'), s.get('symbol'), s.get('timeframe'),
             s.get('strategy'), float(s.get('price',0)), float(s.get('strength',0)),
             json.dumps(s.get('meta',{})))
        )
        conn.commit()
        conn.close()
        _log("{} TD_SIGNAL {} {} {} strength={}".format(time.strftime('%Y-%m-%dT%H:%M:%SZ'),
              s.get('symbol'), s.get('timeframe'), s.get('strategy'), s.get('strength')))
    except Exception as e:
        _log("{} TD_SIGNAL_ERR {}".format(time.strftime('%Y-%m-%dT%H:%M:%SZ'), str(e)))

def record_trade(tr):
    try:
        ensure()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO td_trades (ts,order_id,symbol,side,qty,price,result) VALUES (?,?,?,?,?,?,?)",
            (time.strftime('%Y-%m-%dT%H:%M:%SZ'), tr.get('order_id'), tr.get('symbol'),
             tr.get('side'), float(tr.get('qty',0)), float(tr.get('price',0)), tr.get('result',''))
        )
        conn.commit()
        conn.close()
        _log("{} TD_TRADE {} {} {} {}@{} result={}".format(time.strftime('%Y-%m-%dT%H:%M:%SZ'),
             tr.get('order_id'), tr.get('symbol'), tr.get('side'), tr.get('qty'), tr.get('price'), tr.get('result','')))
    except Exception as e:
        _log("{} TD_TRADE_ERR {}".format(time.strftime('%Y-%m-%dT%H:%M:%SZ'), str(e)))



# --- injected start wrapper (autopatch) ---
import time, traceback
def start(pause_seconds=30):
    try:
        # call ensure() if available
        if 'ensure' in globals() and callable(ensure):
            try:
                ensure()
            except Exception:
                logging.exception('td_test_manager.start: ensure() failed')
        # attempt one record_signal if available
        if 'record_signal' in globals() and callable(record_signal):
            try:
                record_signal({'symbol':'autopatch-start','timeframe':'','strategy':'autopatch','price':0,'strength':0,'meta':{}})
            except Exception:
                logging.exception('td_test_manager.start: record_signal() failed')
        # enter safe heartbeat loop
        logging.info('td_test_manager.start: entering safe heartbeat loop')
        while True:
            time.sleep(pause_seconds)
    except KeyboardInterrupt:
        logging.info('td_test_manager.start: interrupted, exiting')
    except Exception:
        logging.exception('td_test_manager.start: unexpected exception')
# --- end injected start wrapper ---


