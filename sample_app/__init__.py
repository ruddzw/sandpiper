import os

import sandpiper
from sandpiper import HttpTemplateResponse


def index(request):
    return HttpTemplateResponse('index.html', {})


app_dir = os.path.dirname(__file__)
config = {
    'memcached_servers': ['localhost:11211'],
    'mongo_db': 'sample_app',
    'mongo_host': 'localhost',
    'mongo_port': '27017',
    'public_path': os.path.join(app_dir, 'public'),
    'template_path': os.path.join(app_dir, 'templates')
}
routes = [(r'^/$', index)]


# Run with a WSGI server, e.g.:
# gunicorn sample_app:app
# Then view at http://localhost:8000
app = sandpiper.get_wsgi_app(config, routes)
