import asyncio
from functools import wraps

from channels.db import database_sync_to_async
from django.conf import settings
from django.db import transaction

from djangochannelsrestframework.consumers import AsyncAPIConsumer


def detail_action(**kwargs):
    """
    Used to mark a method on a ResourceBinding that should be routed for detail actions.
    """

    def decorator(func):
        func.action = True
        func.detail = True
        func.kwargs = kwargs
        return func

    return decorator


def list_action(**kwargs):
    """
    Used to mark a method on a ResourceBinding that should be routed for list actions.
    """

    def decorator(func):
        func.action = True
        func.detail = False
        func.kwargs = kwargs
        return func

    return decorator


def action(atomic=None, **kwargs):
    """
    Mark a method as an action.
    """

    def decorator(func):
        if atomic is None:
            _atomic = getattr(settings, "ATOMIC_REQUESTS", False)
        else:
            _atomic = atomic

        func.action = True
        func.kwargs = kwargs
        if asyncio.iscoroutinefunction(func):
            if _atomic:
                raise ValueError("Only synchronous actions can be atomic")
            return func

        if _atomic:
            # wrap function in atomic wrapper
            func = transaction.atomic(func)

        @wraps(func)
        async def async_f(self: AsyncAPIConsumer, *args, **_kwargs):

            result, status = await database_sync_to_async(func)(self, *args, **_kwargs)

            return result, status

        async_f.action = True
        async_f.kwargs = kwargs
        async_f.__name__ = func.__name__

        return async_f

    return decorator
