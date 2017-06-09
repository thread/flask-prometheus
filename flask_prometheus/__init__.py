
import time

from prometheus_client import Counter, Histogram
from prometheus_client import start_http_server
from flask import request

latency_buckets = (
    #  0.05s when x <= 1s
    [x / 20.0 for x in range(0, 20)] +
    #  0.1s when 1s < x <= 5s
    [x / 10.0 for x in range(10, 50)] +
    #  0.2s when 5s < x <= 10s
    [x / 5.0 for x in range(25, 50)]
)

FLASK_REQUEST_LATENCY = Histogram(
    'flask_request_latency_seconds',
    'Flask Request Latency',
    ['method', 'endpoint'],
    buckets=latency_buckets,
)

FLASK_REQUEST_COUNT = Counter(
    'flask_request_count',
    'Flask Request Count',
    ['method', 'endpoint', 'http_status']
)


def before_request():
    request.start_time = time.time()
    request.reported = False


def after_request(response):
    request.reported = True
    request_latency = time.time() - request.start_time

    FLASK_REQUEST_LATENCY.labels(
        request.method,
        request.path,
    ).observe(request_latency)

    FLASK_REQUEST_COUNT.labels(
        request.method,
        request.path,
        response.status_code,
    ).inc()

    return response


def teardown_request(excn):
    # implies that we didn't hit the after_request handler for the request
    if not request.reported:
        request_latency = time.time() - request.start_time
        FLASK_REQUEST_LATENCY.labels(
            request.method,
            request.path
        ).observe(request_latency)

        FLASK_REQUEST_COUNT.labels(
            request.method,
            request.path,
            500,
        ).inc()


def monitor(app, port=8000, addr=''):
    app.before_request(before_request)
    app.after_request(after_request)
    app.teardown_request(teardown_request)
    start_http_server(port, addr)

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)

    monitor(app, port=8000)

    @app.route('/')
    def index():
        return "Hello"

    # Run the application!
    app.run()
