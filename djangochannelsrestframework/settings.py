from django.conf import settings

from rest_framework.settings import APISettings

DEFAULTS = {
    'DEFAULT_PAGE_SIZE': 25,
    'DEFAULT_PERMISSION_CLASSES': (
        'djangochannelsrestframework.permissions.AllowAny',
    )
}
IMPORT_STRINGS = (
    'DEFAULT_PERMISSION_CLASSES',
)

api_settings = APISettings(getattr(settings, 'DJANGO_CHANNELS_REST_API', None), DEFAULTS, IMPORT_STRINGS)
