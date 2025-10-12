try:
    import time, os, socket, subprocess, logging
    from fastapi import Response, Request
    from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client import PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
    log = logging.getLogger('health_shim')
    # ensure global registry
    if globals().get('_prom_registry') is None:
        _prom_registry = CollectorRegistry()
        globals()['_prom_registry'] = _prom_registry
        try:
            PROCESS_COLLECTOR(_prom_registry)
            PLATFORM_COLLECTOR(_prom_registry)
            GC_COLLECTOR(_prom_registry)
        except Exception:
            pass
    else:
        _prom_registry = globals()['_prom_registry']

    def _register_routes(app):
        try:
            # runtime info
            if globals().get('_runtime') is None:
                globals()['_runtime'] = {}
            rt = globals()['_runtime']

            # startup handler to populate runtime and log registration
            @app.on_event('startup')
            async def _shim_startup():
                rt['pid'] = os.getpid()
                rt['started_at'] = time.time()
                rt['status'] = 'running'
                try:
                    log.info('health_shim startup: pid=%s registry=%s', rt['pid'], bool(globals().get('_prom_registry')))
                except Exception:
                    pass

            # metrics primitives (store in globals)
            if not globals().get('_metrics_registered'):
                globals()['_REQUEST_COUNT'] = Counter('app_http_requests_total', 'Total HTTP requests', ['method','path','status'], registry=_prom_registry)
                globals()['_REQUEST_LATENCY'] = Histogram('app_http_request_latency_seconds', 'HTTP request latency seconds', ['method','path'], registry=_prom_registry)
                globals()['_IN_PROGRESS'] = Gauge('app_inprogress_requests', 'In-progress HTTP requests', registry=_prom_registry)
                globals()['_metrics_registered'] = True

            # middleware instrumentation if not present
            has_prom_mw = False
            for mw in getattr(app, 'user_middleware', []):
                if getattr(mw, 'name', '') == 'prometheus_middleware':
                    has_prom_mw = True
                    break
            if not has_prom_mw:
                @app.middleware('http')
                async def prometheus_middleware(request: Request, call_next):
                    path = request.url.path
                    method = request.method
                    IN_PROGRESS = globals().get('_IN_PROGRESS')
                    REQUEST_COUNT = globals().get('_REQUEST_COUNT')
                    REQUEST_LATENCY = globals().get('_REQUEST_LATENCY')
                    if IN_PROGRESS: IN_PROGRESS.inc()
                    start = time.time()
                    status = '500'
                    try:
                        resp = await call_next(request)
                        status = str(resp.status_code)
                        return resp
                    finally:
                        elapsed = time.time() - start
                        if REQUEST_LATENCY: REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
                        if REQUEST_COUNT: REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
                        if IN_PROGRESS: IN_PROGRESS.dec()

            # forced registration using add_api_route to avoid route list checks
            async def _metrics_endpoint():
                data = generate_latest(globals().get('_prom_registry'))
                return Response(content=data, media_type=CONTENT_TYPE_LATEST)

            async def _status_endpoint():
                s = globals().get('_runtime', {})
                started = s.get('started_at')
                uptime = None
                if started:
                    uptime = time.time() - started
                git_commit = None
                try:
                    git_commit = subprocess.check_output(['git','rev-parse','--short','HEAD'], cwd=os.getcwd(), stderr=subprocess.DEVNULL).decode().strip()
                except Exception:
                    git_commit = None
                return {
                    'pid': s.get('pid'),
                    'started_at': started,
                    'status': s.get('status', 'unknown'),
                    'uptime_seconds': uptime,
                    'hostname': socket.gethostname(),
                    'git_commit': git_commit
                }

            # add routes idempotently: remove existing same-path routes then add
            existing = [r for r in list(app.router.routes) if getattr(r, 'path', None) in ('/metrics','/status')]
            for r in existing:
                try:
                    app.router.routes.remove(r)
                except Exception:
                    pass

            # add_api_route will register handlers regardless of previous registrations
            app.add_api_route('/metrics', _metrics_endpoint, methods=['GET'], name='metrics')
            app.add_api_route('/status', _status_endpoint, methods=['GET'], name='status')

        except Exception:
            try:
                log.exception('health_shim register failed')
            except Exception:
                pass

    import sys
    caller = sys.modules.get('app')
    if caller is not None and hasattr(caller, 'app'):
        _register_routes(caller.app)
except Exception:
    pass
