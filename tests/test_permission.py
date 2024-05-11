from typing import Dict, Any

import pytest
from channels.consumer import AsyncConsumer
from channels.testing import WebsocketCommunicator
from rest_framework.permissions import BasePermission as DRFBasePermission

from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.permissions import BasePermission


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_calls_permission_class_called():

    called = {}

    class TestPermission(BasePermission):
        async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
        ) -> bool:
            called["has_permission"] = True
            return True

        async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
        ) -> bool:
            called["can_connect"] = True
            return True

    class AConsumer(AsyncAPIConsumer):
        permission_classes = [TestPermission]

        @action()
        async def target(self, *args, **kwargs):
            return {"response": True}, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    assert called == {"can_connect": True}

    await communicator.send_json_to({"action": "target", "request_id": 10})
    response = await communicator.receive_json_from()

    assert called == {"can_connect": True, "has_permission": True}

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_calls_permission_can_connect_closes():
    class TestPermission(BasePermission):
        async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
        ) -> bool:
            return False

    class AConsumer(AsyncAPIConsumer):
        permission_classes = [TestPermission]

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_users_drf_permission_defaults(settings):

    called = {}

    class TestPermission(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission"] = True
            return True

    class AConsumer(AsyncAPIConsumer):
        permission_classes = [TestPermission]
        pass

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()
    assert connected
    assert called == {"has_permission": True}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_users_drf_or_permission(settings):

    called = {}

    class TestPermissionA(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_a"] = False
            return False

    class TestPermissionB(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_b"] = True
            return True

    class AConsumer(AsyncAPIConsumer):
        permission_classes = [TestPermissionA | TestPermissionB]
        pass

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()
    assert connected
    assert called == {"has_permission_a": False, "has_permission_b": True}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_users_drf_and_permission(settings):

    called = {}

    class TestPermissionA(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_a"] = True
            return True

    class TestPermissionB(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_b"] = True
            return True

    class AConsumer(AsyncAPIConsumer):
        permission_classes = [TestPermissionA & TestPermissionB]
        pass

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()
    assert connected
    assert called == {"has_permission_a": True, "has_permission_b": True}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_users_drf_not_permission(settings):

    called = {}

    class TestPermission(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission"] = False
            return False

    class AConsumer(AsyncAPIConsumer):
        permission_classes = [~TestPermission]
        pass

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()
    assert connected
    assert called == {"has_permission": False}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_users_drf_complex_permission(settings):

    called = {}

    class TestPermissionA(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_a"] = False
            return False

    class TestPermissionB(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_b"] = True
            return True

    class TestPermissionC(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_c"] = True
            return True

    class TestPermissionD(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_d"] = True
            return True

    class TestEPermission(DRFBasePermission):
        def has_permission(self, request, view):
            called["has_permission_e"] = False
            return False

    class AConsumer(AsyncAPIConsumer):
        permission_classes = (
            TestPermissionA | TestPermissionB,
            TestPermissionC & TestPermissionD,
            ~TestEPermission,
        )
        pass

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()
    assert connected
    assert called == {
        "has_permission_a": False,
        "has_permission_b": True,
        "has_permission_c": True,
        "has_permission_d": True,
        "has_permission_e": False
    }
