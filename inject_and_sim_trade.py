import sqlite3, time, uuid, json, os
DB='td_test.db'
def simulate():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS td_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, result TEXT)")
    rows = c.execute("SELECT id, ts, symbol, timeframe, strategy, price, strength, meta FROM td_signals ORDER BY id DESC LIMIT 200").fetchall()
    created = 0
    for r in rows:
        sid, ts, symbol, timeframe, strategy, price, strength, meta = r
        try:
            m = json.loads(meta) if meta else {}
        except:
            m = {}
        if strength is None:
            continue
        if float(strength) >= 0.6:
            oid = str(uuid.uuid4())
            qty = 0.001
            side = 'buy'
            result = 'filled_paper'
            c.execute("INSERT INTO td_trades (ts,order_id,symbol,side,qty,price,result) VALUES (?,?,?,?,?,?,?)",
                      (time.strftime('%Y-%m-%dT%H:%M:%SZ'), oid, symbol, side, qty, price or 0.0, result))
            created += 1
    conn.commit()
    conn.close()
    print('simulated trades created:', created)
if __name__=='__main__':
    simulate()
