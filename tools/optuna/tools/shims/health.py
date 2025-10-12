# health_shim.py
# Registers startup runtime info and /health only if `app` exists in importing module
try:
    import time, os
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
        except Exception:
            pass

    import sys
    caller = sys.modules.get('app')
    if caller is not None and hasattr(caller, 'app'):
        _maybe_register(caller.app)
except Exception:
    pass
