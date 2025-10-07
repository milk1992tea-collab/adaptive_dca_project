# store_db.py
import sqlite3, json, os, time
DB = os.path.join(os.path.dirname(__file__), 'adaptive_dca.db')

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS lists (
      name TEXT PRIMARY KEY,
      payload TEXT,
      updated_ts INTEGER
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS dca_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER,
      action TEXT,
      payload TEXT,
      status TEXT
    )
    ''')
    conn.commit()
    conn.close()

def save_list(name, records):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    payload = json.dumps(records, ensure_ascii=False)
    c.execute("REPLACE INTO lists(name,payload,updated_ts) VALUES(?,?,?)", (name, payload, int(time.time())))
    conn.commit()
    conn.close()

def load_list(name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT payload, updated_ts FROM lists WHERE name=?", (name,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None, None
    return json.loads(row[0]), row[1]

def insert_dca_run(action, payload, status='done'):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO dca_runs(ts,action,payload,status) VALUES(?,?,?,?)", (int(time.time()), action, json.dumps(payload, ensure_ascii=False), status))
    conn.commit()
    conn.close()

if __name__=='__main__':
    init_db()
