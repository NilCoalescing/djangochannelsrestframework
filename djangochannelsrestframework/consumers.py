import json
import typing
from collections import defaultdict
from functools import partial
from typing import Dict, List, Type, Any, Set

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.http import HttpRequest, HttpResponse
from django.http.response import Http404
from django.template.response import SimpleTemplateResponse
from rest_framework.exceptions import PermissionDenied, MethodNotAllowed, APIException
from rest_framework.permissions import BasePermission as DRFBasePermission
from rest_framework.response import Response

from djangochannelsrestframework.settings import api_settings
from djangochannelsrestframework.permissions import BasePermission, WrappedDRFPermission
from djangochannelsrestframework.scope_utils import request_from_scope, ensure_async


class APIConsumerMetaclass(type):
    """
    Metaclass that records action methods
    """

    def __new__(mcs, name, bases, body):
        cls = type.__new__(mcs, name, bases, body)

        cls.available_actions = {}
        for method_name in dir(cls):
            attr = getattr(cls, method_name)
            is_action = getattr(attr, "action", False)
            if is_action:
                kwargs = getattr(attr, "kwargs", {})
                name = kwargs.get("name", method_name)
                cls.available_actions[name] = method_name

        return cls


class AsyncAPIConsumer(AsyncJsonWebsocketConsumer, metaclass=APIConsumerMetaclass):
    """
    This provides an async API consumer that is very inspired by DjangoRestFrameworks ViewSets.

    Attributes:
        permission_classes     An array for Permission classes

    """

    # use django rest framework permissions
    # The following policies may be set at either globally, or per-view.
    # take the default values set for django rest framework!

    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
    # type: List[Type[BasePermission]]

    groups = {}

    # mapping observer id -> group name ->
    _observer_group_to_request_id: Dict[str, Dict[str, Set[Any]]] = defaultdict(
        lambda: defaultdict(set)
    )

    async def websocket_connect(self, message):
        """
        Called when a WebSocket connection is opened.
        """
        try:
            for permission in await self.get_permissions(action="connect"):
                if not await ensure_async(permission.can_connect)(
                    scope=self.scope, consumer=self, message=message
                ):
                    raise PermissionDenied()
            await super().websocket_connect(message)
        except PermissionDenied:
            await self.close()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groups = set(self.groups or [])

        self._observer_group_to_request_id = defaultdict(lambda: defaultdict(set))

    async def add_group(self, name: str):
        """
        Add a group to the set of groups this consumer is subscribed to.
        """
        if not isinstance(self.groups, set):
            self.groups = set(self.groups)

        if name not in self.groups:
            await self.channel_layer.group_add(name, self.channel_name)
            self.groups.add(name)

    async def remove_group(self, name: str):
        """
        Remove a group to the set of groups this consumer is subscribed to.
        """
        if not isinstance(self.groups, set):
            self.groups = set(self.groups)

        if name in self.groups:
            await self.channel_layer.group_discard(name, self.channel_name)
            self.groups.remove(name)

    async def get_permissions(self, action: str, **kwargs):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        permission_instances = []
        for permission_class in self.permission_classes:
            instance = permission_class()

            # If the permission is an DRF permission instance
            if isinstance(instance, DRFBasePermission):
                instance = WrappedDRFPermission(instance)
            permission_instances.append(instance)

        return permission_instances

    async def check_permissions(self, action: str, **kwargs):
        """
        Check if the action should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in await self.get_permissions(action=action, **kwargs):

            if not await ensure_async(permission.has_permission)(
                scope=self.scope, consumer=self, action=action, **kwargs
            ):
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
                request_id=request_id,
            )
        elif exc == Http404 or isinstance(exc, Http404):
            await self.reply(
                action=action,
                errors=self._format_errors("Not found"),
                status=404,
                request_id=request_id,
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
        Handle a call for a given action.

        This method checks permissions and handles exceptions sending
        them back over the ws connection to the client.

        If there is no action listed on the consumer for this action name
        a `MethodNotAllowed` error is sent back over the ws connection.
        """
        try:
            await self.check_permissions(action, **kwargs)

            if action not in self.available_actions:
                raise MethodNotAllowed(method=action)

            method_name = self.available_actions[action]
            method = getattr(self, method_name)

            reply = partial(self.reply, action=action, request_id=request_id)

            # the @action decorator will wrap non-async action into async ones.

            response = await method(request_id=request_id, action=action, **kwargs)

            if isinstance(response, tuple):
                data, status = response
                await reply(data=data, status=status)

        except Exception as exc:
            await self.handle_exception(exc, action=action, request_id=request_id)

    async def receive_json(self, content: typing.Dict, **kwargs):
        request_id = content.pop("request_id")
        action, content = await self.get_action_name(content, **kwargs)
        await self.handle_action(action, request_id=request_id, **content)

    async def get_action_name(
        self, content: typing.Dict, **kwargs
    ) -> typing.Tuple[typing.Optional[str], typing.Dict]:
        """
        Retrieves the action name from the json message.

        Returns a tuple of the action name and the argumetns that is passed to the action.

        Override this method if you do not want to use `{"action": "action_name"}` as the way to describe actions.
        """
        action = content.pop("action")
        return (action, content)

    async def reply(
        self, action: str, data=None, errors=None, status=200, request_id=None
    ):
        """
        Send a json response back to the client.

        You should aim to include the `request_id` if possible as this helps clients link messages they have
        sent to responses.
        """

        if errors is None:
            errors = []

        payload = {
            "errors": errors,
            "data": data,
            "action": action,
            "response_status": status,
            "request_id": request_id,
        }

        await self.send_json(payload)


class DjangoViewAsConsumer(AsyncAPIConsumer):
    view = None

    @property
    def dumpy_url_config(self):
        return

    # maps actions to HTTP methods
    actions = {}  # type: Dict[str, str]

    async def handle_action(self, action: str, request_id: str, **kwargs):
        try:
            await self.check_permissions(action, **kwargs)

            if action not in self.actions:
                raise MethodNotAllowed(method=action)

            content, status = await self.call_view(action=action, **kwargs)

            await self.reply(
                action=action, request_id=request_id, data=content, status=status
            )

        except Exception as exc:
            await self.handle_exception(exc, action=action, request_id=request_id)

    @database_sync_to_async
    def call_view(self, action: str, **kwargs):
        request = request_from_scope(self.scope)

        args, view_kwargs = self.get_view_args(action=action, **kwargs)

        request.method = self.actions[action]
        request.POST = json.dumps(kwargs.get("data", {}))

        for key, value in kwargs.get("query", {}).items():
            if isinstance(value, list):
                request.GET.setlist(key, value)
            else:
                request.GET[key] = value

        view = getattr(self.__class__, "view")

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
                response_content = response_content.decode("utf-8")
            except Exception as e:
                response_content = response_content.hex()
        return response_content, status

    def get_view_args(self, action: str, **kwargs):
        return [], kwargs.get("parameters", {})


def view_as_consumer(
    wrapped_view: typing.Callable[[HttpRequest], HttpResponse],
    mapped_actions: typing.Optional[typing.Dict[str, str]] = None,
) -> DjangoViewAsConsumer:
    """
    Wrap a django View to be used over a json ws connection.

    .. code-block:: python

            websocket_urlpatterns = [
                re_path(r"^user/$", view_as_consumer(UserViewSet.as_view()))
            ]

    This exposes the django view to your websocket connection so that you can send messages:

    .. code-block:: javascript

        {
         action: "retrieve",
         request_id: 42,
         query: {pk: 92}
        }

    The default mapping for actions is:

    * ``create`` - ``PUT``
    * ``update`` - ``PATCH``
    * ``list`` - ``GET``
    * ``retrieve`` - ``GET``

    Providing a `query` dict in the websocket messages results in the values of this dict being writen to the `GET`
    property of the request within your django view.

    Providing a `parameters` dict within the websocket messages results in these values being passed as kwargs to the
    view method (in the same way that url parameters would normally be extracted).

    """
    if mapped_actions is None:
        mapped_actions = {
            "create": "PUT",
            "update": "PATCH",
            "list": "GET",
            "retrieve": "GET",
        }

    class DjangoViewWrapper(DjangoViewAsConsumer):
        view = wrapped_view
        actions = mapped_actions

    return DjangoViewWrapper()
