from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import Signal

from djangochannelsrestframework.observer.base_observer import BaseObserver


class Observer(BaseObserver):
    def __init__(self, func, signal: Signal = None, kwargs=None, partition: str = "*"):
        super().__init__(func, partition=partition)
        if kwargs is None:
            kwargs = {}
        self.signal = signal
        self.signal_kwargs = kwargs
        self._serializer = None
        self.signal.connect(self.handle, **self.signal_kwargs)

    def handle(self, signal, *args, **kwargs):
        message = self.serialize(signal, *args, **kwargs)
        channel_layer = get_channel_layer()
        for group_name in self.group_names_for_signal(*args, message=message, **kwargs):
            async_to_sync(channel_layer.group_send)(group_name, message)

    def group_names(self, *args, **kwargs):
        yield "{}-{}-signal-{}".format(
            self._stable_observer_id,
            self.func.__name__.replace("_", "."),
            ".".join(
                arg.lower().replace("_", ".") for arg in self.signal.providing_args
            ),
        )
