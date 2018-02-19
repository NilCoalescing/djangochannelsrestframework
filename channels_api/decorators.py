import asyncio

from channels.db import database_sync_to_async

from channels_api.views import AsyncWebsocketAPIView


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


def action(**kwargs):
    """
    Mark a method as an action.
    """
    def decorator(func):
        func.action = True
        func.kwargs = kwargs
        if asyncio.iscoroutinefunction(func):
            return func

        async def async_f(self: AsyncWebsocketAPIView,
                          *args, reply=None, **kwargs,):
            result, status = await database_sync_to_async(func)(
                self, *args, **kwargs
            )
            if reply:
                await reply(data=result, status=status)
            return

        async_f.action = True
        async_f.kwargs = kwargs
        async_f.__name__ = func.__name__

        return async_f

    return decorator
