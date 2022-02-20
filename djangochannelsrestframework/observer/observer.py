from copy import deepcopy

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import Signal

from djangochannelsrestframework.observer.base_observer import BaseObserver

from typing import Dict, Generator, Optional


class Observer(BaseObserver):

    signal: Signal
    signal_kwargs: Optional[Dict]

    def __init__(self, func, signal: Signal = None, kwargs=None, partition: str = "*"):
        super().__init__(func, partition=partition)
        if kwargs is None:
            kwargs = {}
        self.signal = signal
        self.signal_kwargs = kwargs
        self._serializer = None
        self.signal.connect(self.handle, **self.signal_kwargs)

    def handle(self, signal, *args, **kwargs):
        """Handler method pass to the signal connection

        This method if fired by the signal, it sends the serialized message, to each group name.

        Args:
            signal: signal instance
            args: listed arguments.
        """
        message = self.serialize(signal, *args, **kwargs)
        channel_layer = get_channel_layer()
        for group_name in self.group_names_for_signal(*args, message=message, **kwargs):
            message_to_send = deepcopy(message)
            message_to_send["group"] = group_name
            async_to_sync(channel_layer.group_send)(group_name, message_to_send)

    def group_names(self, *args, **kwargs) -> Generator[str, None, None]:
        """Generator for each signal and group.

        Return:
            Formatted group name for the signal and observer.
        """
        yield "{}-{}-signal".format(
            self._stable_observer_id, self.func.__name__.replace("_", ".")
        )
