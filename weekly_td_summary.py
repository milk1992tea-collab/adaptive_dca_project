import csv, os, datetime
REP_DIR='reports'
OUT='reports/td_test_weekly_summary_' + datetime.date.today().strftime('%Y%m%d') + '.csv'
files = sorted([f for f in os.listdir(REP_DIR) if f.startswith('td_test_summary_')])[-7:]
rows=[]
for fn in files:
    with open(os.path.join(REP_DIR,fn),encoding='utf8') as f:
        reader=csv.reader(f)
        for r in reader:
            rows.append([fn]+r)
with open(OUT,'w',newline='',encoding='utf8') as f:
    w=csv.writer(f)
    w.writerow(['source_file','metric','value'])
    for r in rows: w.writerow(r)
print('weekly summary written to', OUT)
