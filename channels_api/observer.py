import threading
from enum import Enum
from functools import partial
from typing import Dict, Any, Type, Set

from asgiref.sync import async_to_sync
from channels.consumer import AsyncConsumer
from channels.layers import get_channel_layer
from django.db.models import Model
from django.db.models.signals import pre_save, post_save, post_delete, \
    pre_delete
from django.dispatch import Signal


class ObjPartial(partial):
    def __getattribute__(self, name):
        try:
            item = super().__getattribute__(name)
        except AttributeError:
            return partial(getattr(self.func, name), *self.args, **self.keywords)
        return item


class BaseObserver:
    def __init__(self, func):
        self.func = func
        self._serializer = None

    async def __call__(self, *args, **kwargs):
        return await self.func(*args, **kwargs)

    def __get__(self, parent, objtype):
        if parent is None:
            return self

        return ObjPartial(self, parent)

    def serialize(self, signal, *args, **kwargs) -> Dict[str, Any]:
        message = {}
        if self._serializer:
            message = self._serializer(self, signal, *args, **kwargs)
        message['type'] = self.func.__name__.replace('_', '.')

        return message

    def serializer(self, func):
        self._serializer = func

    async def subscribe(self, consumer: AsyncConsumer, *args, **kwargs):
        raise NotImplementedError()


class  Observer(BaseObserver):
    def __init__(self, func, signal: Signal=None, kwargs=None):
        super().__init__(func)
        if kwargs is None:
            kwargs = {}
        self.signal = signal
        self.signal_kwargs = kwargs
        self._serializer = None
        self.signal.connect(
            self.handle, **self.signal_kwargs
        )

    def handle(self, signal, *args, **kwargs):
        message = self.serialize(signal, *args, **kwargs)
        channel_layer = get_channel_layer()
        group_name = self.channel_name(signal, *args, **kwargs)
        async_to_sync(channel_layer.group_send)(group_name, message)

    def channel_name(self, *args, **kwargs):
        return '{}-signal-{}'.format(
            self.func.__name__.replace('_', '.'),
            '.'.join(
                arg.lower().replace('_', '.') for arg in
                self.signal.providing_args
            )
        )

    async def subscribe(self, consumer: AsyncConsumer, *args, **kwargs):
        await consumer.channel_layer.group_add(
            self.channel_name(*args, **kwargs),
            consumer.channel_name
        )


def observer(signal, **kwargs):
    return partial(Observer, signal=signal, kwargs=kwargs)


class Action(Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'


class ModelObserver(BaseObserver):

    def __init__(self, func, model_cls: Type[Model], **kwargs):
        super().__init__(func)
        self.model_cls = model_cls  # type: Type[Model]
        self._connect()

    def _connect(self):
        pre_save.connect(self.pre_save_receiver, sender=self.model_cls)
        post_save.connect(self.post_save_receiver, sender=self.model_cls)
        pre_delete.connect(self.pre_delete_receiver, sender=self.model_cls)
        post_delete.connect(self.post_delete_receiver, sender=self.model_cls)

    def pre_save_receiver(self, instance: Model, **kwargs):
        creating = instance._state.adding
        self.pre_change_receiver(
            instance,
            Action.CREATE if creating else Action.UPDATE
        )

    def post_save_receiver(self, instance: Model, created: bool, **kwargs):
        self.post_change_receiver(
            instance,
            Action.CREATE if created else Action.UPDATE,
            **kwargs
        )

    def pre_delete_receiver(self, instance: Model, **kwargs):
        self.pre_change_receiver(
            instance,
            Action.DELETE
        )

    def post_delete_receiver(self, instance: Model, **kwargs):
        self.post_change_receiver(instance, Action.DELETE, **kwargs)

    def pre_change_receiver(self, instance: Model, action: Action):
        """
        Entry point for triggering the old_binding from save signals.
        """
        if action == Action.CREATE:
            group_names = set()
        else:
            group_names = set(self.channel_names(instance))

        # use a thread local dict to be safe...
        if not hasattr(instance, '__instance_groups'):
            instance.__instance_groups = threading.local()
            instance.__instance_groups.observers = {}
        if not hasattr(instance.__instance_groups, 'observers'):
            instance.__instance_groups.observers = {}

        instance.__instance_groups.observers[self] = group_names

    def post_change_receiver(self, instance: Model, action: Action, **kwargs):
        """
        Triggers the old_binding to possibly send to its group.
        """
        try:
            old_group_names = instance.__instance_groups.observers[self]
        except (ValueError, KeyError):
            old_group_names = set()

        if action == Action.DELETE:
            new_group_names = set()
        else:
            new_group_names = set(self.channel_names(instance))

        # if post delete, new_group_names should be []

        # Django DDP had used the ordering of DELETE, UPDATE then CREATE for good reasons.
        self.send_messages(
            instance,
            old_group_names - new_group_names,
            Action.DELETE,
            **kwargs
        )
        # the object has been updated so that its groups are not the same.
        self.send_messages(
            instance,
            old_group_names & new_group_names,
            Action.UPDATE,
            **kwargs
        )
        #
        self.send_messages(
            instance,
            new_group_names - old_group_names,
            Action.CREATE,
            **kwargs
        )

    def send_messages(self,
                      instance: Model,
                      group_names: Set[str],
                      action: Action, **kwargs):
        if not group_names:
            return
        message = self.serialize(instance, action, **kwargs)
        channel_layer = get_channel_layer()
        for group_name in group_names:
            async_to_sync(channel_layer.group_send)(group_name, message)

    async def subscribe(self, consumer: AsyncConsumer, *args, **kwargs):
        for group_name in self.channel_names(*args, **kwargs):
            await consumer.channel_layer.group_add(
                group_name,
                consumer.channel_name
            )

    def channel_names(self, instance=None, **kwargs):
        model_label = '{}.{}'.format(
            self.model_cls._meta.app_label.lower(),
            self.model_cls._meta.object_name.lower()
        ).lower().replace('_', '.')

        # one channel for all updates.
        yield '{}-model-{}'.format(
            self.func.__name__.replace('_', '.'),
            model_label,
        )

    def serialize(self, instance, action, **kwargs) -> Dict[str, Any]:
        message = {}
        if self._serializer:
            message = self._serializer(self, instance, action, **kwargs)
        else:
            message['pk'] = instance.pk
        message['type'] = self.func.__name__.replace('_', '.')
        message['action'] = action.value
        return message


def model_observer(model: Type[Model], **kwargs):
    return partial(ModelObserver, model_cls=model, kwargs=kwargs)
