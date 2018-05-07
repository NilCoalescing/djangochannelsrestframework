from typing import Dict, Any

from channels.consumer import AsyncConsumer


class BasePermission:

    async def has_permission(self, scope: Dict[str, Any],
                             consumer: AsyncConsumer,
                             action: str, **kwargs) -> bool:
        pass


class AllowAny(BasePermission):
    async def has_permission(self, scope: Dict[str, Any],
                             consumer: AsyncConsumer,
                             action: str, **kwargs) -> bool:
        return True


class IsAuthenticated(BasePermission):
    async def has_permission(self,
                             scope: Dict[str, Any],
                             consumer: AsyncConsumer,
                             action: str, **kwargs) -> bool:
        user = scope.get('user')
        if not user:
            return False
        return user.pk and user.is_authenticated
