Permissions
===========

Permissions can be applied to :class:`~djangochannelsrestframework.consumers.AsyncAPIConsumer`
and its subclasses, such as :class:`~djangochannelsrestframework.generics.GenericAsyncAPIConsumer`.

This is done by setting the `permission_classes = [TestPermission]` property of the consumer.

.. code-block:: python

    from djangochannelsrestframework.consumers import AsyncAPIConsumer
    from djangochannelsrestframework.permissions import IsAuthenticated

    class RoomConsumer(AsyncAPIConsumer):
        permission_classes = [IsAuthenticated]




You can also combine permission classes using boolean operations: ``| & !`` are the supported operations.

.. code-block:: python

    from djangochannelsrestframework.consumers import AsyncAPIConsumer
    from djangochannelsrestframework.permissions import IsAuthenticated

    class RoomConsumer(AsyncAPIConsumer):
        permission_classes = [
            MyCustomPermission | IsAuthenticated
        ]



In addition to subclassing :class:`~djangochannelsrestframework.permissions.BasePermission` You can also use any
`rest_framework.permissions.BasePermission` on a consumer, you may need to update your subclasses to handle the
`CONNECT` method, as the `has_permission` method is called with a proxy request using a `CONNECT` method string.

.. automodule:: djangochannelsrestframework.permissions
    :members:
    :exclude-members: WrappedDRFPermission