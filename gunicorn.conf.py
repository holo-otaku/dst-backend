#!/usr/bin/env python3

import multiprocessing
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Server socket
port = int(os.environ.get('PORT', 5001))
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', 1000))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 30))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 2))

# Restart workers after this many requests, to help prevent memory leaks
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Logging
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')  # STDOUT
access_log_format = os.environ.get('GUNICORN_ACCESS_LOG_FORMAT', 
                                 '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(B)s "%(f)s" "%(a)s"')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')   # STDERR

# Process naming
proc_name = os.environ.get('GUNICORN_PROC_NAME', 'dst-backend')

# Application
preload_app = os.environ.get('GUNICORN_PRELOAD_APP', 'True').lower() == 'true'
