# run_live.py
# service daemon wrapper for run_live.py
import os
import sys
import time
import signal
import logging
import traceback
import subprocess
from datetime import datetime

# single-instance helper (uses psutil if available)
try:
    import psutil
except Exception:
    psutil = None

# primary entry point from your application
from signals_wrapper import main as _entry_main  # 若啟動函式非 main，請改名稱

# import safe writer helper from hotfix
try:
    from replace_signals import safe_write_signals, maybe_backoff
except Exception:
    # Fallback no-op implementations if replace_signals is missing
    def safe_write_signals(signals, consec_empty_ref=None):
        signals_path = os.path.join(os.path.dirname(__file__), "signals_tmp.json")
        try:
            tmp_path = signals_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                import json
                json.dump(signals, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, signals_path)
            logging.getLogger(__name__).info("WROTE %d signals to %s", len(signals) if signals else 0, signals_path)
            if consec_empty_ref is not None and signals:
                try:
                    consec_empty_ref[0] = 0
                except Exception:
                    pass
        except Exception:
            logging.getLogger(__name__).exception("fallback safe_write_signals failed")

    def maybe_backoff(consec_empty):
        return 0

# logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
STDOUT_LOG = os.path.join(LOG_DIR, "stdout.log")
STDERR_LOG = os.path.join(LOG_DIR, "stderr.log")

# configure logging to file and console
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

fh = logging.FileHandler(STDOUT_LOG, encoding="utf-8")
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

eh = logging.FileHandler(STDERR_LOG, encoding="utf-8")
eh.setLevel(logging.ERROR)
eh.setFormatter(formatter)
logger.addHandler(eh)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

def sanitize_for_log(s):
    try:
        if s is None:
            return ''
        value = str(s)
        for pat in ('\r', '\n', '`n', '\\`n'):
            value = value.replace(pat, '')
        return value
    except Exception:
        return str(s)

def safe_git(cmd_args):
    try:
        out = subprocess.check_output(cmd_args, stderr=subprocess.STDOUT, shell=False)
        return out.decode("utf8", errors="ignore").strip()
    except Exception:
        return ""

# PID lock
PIDFILE = os.path.join(os.path.dirname(__file__), "run_live.pid")

def already_running():
    if not os.path.exists(PIDFILE):
        return False
    try:
        with open(PIDFILE, "r") as f:
            pid = int(f.read().strip())
        if pid <= 0:
            return False
        if psutil:
            return psutil.pid_exists(pid)
        else:
            try:
                os.kill(pid, 0)
                return True
            except Exception:
                return False
    except Exception:
        return False

def write_pidfile():
    try:
        with open(PIDFILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        logger.exception("Failed to write pidfile")

def remove_pidfile():
    try:
        if os.path.exists(PIDFILE):
            os.remove(PIDFILE)
    except Exception:
        pass

# graceful shutdown support
_shutdown = False

def _signal_handler(signum, frame):
    global _shutdown
    logging.info("Received signal %s, initiating shutdown", signum)
    _shutdown = True

signal.signal(signal.SIGTERM, _signal_handler)
try:
    signal.signal(signal.SIGINT, _signal_handler)
except Exception:
    pass

# Consecutive-empty counter used by signals writer
# Use single-element list as mutable reference so it can be shared across modules
consec_empty = [0]

# Utility wrapper to call your application entry point safely.
# If your application itself is responsible for writing signals, ensure it
# imports safe_write_signals from replace_signals or calls the helper below.
def _run_entry_once():
    """
    Runs the application entry function once.
    This wrapper exists so we can capture returned signals if your entrypoint
    is structured to return them. If your _entry_main handles its own IO and
    signal writing, this wrapper will simply call it.
    Expected behaviors:
    - If _entry_main returns an object named 'signals' (list/dict), we will use
      safe_write_signals to persist it atomically.
    - If _entry_main handles its own writes, no additional action is performed.
    """
    try:
        result = _entry_main()
        # If entry returns signals (list or dict), persist safely
        if result is not None:
            # treat truthy sequence/dict as signals
            try:
                safe_write_signals(result, consec_empty)
            except RuntimeError:
                # lock held by another instance; short backoff and continue
                time.sleep(0.2)
                try:
                    safe_write_signals(result, consec_empty)
                except Exception:
                    logger.exception("Second attempt to safe_write_signals failed")
        else:
            # entry produced no signals object; increment empty counter
            consec_empty[0] += 1
            maybe_backoff(consec_empty[0])
    except Exception as exc:
        # preserve original behavior: log and propagate to outer loop
        logger.exception("Exception from entry main: %s", exc)
        raise

def _service_main_loop():
    while not _shutdown:
        try:
            # Attempt to run the entrypoint using wrapper which will persist returned signals if any.
            _run_entry_once()
        except Exception as exc:
            logger.exception("Unhandled exception in service main loop: %s", exc)
            logger.error(traceback.format_exc())
            for _ in range(10):
                if _shutdown:
                    break
                time.sleep(1)
        # small sleep between iterations to avoid tight loop
        for _ in range(1):
            if _shutdown:
                break
            time.sleep(1)

def _graceful_run():
    try:
        if already_running():
            logger.info("Another instance is running, exiting")
            return
        write_pidfile()
        _service_main_loop()
    except KeyboardInterrupt:
        logger.info("Service interrupted by KeyboardInterrupt, exiting gracefully")
    except SystemExit:
        logger.info("Service received SystemExit, exiting gracefully")
    except Exception:
        logger.exception("Unexpected exception in graceful runner")
    finally:
        logger.info("Service stopped")
        remove_pidfile()

if __name__ == "__main__":
    _graceful_run()