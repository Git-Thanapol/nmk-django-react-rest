from .settings import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable media file storage side-effects
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Suppress logging noise
LOGGING = {}
