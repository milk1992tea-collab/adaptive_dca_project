import sqlite3, json, pprint
conn = sqlite3.connect("adaptive_dca.db")
for row in conn.execute("SELECT id,ts,action,status,payload FROM dca_runs ORDER BY id DESC LIMIT 5"):
    print("id", row[0], "ts", row[1], "action", row[2], "status", row[3])
    pprint.pprint(json.loads(row[4]) if row[4] else None)
conn.close()
