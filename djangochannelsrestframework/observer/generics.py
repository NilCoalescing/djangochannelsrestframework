from functools import partial
from typing import Dict, Type

from channels.db import database_sync_to_async
from rest_framework import status

from djangochannelsrestframework.consumers import APIConsumerMetaclass
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import RetrieveModelMixin
from djangochannelsrestframework.observer import ModelObserver


class GenericModelObserver(ModelObserver):

    def __init__(self, func, **kwargs):
        super().__init__(func=func, model_cls=None, **kwargs)


generic_model_observer = GenericModelObserver


class ObserverAPIConsumerMetaclass(APIConsumerMetaclass):
    def __new__(mcs, name, bases, body) -> Type[GenericAsyncAPIConsumer]:
        cls = super().__new__(mcs, name, bases, body)  # type: Type[GenericAsyncAPIConsumer]

        if issubclass(cls, GenericAsyncAPIConsumer):
            for method_name in dir(cls):
                attr = getattr(cls, method_name)
                if isinstance(attr, GenericModelObserver):
                    if getattr(cls, 'queryset') is not None:
                        if attr.model_cls is None:
                            attr.model_cls = cls.queryset.model
                        elif attr.model_cls != cls.queryset.model:
                            raise ValueError('Subclasses of observed consumers'
                                             ' cant change the model class')
        return cls


class ObserverConsumerMixin(metaclass=ObserverAPIConsumerMetaclass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_requests = {}  # type: Dict[function, str]


class ObserverModelInstanceMixin(ObserverConsumerMixin, RetrieveModelMixin):

    @action()
    async def subscribe_instance(self, request_id=None, **kwargs):
        if request_id is None:
            raise ValueError('request_id must have a value set')
        # subscribe!
        instance = await database_sync_to_async(self.get_object)(**kwargs)
        await self.handle_instance_change.subscribe(instance=instance)
        self.subscribed_requests[self.__class__.handle_instance_change] = request_id

        return None, status.HTTP_201_CREATED

    @generic_model_observer
    async def handle_instance_change(self, message, **kwargs):
        action = message.pop('action')
        message.pop('type')

        await self.handle_observed_action(
            action=action,
            request_id=self.subscribed_requests.get(
                self.__class__.handle_instance_change
            ),
            **message
        )

    @handle_instance_change.groups
    def handle_instance_change(self: ModelObserver, instance, *args, **kwargs):

        model_label = '{}.{}'.format(
            self.model_cls._meta.app_label.lower(),
            self.model_cls._meta.object_name.lower()
        ).lower().replace('_', '.')

        # one channel for all updates.
        yield '{}-model-{}-pk-{}'.format(
            self.func.__name__.replace('_', '.'),
            model_label,
            instance.pk
        )

    async def handle_observed_action(self,
                                     action: str, request_id: str, **kwargs):
        """
        run the action.
        """
        try:
            await self.check_permissions(action, **kwargs)

            reply = partial(self.reply, action=action, request_id=request_id)

            if action == 'delete':
                await reply(data=kwargs, status=204)
                # send the delete
                return

            # the @action decorator will wrap non-async action into async ones.

            response = await self.retrieve(
                request_id=request_id,
                action=action,
                **kwargs
            )

            if isinstance(response, tuple):
                data, status = response
                await reply(
                    data=data,
                    status=status
                )

        except Exception as exc:
            await self.handle_exception(
                exc,
                action=action,
                request_id=request_id
            )
