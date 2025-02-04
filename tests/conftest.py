from django.conf import settings


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "channels",
            "tests",
        ),
        SECRET_KEY="dog",
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
            }
        },
        MIDDLEWARE_CLASSES=[],
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer",
                "TEST_CONFIG": {
                    "expiry": 100500,
                },
            },
        }
    )
