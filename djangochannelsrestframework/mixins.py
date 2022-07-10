from typing import Any, Tuple, Dict, Optional, OrderedDict, Union

from rest_framework import status
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

from djangochannelsrestframework.settings import api_settings
from djangochannelsrestframework.decorators import action


class CreateModelMixin:
    """ Create model mixin."""

    @action()
    def create(self, data: dict, **kwargs) -> Tuple[ReturnDict, int]:
        """Create action.

        Args:
            data: model data to create.

        Returns:
            Tuple with the serializer data and the status code.

        Examples:
            .. code-block:: python

                #! consumers.py
                from .models import User
                from .serializers import UserSerializer
                from djangochannelsrestframework import permissions
                from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
                from djangochannelsrestframework.mixins import CreateModelMixin

                class LiveConsumer(CreateModelMixin, GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    permission_classes = (permissions.AllowAny,)

            .. code-block:: python

                #! routing.py
                from django.urls import re_path
                from .consumers import LiveConsumer

                websocket_urlpatterns = [
                    re_path(r'^ws/$', LiveConsumer.as_asgi()),
                ]

            .. code-block:: javascript

                // html
                const ws = new WebSocket("ws://localhost:8000/ws/")
                ws.send(JSON.stringify({
                    action: "create",
                    request_id: new Date().getTime(),
                    data: {
                        username: "test",
                        password1: "testpassword123",
                        password2: "testpassword123",
                    }
                }))
                /* The response will be something like this.
                {
                    "action": "create",
                    "errors": [],
                    "response_status": 201,
                    "request_id": 150060530,
                    "data": {'username': 'test', 'id': 42,},
                }
                */
        """

        serializer = self.get_serializer(data=data, action_kwargs=kwargs)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer, **kwargs)
        return serializer.data, status.HTTP_201_CREATED

    def perform_create(self, serializer, **kwargs):
        serializer.save()


class ListModelMixin:
    """List model mixin"""

    @action()
    def list(self, **kwargs) -> Tuple[ReturnList, int]:
        """List action.

        Returns:
            Tuple with the list of serializer data and the status code.

        Examples:
            .. code-block:: python

                #! consumers.py
                from .models import User
                from .serializers import UserSerializer
                from djangochannelsrestframework import permissions
                from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
                from djangochannelsrestframework.mixins import ListModelMixin

                class LiveConsumer(ListModelMixin, GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    permission_classes = (permissions.AllowAny,)

            .. code-block:: python

                #! routing.py
                from django.urls import re_path
                from .consumers import LiveConsumer

                websocket_urlpatterns = [
                    re_path(r'^ws/$', LiveConsumer.as_asgi()),
                ]

            .. code-block:: javascript

                // html
                const ws = new WebSocket("ws://localhost:8000/ws/")
                ws.send(JSON.stringify({
                    action: "list",
                    request_id: new Date().getTime(),
                }))
                /* The response will be something like this.
                {
                    "action": "list",
                    "errors": [],
                    "response_status": 200,
                    "request_id": 1500000,
                    "data": [
                        {"email": "42@example.com", "id": 1, "username": "test1"},
                        {"email": "45@example.com", "id": 2, "username": "test2"},
                    ],
                }
                */
        """
        queryset = self.filter_queryset(self.get_queryset(**kwargs), **kwargs)
        serializer = self.get_serializer(
            instance=queryset, many=True, action_kwargs=kwargs
        )
        return serializer.data, status.HTTP_200_OK


class RetrieveModelMixin:
    """Retrieve model mixin"""

    @action()
    def retrieve(self, **kwargs) -> Tuple[ReturnDict, int]:
        """Retrieve action.

        Returns:
            Tuple with the serializer data and the status code.

        Examples:
            .. code-block:: python

                #! consumers.py
                from .models import User
                from .serializers import UserSerializer
                from djangochannelsrestframework import permissions
                from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
                from djangochannelsrestframework.mixins import RetrieveModelMixin

                class LiveConsumer(RetrieveModelMixin, GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    permission_classes = (permissions.AllowAny,)

            .. code-block:: python

                #! routing.py
                from django.urls import re_path
                from .consumers import LiveConsumer

                websocket_urlpatterns = [
                    re_path(r'^ws/$', LiveConsumer.as_asgi()),
                ]

            .. code-block:: javascript

                // html
                const ws = new WebSocket("ws://localhost:8000/ws/")
                ws.send(JSON.stringify({
                    action: "retrieve",
                    request_id: new Date().getTime(),
                    pk: 1,
                }))
                /* The response will be something like this.
                {
                    "action": "retrieve",
                    "errors": [],
                    "response_status": 200,
                    "request_id": 1500000,
                    "data": {"email": "42@example.com", "id": 1, "username": "test1"},
                }
                */
        """
        instance = self.get_object(**kwargs)
        serializer = self.get_serializer(instance=instance, action_kwargs=kwargs)
        return serializer.data, status.HTTP_200_OK


class UpdateModelMixin:
    """Update model mixin"""

    @action()
    def update(self, data: dict, **kwargs) -> Tuple[ReturnDict, int]:
        """Retrieve action.

        Returns:
            Tuple with the serializer data and the status code.

        Examples:
            .. code-block:: python

                #! consumers.py
                from .models import User
                from .serializers import UserSerializer
                from djangochannelsrestframework import permissions
                from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
                from djangochannelsrestframework.mixins import UpdateModelMixin

                class LiveConsumer(UpdateModelMixin, GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    permission_classes = (permissions.AllowAny,)

            .. code-block:: python

                #! routing.py
                from django.urls import re_path
                from .consumers import LiveConsumer

                websocket_urlpatterns = [
                    re_path(r'^ws/$', LiveConsumer.as_asgi()),
                ]

            .. code-block:: javascript

                // html
                const ws = new WebSocket("ws://localhost:8000/ws/")
                ws.send(JSON.stringify({
                    action: "update",
                    request_id: new Date().getTime(),
                    pk: 1,
                    data: {
                        username: "test edited",
                    },
                }))
                /* The response will be something like this.
                {
                    "action": "update",
                    "errors": [],
                    "response_status": 200,
                    "request_id": 1500000,
                    "data": {"email": "42@example.com", "id": 1, "username": "test edited"},
                }
                */
        """
        instance = self.get_object(data=data, **kwargs)

        serializer = self.get_serializer(
            instance=instance, data=data, action_kwargs=kwargs, partial=False
        )

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer, **kwargs)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return serializer.data, status.HTTP_200_OK

    def perform_update(self, serializer, **kwargs):
        serializer.save()


class PatchModelMixin:
    """Patch model mixin"""

    @action()
    def patch(self, data: dict, **kwargs) -> Tuple[ReturnDict, int]:
        """Patch action.

        Returns:
            Tuple with the serializer data and the status code.

        Examples:
            .. code-block:: python

                #! consumers.py
                from .models import User
                from .serializers import UserSerializer
                from djangochannelsrestframework import permissions
                from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
                from djangochannelsrestframework.mixins import PatchModelMixin

                class LiveConsumer(PatchModelMixin, GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    permission_classes = (permissions.AllowAny,)

            .. code-block:: python

                #! routing.py
                from django.urls import re_path
                from .consumers import LiveConsumer

                websocket_urlpatterns = [
                    re_path(r'^ws/$', LiveConsumer.as_asgi()),
                ]

            .. code-block:: javascript

                // html
                const ws = new WebSocket("ws://localhost:8000/ws/")
                ws.send(JSON.stringify({
                    action: "patch",
                    request_id: new Date().getTime(),
                    pk: 1,
                    data: {
                        email: "00@example.com",
                    },
                }))
                /* The response will be something like this.
                {
                    "action": "patch",
                    "errors": [],
                    "response_status": 200,
                    "request_id": 150000,
                    "data": {"email": "00@example.com", "id": 1, "username": "test1"},
                }
                */
        """
        instance = self.get_object(data=data, **kwargs)

        serializer = self.get_serializer(
            instance=instance, data=data, action_kwargs=kwargs, partial=True
        )

        serializer.is_valid(raise_exception=True)
        self.perform_patch(serializer, **kwargs)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return serializer.data, status.HTTP_200_OK

    def perform_patch(self, serializer, **kwargs):
        serializer.save()


class DeleteModelMixin:
    """Delete model mixin"""

    @action()
    def delete(self, **kwargs) -> Tuple[None, int]:
        """Retrieve action.

        Returns:
            Tuple with the serializer data and the status code.

        Examples:
            .. code-block:: python

                #! consumers.py
                from .models import User
                from .serializers import UserSerializer
                from djangochannelsrestframework import permissions
                from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
                from djangochannelsrestframework.mixins import DeleteModelMixin

                class LiveConsumer(DeleteModelMixin, GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    permission_classes = (permissions.AllowAny,)

            .. code-block:: python

                #! routing.py
                from django.urls import re_path
                from .consumers import LiveConsumer

                websocket_urlpatterns = [
                    re_path(r'^ws/$', LiveConsumer.as_asgi()),
                ]

            .. code-block:: javascript

                // html
                const ws = new WebSocket("ws://localhost:8000/ws/")
                ws.send(JSON.stringify({
                    action: "delete",
                    request_id: new Date().getTime(),
                    pk: 1,
                }))
                /* The response will be something like this.
                {
                    "action": "delete",
                    "errors": [],
                    "response_status": 204,
                    "request_id": 150000,
                    "data": null,
                }
                */
        """
        instance = self.get_object(**kwargs)

        self.perform_delete(instance, **kwargs)
        return None, status.HTTP_204_NO_CONTENT

    def perform_delete(self, instance, **kwargs):
        instance.delete()


class PaginatedModelListMixin(ListModelMixin):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS

    @action()
    def list(self, **kwargs):
        queryset = self.filter_queryset(self.get_queryset(**kwargs), **kwargs)
        page = self.paginate_queryset(queryset, **kwargs)
        if page is not None:
            serializer = self.get_serializer(
                instance=page, many=True, action_kwargs=kwargs
            )
            return self.get_paginated_response(serializer.data), status.HTTP_200_OK

        serializer = self.get_serializer(
            instance=queryset, many=True, action_kwargs=kwargs
        )
        return serializer.data, status.HTTP_200_OK

    @property
    def paginator(self) -> Optional[any]:
        """Gets the paginator class

        Returns:
            Pagination class. Optional.
        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset, **kwargs: Dict) -> Optional[Any]:
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.scope, view=self, **kwargs
        )

    def get_paginated_response(
        self, data: Union[ReturnDict, ReturnList]
    ) -> OrderedDict:
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)


class StreamedPaginatedListMixin(PaginatedModelListMixin):
    @action()
    async def list(self, action, request_id, **kwargs):
        data, status = await super().list(
            action=action, request_id=request_id, **kwargs
        )

        await self.reply(action=action, data=data, status=status, request_id=request_id)

        count = data.get("count", 0)
        limit = data.get("limit", 0)
        offset = data.get("offset", 0)

        if offset < (count - limit):
            kwargs["offset"] = limit + offset

            await self.list(action=action, request_id=request_id, **kwargs)
