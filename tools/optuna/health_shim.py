# health_shim.py
# Registers startup runtime info and /health only if `app` exists in importing module
try:
    import time, os, json
    from fastapi import Response
    # try to find the FastAPI app object in caller modules
    def _maybe_register(app):
        try:
            # startup event to populate _runtime in global namespace
            _runtime = globals().get('_runtime', {})
            @app.on_event("startup")
            async def _shim_startup():
                _runtime['pid'] = os.getpid()
                _runtime['started_at'] = time.time()
                _runtime['status'] = 'running'
            # register /health if not already present
            if not any(r.path == "/health" for r in getattr(app, "routes", [])):
                @app.get("/health")
                async def _health():
                    rt = globals().get("_runtime", {})
                    pid = rt.get("pid")
                    started = rt.get("started_at")
                    status = rt.get("status", "unknown")
                    return Response(content=json.dumps({"pid": pid, "started_at": started, "status": status}), media_type="application/json")
        except Exception:
            pass

    # If imported from the app module where 'app' is defined, register immediately
    import sys
    caller = sys.modules.get('app')
    if caller is not None and hasattr(caller, 'app'):
        _maybe_register(caller.app)
except Exception:
    # non-fatal; shim must never break app startup
    pass
