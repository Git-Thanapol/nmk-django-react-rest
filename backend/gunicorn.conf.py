import multiprocessing
import os

# Bind to TCP for Docker container networking (not unix socket)
bind = "0.0.0.0:8000"

# Allow overriding worker count via env; default to (2 × cores) + 1
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

worker_class = "sync"

# Log to stdout/stderr so `docker logs` captures output
accesslog = "-"
errorlog  = "-"
loglevel  = "info"

timeout   = 120
keepalive = 2
