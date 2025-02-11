from typing import Dict, Any, Type


from channels.consumer import AsyncConsumer
from rest_framework.permissions import BasePermission as DRFBasePermission

from djangochannelsrestframework.scope_utils import ensure_async
from djangochannelsrestframework.scope_utils import request_from_scope


class OperationHolderMixin:
    def __and__(self, other):
        return OperandHolder(AND, self, other)

    def __or__(self, other):
        return OperandHolder(OR, self, other)

    def __rand__(self, other):
        return OperandHolder(AND, other, self)

    def __ror__(self, other):
        return OperandHolder(OR, other, self)

    def __invert__(self):
        return SingleOperandHolder(NOT, self)


class SingleOperandHolder(OperationHolderMixin):
    op1_class: "Type[BasePermission | OperationHolderMixin]"

    def __init__(
        self, operator_class, op1_class: "Type[ BasePermission | OperationHolderMixin]"
    ):
        self.operator_class = operator_class
        self.op1_class = op1_class

    def __call__(self, *args, **kwargs):
        op1 = _ensure_base(self.op1_class)
        return self.operator_class(op1)


class OperandHolder(OperationHolderMixin):
    op1_class: "Type[BasePermission | OperationHolderMixin]"
    op2_class: "Type[BasePermission | OperationHolderMixin]"

    def __init__(
        self,
        operator_class,
        op1_class: "Type[BasePermission | OperationHolderMixin]",
        op2_class: "Type[BasePermission | OperationHolderMixin]",
    ):
        self.operator_class = operator_class
        self.op1_class = op1_class
        self.op2_class = op2_class

    def __call__(self, *args, **kwargs):
        op1 = _ensure_base(self.op1_class)
        op2 = _ensure_base(self.op2_class)
        return self.operator_class(op1, op2)


class AND:
    def __init__(self, op1: "BasePermission", op2: "BasePermission"):
        self.op1 = op1
        self.op2 = op2

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ):
        return await self.op1.has_permission(
            scope, consumer, action, **kwargs
        ) and await self.op2.has_permission(scope, consumer, action, **kwargs)

    async def can_connect(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, **kwargs
    ) -> bool:
        return await self.op1.can_connect(
            scope, consumer, **kwargs
        ) and await self.op2.can_connect(scope, consumer, **kwargs)


class OR:
    def __init__(self, op1: "BasePermission", op2: "BasePermission"):
        self.op1 = op1
        self.op2 = op2

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ):
        return await self.op1.has_permission(
            scope, consumer, action, **kwargs
        ) or await self.op2.has_permission(scope, consumer, action, **kwargs)

    async def can_connect(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, **kwargs
    ) -> bool:
        return await self.op1.can_connect(
            scope, consumer, **kwargs
        ) or await self.op2.can_connect(scope, consumer, **kwargs)


class NOT:
    def __init__(self, op1: "BasePermission"):
        self.op1 = op1

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ):
        return not await self.op1.has_permission(scope, consumer, action, **kwargs)

    async def can_connect(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, **kwargs
    ) -> bool:
        return not await self.op1.can_connect(scope, consumer, **kwargs)


class BasePermissionMetaclass(OperationHolderMixin, type):
    pass


class BasePermission(metaclass=BasePermissionMetaclass):
    """Base permission class

    Notes:
        You should extend this class and override the `has_permission` method to create your own permission class.
        You can also over override`can_connect` to determine if a websocket connection should even be permitted.

    Methods:
        async has_permission (scope, consumer, action, **kwargs)
    """

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        """
        Called on every websocket message sent before the corresponding action handler is called.
        """
        pass

    async def can_connect(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        """
        Called during connection to validate if a given client can establish a websocket connection.

        By default, this returns True and permits all connections to be made.
        """
        return True


class AllowAny(BasePermission):
    """Always allow"""

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        return True


class IsAuthenticated(BasePermission):
    """Allow authenticated users"""

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        user = scope.get("user")
        if not user:
            return False
        return user.pk and user.is_authenticated


class WrappedDRFPermission(BasePermission):

    permission: DRFBasePermission

    mapped_actions = {
        "create": "PUT",
        "update": "PATCH",
        "list": "GET",
        "retrieve": "GET",
        "connect": "HEAD",
    }

    def __init__(self, permission: DRFBasePermission):
        super().__init__()
        self.permission = permission

    async def has_permission(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        request = request_from_scope(scope)
        request.method = self.mapped_actions.get(action, action.upper())
        return await ensure_async(self.permission.has_permission)(request, consumer)

    async def can_connect(
        self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        request = request_from_scope(scope)
        request.method = self.mapped_actions.get("connect", "CONNECT")
        return await ensure_async(self.permission.has_permission)(request, consumer)


def _ensure_base(cls: Type[BasePermission | DRFBasePermission]) -> BasePermission:
    if issubclass(cls, DRFBasePermission):
        return WrappedDRFPermission(permission=cls())
    return cls()
