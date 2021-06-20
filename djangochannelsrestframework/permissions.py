from typing import Dict, Any

from channels.consumer import AsyncConsumer


class BasePermission:
    """Base permision class

    Notes:
        You should extend this class and overide the `has_permision` method to create your own permission class.

    Methods:
        async has_permision (scope, consumer, action, **kwargs)
    """

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        pass


class AllowAny(BasePermission):
    """Allow any permision class"""

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        return True


class IsAuthenticated(BasePermission):
    """Allow authenticated only class"""

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        user = scope.get("user")
        if not user:
            return False
        return user.pk and user.is_authenticated
