import time, logging
from replace_signals import safe_write_signals, maybe_backoff
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('demo')
consec = [0]
# 模擬主迴圈：前三次傳回空 signals，第四次傳回一筆 signal
cycles = 0
while cycles < 8:
    cycles += 1
    if cycles < 4:
        signals = []
    else:
        signals = [{ 'symbol':'BTC/USDT','timeframe':'5m','signal':'hold' }]
    if not signals:
        consec[0] += 1
        maybe_backoff(consec[0])
    else:
        safe_write_signals(signals, consec)
    time.sleep(1)
import os, tempfile

def atomic_write(path, data_bytes):
    dirpath = os.path.dirname(path) or '.'
    fd, tmp = tempfile.mkstemp(prefix='.tmp_', dir=dirpath)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except:
                pass
import os, tempfile, json, uuid, datetime

def atomic_write(path, data_bytes):
    dirpath = os.path.dirname(path) or '.'
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=dirpath)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except:
                pass

def make_instance_path(base_dir, prefix="signals_instance"):
    pid = os.getpid()
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique = uuid.uuid4().hex[:8]
    filename = f"{prefix}_{pid}_{ts}_{unique}.json"
    return os.path.join(base_dir, filename)

# Example usage: replace existing direct-write with below sequence
# base_dir = os.path.dirname(__file__)
# output_path = make_instance_path(base_dir)
# data_bytes = json.dumps(obj, ensure_ascii=False).encode("utf-8")
# atomic_write(output_path, data_bytes)
# optional marker log
# try:
#     with open(os.path.join(base_dir, "write_markers.log"), "a", encoding="utf-8") as m:
#         m.write(f"{datetime.datetime.utcnow().isoformat()} wrote {os.path.basename(output_path)}\n")
# except:
#     pass
