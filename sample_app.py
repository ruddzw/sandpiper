import sandpiper
from sandpiper import HttpResponse


def index(request):
    return HttpResponse('Hello from sandpiper!')


config = {
    'memcached_servers': ['localhost:11211'],
    'mongo_db': 'sample_app',
    'mongo_host': 'localhost',
    'mongo_port': '27017',
    'public_path': None,
    'template_path': None
}
routes = [(r'^/$', index)]


# Run with a WSGI server, e.g.:
# gunicorn --bind=127.0.0.1:8000 sample_app:app
# Then view at http://localhost:8000
app = sandpiper.get_wsgi_app(config, routes)
