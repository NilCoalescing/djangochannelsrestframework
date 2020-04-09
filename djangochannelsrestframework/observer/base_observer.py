from typing import Any, Dict, Generator
from uuid import uuid4

from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.observer.utils import ObjPartial


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
        message["type"] = self.func.__name__.replace("_", ".")

        return message

    def serializer(self, func):
        self._serializer = func
        return self

    async def subscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names(*args, consumer=consumer, **kwargs):
            await consumer.add_group(group_name)

    async def unsubscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names(*args, consumer=consumer, **kwargs):
            await consumer.remove_group(group_name)

    def group_names(self, *args, **kwargs) -> Generator[str, None, None]:
        if self._group_names:
            for group in self._group_names(*args, **kwargs):
                yield "{}-{}".format(self._uuid, group)
            return
        raise NotImplementedError()

    def groups(self, func):
        self._group_names = func
        return self
