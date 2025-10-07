import sqlite3, csv, os, datetime, json
DB='td_test.db'
OUT_DIR='reports'
os.makedirs(OUT_DIR, exist_ok=True)
def fetch():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    total_signals = c.execute('SELECT COUNT(*) FROM td_signals').fetchone()[0]
    per_symbol = c.execute('SELECT symbol, COUNT(*) cnt, AVG(strength) avg_strength FROM td_signals GROUP BY symbol ORDER BY cnt DESC').fetchall()
    per_day = c.execute("SELECT substr(ts,1,10) day, COUNT(*) cnt FROM td_signals GROUP BY day ORDER BY day DESC LIMIT 30").fetchall()
    meta_counts = c.execute("SELECT json_extract(meta,'$.td_count') tdcount, COUNT(*) cnt FROM td_signals GROUP BY tdcount ORDER BY cnt DESC").fetchall()
    conn.close()
    return total_signals, per_symbol, per_day, meta_counts
def write_csv(total, per_symbol, per_day, meta_counts):
    today = datetime.date.today().strftime('%Y%m%d')
    out = os.path.join(OUT_DIR, f'td_test_summary_{today}.csv')
    with open(out,'w',newline='',encoding='utf8') as f:
        w=csv.writer(f)
        w.writerow(['metric','value'])
        w.writerow(['total_signals', total])
        w.writerow([])
        w.writerow(['top_symbols','count','avg_strength'])
        for s in per_symbol: w.writerow(s)
        w.writerow([])
        w.writerow(['day','count'])
        for d in per_day: w.writerow(d)
        w.writerow([])
        w.writerow(['td_count','count'])
        for m in meta_counts: w.writerow(m)
    return out
def pretty_print(total, per_symbol, per_day, meta_counts, csv_path):
    print('total_signals:', total)
    print('\\nTop symbols (symbol, count, avg_strength):')
    for r in per_symbol[:10]: print(' ', r)
    print('\\nSignals per day (last 30):')
    for r in per_day: print(' ', r)
    print('\\nTD count distribution:')
    for r in meta_counts: print(' ', r)
    print('\\nCSV:', csv_path)
if __name__=='__main__':
    total, per_symbol, per_day, meta_counts = fetch()
    csv_path = write_csv(total, per_symbol, per_day, meta_counts)
    pretty_print(total, per_symbol, per_day, meta_counts, csv_path)
