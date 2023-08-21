from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed, APIException
from django.utils.translation import gettext_lazy as _


class ActionMissingException(APIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    default_detail = _("Unable to find action in message body.")
    default_code = "method_not_allowed"
