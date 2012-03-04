import os
import random

import sandpiper
from sandpiper import db, HttpTemplateResponse


CONSONANTS = 'bcdfghjklmnpqrstvwxyz'
VOWELS = 'aeiou'


# Helper: generates a random CVCVC name
def random_name():
    return (random.choice(CONSONANTS) +
        random.choice(VOWELS) +
        random.choice(CONSONANTS) +
        random.choice(VOWELS) +
        random.choice(CONSONANTS))


# Model
class BirdLover(db.Model):
    fields = ['name', 'favorite_bird']
    defaults = {'favorite_bird': 'sandpiper'}
    key = 'name'
    collection = 'birdlovers'


# Request handler
def index(request):
    birdlover = BirdLover(name=random_name())
    birdlover.save()
    return HttpTemplateResponse('index.html', {'bird_lovers': BirdLover.find()})


# Configuration and Routes
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


# Create a WSGI App
# Run with a WSGI server, e.g.:
# gunicorn sample_app:app
# Then view at http://localhost:8000
app = sandpiper.get_wsgi_app(config, routes)
