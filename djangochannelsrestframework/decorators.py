import asyncio
from functools import wraps
from typing import Optional

from channels.db import database_sync_to_async
from django.conf import settings
from django.db import transaction

from djangochannelsrestframework.consumers import (
    AsyncAPIConsumer,
    DetachedTaskConsumerMixin,
)


def action(atomic: Optional[bool] = None, **kwargs):
    """
    Mark a method as an action.

    .. note::

        Should be used as a method decorator eg: `@action()`


    It can be used on both `async` and `sync` methods.

    .. code-block:: python

        from djangochannelsrestframework.decorators import action

        class MyConsumer(AsyncAPIConsumer):
            queryset = User.objects.all()
            serializer_class = UserSerializer

            @action()
            async def delete_user(self, request_id, user_pk, **kwargs):
                ...

    Methods decorated with `@action()` will be called when a json message arrives
    from the client with a matching `action` name.

    The default way of sending a message to call an action is:

    .. code-block:: javascript

        {
         action: "delete_user",
         request_id: 42,
         user_pk: 82
        }


    You can alter how :class:`AsyncAPIConsumer` matches the action using the
    :meth:`get_action_name` method.


    When using on `sync` methods you can provide an additional
    option `atomic=True` to forcefully wrap the method in a transaction.
    The default value for atomic is determined by django's default db `ATOMIC_REQUESTS` setting.
    """

    def decorator(func):
        _atomic = False

        if atomic is not None:
            _atomic = atomic

        func.action = True
        func.kwargs = kwargs

        if asyncio.iscoroutinefunction(func):
            if _atomic:
                raise ValueError("Only synchronous actions can be atomic")
            return func

        # Read out default atomic state from DB connection
        if atomic is None:
            databases = getattr(settings, "DATABASES", {})
            database = databases.get("default", {})
            _atomic = database.get("ATOMIC_REQUESTS", False)

        if _atomic:
            # wrap function in atomic wrapper
            func = transaction.atomic(func)

        @wraps(func)
        async def async_f(self: AsyncAPIConsumer, *args, **_kwargs):
            return await database_sync_to_async(func)(self, *args, **_kwargs)

        async_f.action = True
        async_f.kwargs = kwargs
        async_f.__name__ = func.__name__

        return async_f

    return decorator


def detached_action(**kwargs):
    def decorator(func):
        func.action = True
        func.kwargs = kwargs

        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Only async actions can be detached")

        @wraps(func)
        async def wrapped(
            self: DetachedTaskConsumerMixin, *args, action, request_id, **_kwargs
        ):
            async def method_wrapped():
                result = await func(
                    self, *args, action=action, request_id=request_id, **_kwargs
                )
                if isinstance(result, tuple):
                    data, status = result
                    await self.reply(
                        data=data, status=status, request_id=request_id, action=action
                    )

            loop = asyncio.get_event_loop()
            task = loop.create_task(method_wrapped())
            self._tasks_pending_attachment.append(task)

        wrapped.action = True
        wrapped.kwargs = kwargs
        wrapped.__name__ = func.__name__

        return wrapped

    return decorator
