import sys,traceback,uvicorn
try:
    uvicorn.run('app:app', host='127.0.0.1', port=18081, log_level='debug', access_log=False)
except SystemExit as e:
    print('SystemExit code:', e.code)
    traceback.print_exc()
except Exception:
    traceback.print_exc()
print('END-OF-RUN')
