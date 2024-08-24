# Gunicorn configuration file
import multiprocessing

# The socket to bind
bind = "0.0.0.0:443"

# The number of worker processes for handling requests
workers = 4  # or even 2, depending on your application's needs

# The type of workers to use
worker_class = 'gevent'

# The maximum number of simultaneous clients
worker_connections = 1000

# Reduce max requests to encourage more frequent worker restarts
max_requests = 500
max_requests_jitter = 100

# Add graceful timeout
graceful_timeout = 120

# Increase timeout to allow more time for YOLO processing
timeout = 120  # or higher if needed

# Restart workers when code changes (development only)
reload = True

# The number of seconds to wait for requests on a Keep-Alive connection
keepalive = 5

certfile = "full_chain.crt"

keyfile = "private.key"

logfile = "gunicorn.log"

# Improve logging
loglevel = 'info'
accesslog = 'access.log'
errorlog = 'error.log'

# Preload application code
preload_app = True

# The on_starting function is called just before the master process is initialized
def on_starting(server):
    print("Starting Gunicorn server...")

# The on_exit function is called just before exiting Gunicorn
def on_exit(server):
    print("Stopping Gunicorn server...")