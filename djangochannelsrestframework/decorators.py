import asyncio
from functools import wraps, partial
from typing import Optional

from channels.db import database_sync_to_async
from django.conf import settings
from django.db import transaction

from djangochannelsrestframework.consumers import AsyncAPIConsumer


def action(atomic: Optional[bool] = None, detached: Optional[bool] = None, **kwargs):
    """
    Mark a method as an action.

    .. note::

        Should be used as a method decorator eg: `@action()`


    It can be used on both `async` and `sync` methods.

    .. code-block:: python

        from djangochannelsrestframework.decorators import action

        class MyConsumer(AsyncAPIConsumer):

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

    ----

    When using on `async` methods you can provide an additional
    option `detached=True` so that the method runs detached from the main run-loop of the consumer,
    allowing other actions on the consumer to be called while this action runs.
    This can be useful if the action needs to make further long-running async operations
    such as upstream network requests.

    .. code-block:: python

        from djangochannelsrestframework.decorators import action

        class MyConsumer(AsyncAPIConsumer):

            @action(detached=true)
            async def check_homepage(self, request_id, user_pk, **kwargs):
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://python.org') as response:
                        return dict(response.headers), response.status


    ----

    When using on `sync` methods you can provide an additional
    option `atomic=True` to forcefully wrap the method in a transaction.
    The default value for atomic is determined by django's default db `ATOMIC_REQUESTS` setting.




    """

    def decorator(func):
        _atomic = False
        _detached = False

        if atomic is not None:
            _atomic = atomic

        if detached is not None:
            _detached = detached

        func.action = True
        func.kwargs = kwargs

        if asyncio.iscoroutinefunction(func):
            if _atomic:
                raise ValueError("Only synchronous actions can be atomic")

            if detached:
                return __detached_action(func)
            else:
                return func
        elif detached:
            raise ValueError("Only asynchronous actions can be detached")

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

            response = await database_sync_to_async(func)(self, *args, **_kwargs)

            return response

        async_f.action = True
        async_f.kwargs = kwargs
        async_f.__name__ = func.__name__

        return async_f

    return decorator


def detached(func):
    """
    Sets a method to run detached from the consumers main run-loop.

    You should only do this for methods were you expect the runtime to be long
    (such as awaiting an upstream network request) and what to be able to handle other messages using the
    consumer while waiting.

    If you need a detached :func:`action` then you should use `@action(detached=True)` instead.

    .. note::

        Should be used as a method decorator eg: `@detached`


    This can **only** be applied to async methods:

    .. code-block:: python

        from djangochannelsrestframework.decorators import detached

        class MyConsumer(AsyncAPIConsumer):

            @detached
            async def on_message(self, *args, **kwargs):
                ...

    Methods decorated with `@detached` are canceled when the websocket connection closes.
    """

    @wraps(func)
    async def wrapped_method(self: AsyncAPIConsumer, *args, **kwargs):
        task = asyncio.create_task(func(self, *args, **kwargs))
        task.add_done_callback(
            lambda t: asyncio.create_task(self.handle_detached_task_completion(t))
        )
        self.detached_tasks.append(task)

    return wrapped_method


def __detached_action(func):
    @wraps(func)
    async def wrapped_detached_method(self: AsyncAPIConsumer, *args, **kwargs):
        @wraps(func)
        async def wrapped_action():
            try:
                response = await func(self, *args, **kwargs)

                if isinstance(response, tuple):
                    data, status = response
                    await self.reply(
                        data=data,
                        status=status,
                        action=kwargs.get("action"),
                        request_id=kwargs.get("request_id"),
                    )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                await self.handle_exception(
                    exc=e,
                    action=kwargs.get("action"),
                    request_id=kwargs.get("request_id"),
                )

        task = asyncio.create_task(wrapped_action())
        task.add_done_callback(
            lambda t: asyncio.create_task(self.handle_detached_task_completion(t))
        )
        self.detached_tasks.append(task)

    return wrapped_detached_method
