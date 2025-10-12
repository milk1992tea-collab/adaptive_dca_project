# tools/shims/health.py - extended status
try:
    import time, os, socket, subprocess, sys
    from fastapi import Response
    def _maybe_register(app):
        try:
            _runtime = globals().get('_runtime')
            if _runtime is None:
                _runtime = {}
                globals()['_runtime'] = _runtime

            @app.on_event("startup")
            async def _shim_startup():
                _runtime['pid'] = os.getpid()
                _runtime['started_at'] = time.time()
                _runtime['status'] = 'running'

            if not any(r.path == "/health" for r in getattr(app, "routes", [])):
                @app.get("/health")
                async def _health():
                    rt = globals().get("_runtime", {})
                    return {"pid": rt.get("pid"), "started_at": rt.get("started_at"), "status": rt.get("status", "unknown")}

            if not any(r.path == "/status" for r in getattr(app, "routes", [])):
                @app.get("/status")
                async def _status():
                    rt = globals().get("_runtime", {})
                    started = rt.get("started_at")
                    uptime = None
                    if started:
                        uptime = time.time() - started
                    # attempt to read git commit, ignore errors
                    git_commit = None
                    try:
                        git_commit = subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=os.getcwd(), stderr=subprocess.DEVNULL).decode().strip()
                    except Exception:
                        git_commit = None
                    return {
                        "pid": rt.get("pid"),
                        "started_at": started,
                        "status": rt.get("status", "unknown"),
                        "uptime_seconds": uptime,
                        "hostname": socket.gethostname(),
                        "git_commit": git_commit
                    }
        except Exception:
            pass

    import sys
    caller = sys.modules.get('app')
    if caller is not None and hasattr(caller, 'app'):
        _maybe_register(caller.app)
except Exception:
    pass
