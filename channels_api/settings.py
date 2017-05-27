from django.conf import settings

from rest_framework.settings import APISettings

DEFAULTS = {
    'DEFAULT_PAGE_SIZE': 25,
    'DEFAULT_PERMISSION_CLASSES': (
        'channels_api.permissions.AllowAny',
    )
}
IMPORT_STRINGS = (
    'DEFAULT_PERMISSION_CLASSES',
)

api_settings = APISettings(getattr(settings, 'CHANNELS_API', None), DEFAULTS, IMPORT_STRINGS)
