import multiprocessing

# Gunicorn configuration file
# See: https://docs.gunicorn.org/en/stable/configure.html

# Binding
# Since we use Nginx as a reverse proxy, we'll bind to a Unix socket
bind = "unix:/tmp/gunicorn.nmk.sock"

# Workers
# The number of worker processes for handling requests
# A standard formula is (2 x num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Worker Class
# sync is usually fine for Django, but gevent/eventlet are good for high concurrency
worker_class = "sync"

# Logging
accesslog = "/var/log/gunicorn/nmk_access.log"
errorlog = "/var/log/gunicorn/nmk_error.log"
loglevel = "info"

# Security: Don't run as root
# These are handled by systemd usually, but can be set here
# user = "www-data"
# group = "www-data"

# Performance
timeout = 120
keepalive = 2

# Django environment
# chdir = "/path/to/project/backend"
# env = ["DJANGO_SETTINGS_MODULE=backend.settings"]
