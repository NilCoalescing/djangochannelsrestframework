import asyncio
import typing
from functools import partial

from typing import List, Type

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


from rest_framework.exceptions import PermissionDenied, MethodNotAllowed, \
    APIException

from channels_api.permissions import BasePermission
from channels_api.settings import api_settings


class APIViewMetaclass(type):
    """
    Metaclass that records action methods
    """

    def __new__(mcs, name, bases, body):
        cls = type.__new__(mcs, name, bases, body)

        cls.available_actions = {}
        for method_name in dir(cls):
            attr = getattr(cls, method_name)
            is_action = getattr(attr, 'action', False)
            if is_action:
                kwargs = getattr(attr, 'kwargs', {})
                name = kwargs.get('name', method_name)
                cls.available_actions[name] = method_name

        return cls


def ensure_async(method: typing.Callable):
    if asyncio.iscoroutinefunction(method):
        return method
    return database_sync_to_async(method)


class AsyncWebsocketAPIView(AsyncJsonWebsocketConsumer,
                            metaclass=APIViewMetaclass):
    """
    Be very inspired by django rest framework ViewSets
    """

    # use django rest framework permissions
    # The following policies may be set at either globally, or per-view.
    # take the default values set for django rest framework!

    permission_classes = api_settings.\
        DEFAULT_PERMISSION_CLASSES  # type: List[Type[BasePermission]]

    async def get_permissions(self, action: str, **kwargs):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        return [permission() for permission in self.permission_classes]

    async def check_permissions(self, action: str, **kwargs):
        """
        Check if the action should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in await self.get_permissions(action=action, **kwargs):

            if not await ensure_async(permission.has_permission)(
                    scope=self.scope, consumer=self, action=action, **kwargs):
                raise PermissionDenied()

    async def handle_exception(self, exc: Exception, action: str, request_id):
        """
        Handle any exception that occurs, by sending an appropriate message
        """
        if isinstance(exc, APIException):
            await self.reply(
                action=action,
                errors=self._format_errors(exc.detail),
                status=exc.status_code,
                request_id=request_id
            )
        else:
            raise exc

    def _format_errors(self, errors):
        if isinstance(errors, list):
            return errors
        elif isinstance(errors, str):
            return [errors]
        elif isinstance(errors, dict):
            return [errors]

    async def handle_action(self, action: str, request_id: str, **kwargs):
        """
        run the action.
        """
        try:
            await self.check_permissions(action, **kwargs)

            if action not in self.available_actions:
                raise MethodNotAllowed(method=action)

            method_name = self.available_actions[action]
            method = getattr(self, method_name)

            reply = partial(self.reply, action=action, request_id=request_id)

            # the @action decorator will wrap non-async action into async ones.

            await method(reply=reply, **kwargs)

        except Exception as exc:
            await self.handle_exception(
                exc,
                action=action,
                request_id=request_id
            )

    async def receive_json(self, content: typing.Dict, **kwargs):
        """
        Called with decoded JSON content.
        """
        # TODO assert format, if does not match return message.
        request_id = content.pop('request_id')
        action = content.pop('action')
        await self.handle_action(action, request_id=request_id, **content)

    async def reply(self,
                    action: str,
                    data=None,
                    errors=None,
                    status=200,
                    request_id=None):

        if errors is None:
            errors = []

        payload = {
            'errors': errors,
            'data': data,
            'action': action,
            'response_status': status,
            'request_id': request_id,
        }

        await self.send_json(
            payload
        )
