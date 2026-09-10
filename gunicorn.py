import os

# Add the src/ directory to the Python path so the "transport" package resolves
pythonpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

# ASGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "transport.main:app"

# The granularity of Error log outputs
loglevel = "info"

# The number of worker processes for handling requests
workers = 1

# The socket to bind
#bind = "/run/gunicorn.sock"
bind = "0.0.0.0:4010"

# Don't restart workers when code changes (development only!)
reload = False

# Write access and error info to /var/log
accesslog = errorlog = "var/log/prod.log"

# Redirect stdout/stderr to log file
capture_output = True

# PID file so you can easily fetch process ID
pidfile = "var/run/prod.pid"

# Daemonize the Gunicorn process (detach & enter background)
daemon = True

# ASGI Uvicorn worker class (instead of WSGI)
worker_class = "uvicorn.workers.UvicornWorker"

# Allow uvicorn's lifespan handling for FastAPI
lifespan = "on"
