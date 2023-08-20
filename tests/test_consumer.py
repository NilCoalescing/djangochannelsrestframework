import asyncio

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework.exceptions import Throttled

from djangochannelsrestframework.decorators import action, detached
from djangochannelsrestframework.consumers import AsyncAPIConsumer


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_decorator():

    results = {}

    class AConsumer(AsyncAPIConsumer):
        @action()
        async def test_async_action(self, pk=None, **kwargs):
            results["test_action"] = pk
            return {"pk": pk}, 200

        @action()
        def test_sync_action(self, pk=None, **kwargs):
            results["test_sync_action"] = pk
            return {"pk": pk, "sync": True}, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {"action": "test_async_action", "pk": 2, "request_id": 1}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 2},
        "action": "test_async_action",
        "response_status": 200,
        "request_id": 1,
    }

    await communicator.send_json_to(
        {"action": "test_sync_action", "pk": 3, "request_id": 10}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 3, "sync": True},
        "action": "test_sync_action",
        "response_status": 200,
        "request_id": 10,
    }

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_detached_method():

    results = {}

    class AConsumer(AsyncAPIConsumer):
        @action()
        async def test_async_action(self, pk=None, **kwargs):
            await self.detached_test_method()
            return {"pk": pk}, 200

        @detached
        async def detached_test_method(self):
            await asyncio.sleep(1)
            await self.send_json({"waited": 1})

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {"action": "test_async_action", "pk": 2, "request_id": 1}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 2},
        "action": "test_async_action",
        "response_status": 200,
        "request_id": 1,
    }

    response = await communicator.receive_json_from(timeout=2)

    assert response == {"waited": 1}

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_detached_method_cleanup():

    errors = []

    class AConsumer(AsyncAPIConsumer):
        @action()
        async def test_async_action(self, pk=None, **kwargs):
            await self.detached_test_method()
            return {"pk": pk}, 200

        @detached
        async def detached_test_method(self):
            try:
                await asyncio.sleep(1000)
            except asyncio.CancelledError as e:
                errors.append(e)
                raise

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {"action": "test_async_action", "pk": 2, "request_id": 1}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 2},
        "action": "test_async_action",
        "response_status": 200,
        "request_id": 1,
    }

    await communicator.disconnect()

    assert len(errors) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_detached_action():

    event = asyncio.Event()

    class AConsumer(AsyncAPIConsumer):
        @action(detached=True)
        async def test_detached_async_action(self, pk=None, **kwargs):
            await event.wait()
            return {"pk": pk}, 200

        @action()
        async def test_async_action(self, pk=None, **kwargs):
            return {"pk": pk}, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {"action": "test_detached_async_action", "pk": 2, "request_id": 1}
    )

    await communicator.send_json_to(
        {"action": "test_async_action", "pk": 3, "request_id": 2}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 3},
        "action": "test_async_action",
        "response_status": 200,
        "request_id": 2,
    }

    event.set()

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 2},
        "action": "test_detached_async_action",
        "response_status": 200,
        "request_id": 1,
    }

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_error_in_detached_action():

    event = asyncio.Event()

    class AConsumer(AsyncAPIConsumer):
        @action(detached=True)
        async def test_detached_async_action(self, pk=None, **kwargs):
            await event.wait()
            raise Throttled()

        @action()
        async def test_async_action(self, pk=None, **kwargs):
            return {"pk": pk}, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {"action": "test_detached_async_action", "pk": 2, "request_id": 1}
    )

    await communicator.send_json_to(
        {"action": "test_async_action", "pk": 3, "request_id": 2}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 3},
        "action": "test_async_action",
        "response_status": 200,
        "request_id": 2,
    }

    event.set()

    response = await communicator.receive_json_from()

    assert response == {
        "data": None,
        "action": "test_detached_async_action",
        "response_status": 429,
        "errors": ["Request was throttled."],
        "request_id": 1,
    }

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_error_on_missing_action():

    event = asyncio.Event()

    class AConsumer(AsyncAPIConsumer):
        @action()
        async def test_action(self, pk=None, **kwargs):
            return {}, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to({"pk": 2, "request_id": 1})

    response = await communicator.receive_json_from()

    assert response == {
        "errors": ["Unable to find action in message body."],
        "data": None,
        "action": None,
        "response_status": 405,
        "request_id": 1,
    }

    await communicator.disconnect()
