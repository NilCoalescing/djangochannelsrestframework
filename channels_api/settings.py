from django.conf import settings

from rest_framework.settings import APISettings

DEFAULTS = {
    'DEFAULT_FORMATTER_CLASS': 'channels_api.formatters.SimpleFormatter'
}

IMPORT_STRINGS = (
    'DEFAULT_FORMATTER_CLASS',
)

api_settings = APISettings(getattr(settings, 'CHANNELS_API', None), DEFAULTS, IMPORT_STRINGS)
