from copy import deepcopy

from django.db.models import Model
from functools import partial
from typing import Dict, Type, Optional, Set, List, Iterable

from channels.db import database_sync_to_async
from rest_framework import status

from djangochannelsrestframework.consumers import APIConsumerMetaclass
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import RetrieveModelMixin
from djangochannelsrestframework.observer import ModelObserver


class _GenericModelObserver:
    def __init__(self, func, **kwargs):
        self.func = func
        self._group_names = None
        self._serializer = None

    def bind_to_model(
        self, model_cls: Type[Model], name: str, many_to_many=False
    ) -> ModelObserver:
        observer = ModelObserver(
            func=self.func,
            model_cls=model_cls,
            partition=name,
            many_to_many=many_to_many,
        )
        observer.groups(self._group_names)
        observer.serializer(self._serializer)
        return observer

    def groups(self, func):
        self._group_names = func
        return self

    def serializer(self, func):
        self._serializer = func
        return self


class ObserverAPIConsumerMetaclass(APIConsumerMetaclass):
    def __new__(mcs, name, bases, body) -> Type[GenericAsyncAPIConsumer]:

        queryset = body.get("queryset", None)
        many_to_many = body.get("observer_many_to_many_relationships", False)
        if queryset is not None:
            for attr_name, attr in body.items():
                if isinstance(attr, _GenericModelObserver):
                    body[attr_name] = attr.bind_to_model(
                        model_cls=queryset.model,
                        name=f"{body['__module__']}.{name}.{attr_name}",
                        many_to_many=many_to_many,
                    )
            for base in bases:
                for attr_name in dir(base):
                    attr = getattr(base, attr_name)
                    if isinstance(attr, _GenericModelObserver):
                        body[attr_name] = attr.bind_to_model(
                            model_cls=queryset.model,
                            name=f"{body['__module__']}.{name}.{attr_name}",
                            many_to_many=many_to_many,
                        )

        return super().__new__(mcs, name, bases, body)


class ObserverConsumerMixin(metaclass=ObserverAPIConsumerMetaclass):
    observer_many_to_many_relationships = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_requests = {}  # type: Dict[str, Set[str]]

    def _subscribe(self, request_id: str, groups: Set[str]):
        for group in groups:
            request_ids = self.subscribed_requests.get(group, set())
            request_ids.add(request_id)
            self.subscribed_requests[group] = request_ids

    def _unsubscribe(self, request_id: str):
        to_remove = []
        for group, request_ids in self.subscribed_requests.items():
            request_ids.remove(request_id)
            if not request_ids:
                to_remove.append(group)

        self._unsubscribe_groups(to_remove)

    def _unsubscribe_groups(self, groups: Iterable[str]):
        for group in groups:
            try:
                self.subscribed_requests.pop(group)
            except KeyError:
                continue

    def _requests_for(self, group: Optional[str]) -> Set[str]:
        all_request_ids = set()
        if not group:
            for request_ids in self.subscribed_requests.values():
                all_request_ids = all_request_ids.union(request_ids)
            return all_request_ids
        return self.subscribed_requests.get(group, set())


class ObserverModelInstanceMixin(ObserverConsumerMixin, RetrieveModelMixin):
    """
    Use this as a mixing with :class:`~djangochannelsrestframework.generics.GenericAsyncAPIConsumer`.

    You can also set the ``observer_many_to_many_relationships = True`` class property to ensure many-to-many
    relationship changes are tracked by the subscription.

    .. code-block:: python

        # consumers.py
        from djangochannelsrestframework.consumers import GenericAsyncAPIConsumer
        from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin

        from .serializers import UserSerializer
        from .models import User

        class MyConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
            queryset = User.objects.all()
            serializer_class = UserSerializer
            observer_many_to_many_relationships = True

    """

    @action()
    async def subscribe_instance(self, request_id=None, **kwargs):
        """
        Subscribes the current consumer to updates for a specific model instance.

        This method retrieves the model instance based on the provided lookup parameters
        (`kwargs`), then subscribes the consumer to receive real-time updates related to
        that instance. The subscription is identified by a `request_id`, which must be provided.

        Args:
            request_id (str): A unique identifier for the subscription request.
            **kwargs: Lookup parameters used to retrieve the model instance.

        Raises:
            ValueError: If `request_id` is not provided.
        """
        if request_id is None:
            raise ValueError("request_id must have a value set")
        # subscribe!
        instance = await database_sync_to_async(self.get_object)(**kwargs)
        groups = set(await self.handle_instance_change.subscribe(instance=instance))
        self._subscribe(request_id, groups)

        return None, status.HTTP_201_CREATED

    @action()
    async def unsubscribe_instance(self, request_id: Optional[str] = None, **kwargs):
        """
        Unsubscribes the current consumer from updates for a specific model instance.

        This method removes the consumer's subscription to real-time updates for the given
        model instance. If a `request_id` is provided, only that specific subscription is removed.
        Otherwise, all subscriptions related to the instance are unsubscribed.

        Args:
            request_id (str, optional): A unique identifier for the subscription request.
            **kwargs: Lookup parameters used to retrieve the model instance.
        """
        instance = await database_sync_to_async(self.get_object)(**kwargs)
        groups = await self.handle_instance_change.unsubscribe(instance=instance)

        if request_id is None:
            self._unsubscribe_groups(groups)
        else:
            self._unsubscribe(request_id)

        return None, status.HTTP_204_NO_CONTENT

    @_GenericModelObserver
    async def handle_instance_change(
        self, message: Dict, group=None, action=None, **kwargs
    ):
        await self.handle_observed_action(
            action=action,
            group=group,
            **message,
        )

    @handle_instance_change.groups
    def handle_instance_change(self: ModelObserver, instance, *args, **kwargs):
        # one channel for all updates.
        yield "{}-model-{}-pk-{}".format(
            self.func.__name__.replace("_", "."), self.model_label, instance.pk
        )

    async def handle_observed_action(
        self, action: str, group: Optional[str] = None, **kwargs
    ):
        """
        run the action.
        """
        try:
            await self.check_permissions(action, **kwargs)
        except Exception as exc:
            await self.handle_exception(exc, action=action, request_id=None)

        for request_id in self._requests_for(group):
            try:
                reply = partial(self.reply, action=action, request_id=request_id)

                if action == "delete":
                    await reply(data=kwargs, status=204)
                    # send the delete
                    continue

                # the @action decorator will wrap non-async action into async ones.
                response = await self.retrieve(
                    request_id=request_id, action=action, **kwargs
                )

                if isinstance(response, tuple):
                    data, status = response
                    await reply(data=data, status=status)
            except Exception as exc:
                await self.handle_exception(exc, action=action, request_id=request_id)
