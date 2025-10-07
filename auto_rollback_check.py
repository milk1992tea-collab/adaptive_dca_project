import subprocess,sys,os
def alert_and_rollback():
    # quick check: if daily_monitor.latest.csv empty or contains ERROR, rollback to stable-post-sanitize
    try:
        with open('daily_monitor.latest.csv','r',encoding='utf8') as f:
            s=f.read()
        if not s.strip() or 'ERROR' in s.upper():
            subprocess.run(['git','checkout','stable-post-sanitize-20251003'.replace('20251003','stable-post-sanitize-20251003')])
            with open('rollback.log','a',encoding='utf8') as L: L.write('rollback triggered\\n')
    except Exception as e:
        with open('rollback.err.log','a',encoding='utf8') as L: L.write(str(e)+'\\n')
if __name__=='__main__': alert_and_rollback()
