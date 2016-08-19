from django.conf import settings

from rest_framework.settings import APISettings

DEFAULTS = {
    'DEFAULT_PAGE_SIZE': 25
}
IMPORT_STRINGS = (
)

api_settings = APISettings(getattr(settings, 'CHANNELS_API', None), DEFAULTS, IMPORT_STRINGS)
