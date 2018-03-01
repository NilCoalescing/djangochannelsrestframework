from functools import partial
from typing import Dict, Any

from asgiref.sync import async_to_sync
from channels.consumer import AsyncConsumer
from channels.layers import get_channel_layer
from django.dispatch import Signal


class Observer:
    def __init__(self, func, signal: Signal=None, kwargs=None):
        if kwargs is None:
            kwargs = {}
        self.func = func
        self.signal = signal
        self.signal_kwargs = kwargs
        self._serializer = None
        self.signal.connect(
            self.handle, **self.signal_kwargs
        )

    async def __call__(self, *args, **kwargs):
        return await self.func(*args, **kwargs)

    def serialize(self, signal, *args, **kwargs) -> Dict[str, Any]:
        message = {}
        if self._serializer:
            message = self._serializer(self, signal, *args, **kwargs)
        message['type'] = self.func.__name__.replace('_', '.')

        return message

    def serializer(self, func):
        self._serializer = func

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

    def __get__(self, parent, objtype):

        if parent is None:
            return self

        return partial(self.__call__, parent)

    async def subscribe(self, consumer: AsyncConsumer, *args, **kwargs):
        await consumer.channel_layer.group_add(
            self.channel_name(*args, **kwargs),
            consumer.channel_name
        )
        print('subscribed', consumer, self.channel_name(*args, **kwargs), consumer.channel_name)


def observer(signal, **kwargs):
    return partial(Observer, signal=signal, kwargs=kwargs)
