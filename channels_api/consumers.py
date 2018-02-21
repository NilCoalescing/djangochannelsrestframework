import asyncio
import json
import re
import typing
from functools import partial

from typing import List, Type

from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer, \
    WebsocketConsumer
from django.conf.urls import url
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase, Http404
from django.template.response import SimpleTemplateResponse
from django.urls import Resolver404, reverse, resolve

from rest_framework.exceptions import PermissionDenied, MethodNotAllowed, \
    APIException, NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from channels_api.permissions import BasePermission
from channels_api.settings import api_settings


class APIConsumerMetaclass(type):
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


class AsyncAPIConsumer(AsyncJsonWebsocketConsumer,
                       metaclass=APIConsumerMetaclass):
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
        elif exc == Http404 or isinstance(exc, Http404):
            await self.reply(
                action=action,
                errors=self._format_errors('Not found'),
                status=404,
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


class DjangoViewAsConsumer(AsyncAPIConsumer):

    view = None

    @property
    def dumpy_url_config(self):
        return

    # maps actions to HTTP methods
    actions = {}  # type: Dict[str, str]

    async def receive_json(self, content: typing.Dict, **kwargs):
        """
        Called with decoded JSON content.
        """
        # TODO assert format, if does not match return message.
        request_id = content.pop('request_id')
        action = content.pop('action')
        await self.handle_action(action, request_id=request_id, **content)

    async def handle_action(self, action: str, request_id: str, **kwargs):
        """
        run the action.
        """
        try:
            await self.check_permissions(action, **kwargs)

            if action not in self.actions:
                raise MethodNotAllowed(method=action)

            content, status = await self.call_view(
                action=action,
                **kwargs
            )

            await self.reply(
                action=action,
                request_id=request_id,
                data=content,
                status=status
            )

        except Exception as exc:
            await self.handle_exception(
                exc,
                action=action,
                request_id=request_id
            )

    @database_sync_to_async
    def call_view(self,
                  action: str,
                  **kwargs):

        request = HttpRequest()
        request.path = self.scope.get('path')
        request.session = self.scope.get('session', None)

        request.META['HTTP_CONTENT_TYPE'] = 'application/json'
        request.META['HTTP_ACCEPT'] = 'application/json'

        for (header_name, value) in self.scope.get('headers', []):
            request.META[header_name.decode('utf-8')] = value.decode('utf-8')

        args, view_kwargs = self.get_view_args(action=action, **kwargs)

        request.method = self.actions[action]
        request.POST = json.dumps(kwargs.get('data', {}))
        if self.scope.get('cookies'):
            request.COOKIES = self.scope.get('cookies')

        view = getattr(self.__class__, 'view')

        response = view(request, *args, **view_kwargs)

        status = response.status_code

        if isinstance(response, Response):
            data = response.data
            try:
                # check if we can json encode it!
                # there must be a better way fo doing this?
                json.dumps(data)
                return data, status
            except Exception as e:
                pass
        if isinstance(response, SimpleTemplateResponse):
            response.render()

        response_content = response.content
        if isinstance(response_content, bytes):
            try:
                response_content = response_content.decode('utf-8')
            except Exception as e:
                response_content = response_content.hex()
        return response_content, status

    def get_view_args(self, action: str, **kwargs):
        return [], {}


def view_as_consumer(
        wrapped_view: typing.Callable[[HttpRequest], HttpResponse],
        mapped_actions: typing.Optional[
            typing.Dict[str, str]
        ]=None) -> Type[AsyncConsumer]:
    """
    Wrap a django View so that it will be triggered by actions over this json
     websocket consumer.
    """
    if mapped_actions is None:
        mapped_actions = {
            'create': 'PUT',
            'update': 'PATCH',
            'list': 'GET',
            'retrieve': 'GET'
        }

    class DjangoViewWrapper(DjangoViewAsConsumer):
        view = wrapped_view
        actions = mapped_actions

    return DjangoViewWrapper
