import threading
from enum import Enum
from functools import partial
from typing import Dict, Any, Type, Set, Generator
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Model
from django.db.models.signals import pre_save, post_save, post_delete, \
    pre_delete
from django.dispatch import Signal

from djangochannelsrestframework.consumers import AsyncAPIConsumer


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
        self._group_names = None
        self._uuid = str(uuid4())

    async def __call__(self, *args, consumer=None, **kwargs):
        return await self.func(consumer, *args, observer=self, **kwargs)

    def __get__(self, parent, objtype):
        if parent is None:
            return self

        return ObjPartial(self, consumer=parent)

    def serialize(self, signal, *args, **kwargs) -> Dict[str, Any]:
        message = {}
        if self._serializer:
            message = self._serializer(self, signal, *args, **kwargs)
        message['type'] = self.func.__name__.replace('_', '.')

        return message

    def serializer(self, func):
        self._serializer = func
        return self

    async def subscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names(*args, consumer=consumer, **kwargs):
            await consumer.add_group(group_name)

    def group_names(self, *args, **kwargs) -> Generator[str, None, None]:
        if self._group_names:
            for group in self._group_names(*args, **kwargs):
                yield '{}-{}'.format(self._uuid, group)
            return
        raise NotImplementedError()

    def groups(self, func):
        self._group_names = func
        return self


class Observer(BaseObserver):
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
        for group_name in self.group_names(*args, **kwargs):
            async_to_sync(channel_layer.group_send)(group_name, message)

    def group_names(self, *args, **kwargs):
        if self._group_names:
            for group in self._group_names(*args, **kwargs):
                yield '{}-{}'.format(self._uuid, group)
            return
        yield '{}-{}-signal-{}'.format(
            self._uuid,
            self.func.__name__.replace('_', '.'),
            '.'.join(
                arg.lower().replace('_', '.') for arg in
                self.signal.providing_args
            )
        )


class Action(Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'


class ModelObserver(BaseObserver):

    def __init__(self, func, model_cls: Type[Model], **kwargs):
        super().__init__(func)
        self._model_cls = None
        self.model_cls = model_cls  # type: Type[Model]

    @property
    def model_cls(self) -> Type[Model]:
        return self._model_cls

    @model_cls.setter
    def model_cls(self, value: Type[Model]):
        was_none = self._model_cls is None
        self._model_cls = value

        if self._model_cls is not None and was_none:
            self._connect()

    def _connect(self):
        pre_save.connect(
            self.pre_save_receiver,
            sender=self.model_cls,
            dispatch_uid=id(self)
        )
        post_save.connect(
            self.post_save_receiver,
            sender=self.model_cls,
            dispatch_uid=id(self)
        )
        pre_delete.connect(self.pre_delete_receiver, sender=self.model_cls, dispatch_uid=id(self))
        post_delete.connect(self.post_delete_receiver, sender=self.model_cls, dispatch_uid=id(self))

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
            group_names = set(self.group_names(instance))

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
            new_group_names = set(self.group_names(instance))

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

    def group_names(self, *args, **kwargs):
        if self._group_names:
            for group in self._group_names(self, *args, **kwargs):
                yield '{}-{}'.format(self._uuid, group)
            return

        model_label = '{}.{}'.format(
            self.model_cls._meta.app_label.lower(),
            self.model_cls._meta.object_name.lower()
        ).lower().replace('_', '.')

        # one channel for all updates.
        yield '{}-{}-model-{}'.format(
            self._uuid,
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
