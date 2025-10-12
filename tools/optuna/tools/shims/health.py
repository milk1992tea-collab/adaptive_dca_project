# tools/shims/health.py - extended with Prometheus metrics
try:
    import time, os, socket, subprocess
    from fastapi import Response, Request
    from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client import PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
    from prometheus_client import multiprocess

    # global runtime storage
    def _maybe_register(app):
        try:
            # runtime dict
            _runtime = globals().get("_runtime")
            if _runtime is None:
                _runtime = {}
                globals()["_runtime"] = _runtime

            @app.on_event("startup")
            async def _shim_startup():
                _runtime['pid'] = os.getpid()
                _runtime['started_at'] = time.time()
                _runtime['status'] = 'running'

            # Setup Prometheus registry and metrics (single-process)
            registry = CollectorRegistry()
            # register standard collectors
            PROCESS_COLLECTOR(registry)
            PLATFORM_COLLECTOR(registry)
            GC_COLLECTOR(registry)

            REQUEST_COUNT = Counter("app_http_requests_total", "Total HTTP requests", ["method","path","status"], registry=registry)
            REQUEST_LATENCY = Histogram("app_http_request_latency_seconds", "HTTP request latency seconds", ["method","path"], registry=registry)
            IN_PROGRESS = Gauge("app_inprogress_requests", "In-progress HTTP requests", registry=registry)

            # middleware to instrument requests
            @app.middleware("http")
            async def prometheus_middleware(request: Request, call_next):
                path = request.url.path
                method = request.method
                IN_PROGRESS.inc()
                start = time.time()
                try:
                    resp = await call_next(request)
                    status = str(resp.status_code)
                    return resp
                finally:
                    elapsed = time.time() - start
                    REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
                    REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
                    IN_PROGRESS.dec()

            # /metrics endpoint
            if not any(r.path == "/metrics" for r in getattr(app, "routes", [])):
                @app.get("/metrics")
                async def metrics():
                    # return the prometheus metrics for this process
                    data = generate_latest(registry)
                    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

            # keep existing /health and /status registrations if not present
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
