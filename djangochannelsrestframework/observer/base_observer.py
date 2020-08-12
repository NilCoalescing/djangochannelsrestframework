import hashlib
from typing import Any, Dict, Generator, Callable, Optional
from uuid import uuid4

from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.observer.utils import ObjPartial


class BaseObserver:
    def __init__(self, func, partition: str = "*"):
        self.func = func
        self._serializer = None
        self._group_names_for_signal = None
        self._group_names_for_consumer = None

        self._stable_observer_id = f"{partition}-{self.__class__.__name__}-{self.func.__module__}.{self.func.__name__}"

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
        message["type"] = self.func.__name__.replace("_", ".")

        return message

    def serializer(self, func):
        self._serializer = func
        return self

    async def subscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names_for_consumer(
            *args, consumer=consumer, **kwargs
        ):
            await consumer.add_group(group_name)

    async def unsubscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names_for_consumer(
            *args, consumer=consumer, **kwargs
        ):
            await consumer.remove_group(group_name)

    def group_names_for_consumer(
        self, consumer: AsyncAPIConsumer, *args, **kwargs
    ) -> Generator[str, None, None]:
        if self._group_names_for_consumer:
            for group in self._group_names_for_consumer(
                self, *args, consumer=consumer, **kwargs
            ):
                yield self.clean_group_name(
                    "{}-{}".format(self._stable_observer_id, group)
                )
            return
        for group in self.group_names(*args, **kwargs):
            yield self.clean_group_name(group)

    def group_names_for_signal(self, *args, **kwargs) -> Generator[str, None, None]:
        if self._group_names_for_signal:
            for group in self._group_names_for_signal(self, *args, **kwargs):
                yield self.clean_group_name(
                    "{}-{}".format(self._stable_observer_id, group)
                )
            return
        for group in self.group_names(*args, **kwargs):
            yield self.clean_group_name(group)

    def group_names(self, *args, **kwargs):
        raise NotImplementedError()

    def groups_for_consumer(
        self,
        func: Callable[["BaseObserver", AsyncAPIConsumer], Generator[str, None, None]],
    ):
        self._group_names_for_consumer = func
        return self

    def groups_for_signal(self, func: Callable[..., Generator[str, None, None]]):
        self._group_names_for_signal = func
        return self

    def groups(self, func):
        self._group_names_for_consumer = func
        self._group_names_for_signal = func
        return self

    def clean_group_name(self, name):
        # Some chanel layers have a max group name length.
        return f"DCRF-{hashlib.sha256(name.encode()).hexdigest()}"
