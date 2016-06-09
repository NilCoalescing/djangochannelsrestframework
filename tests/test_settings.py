SECRET_KEY = 'dog'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'asgiref.inmemory.ChannelLayer',
        'ROUTING': [],
    },
}

MIDDLEWARE_CLASSES = []

INSTALLED_APPS = ('tests', )
