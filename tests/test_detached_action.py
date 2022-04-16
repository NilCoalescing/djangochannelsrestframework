import asyncio

import pytest
from channels.testing import WebsocketCommunicator

from consumers import AsyncAPIConsumer, DetachedTaskConsumerMixin
from decorators import detached_action, action


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_detached_runs_as_expected_as_expected():

    results = {}

    class AConsumer(DetachedTaskConsumerMixin, AsyncAPIConsumer):
        @detached_action()
        async def test_async_action(self, pk=None, **kwargs):
            results["test_action"] = pk
            return {"pk": pk}, 200

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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_detached_runs_detached():

    results = {}

    event = asyncio.Event()

    class AConsumer(DetachedTaskConsumerMixin, AsyncAPIConsumer):
        @detached_action()
        async def test_async_action(self, pk=None, **kwargs):
            await event.wait()
            results["test_action"] = pk
            return {"pk": pk}, 200

        @action()
        async def other_action(self, pk=None, **kwargs):
            return {"pk": pk}, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {"action": "test_async_action", "pk": 2, "request_id": 1}
    )

    await communicator.send_json_to(
        {"action": "other_action", "pk": 2, "request_id": 1}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 2},
        "action": "other_action",
        "response_status": 200,
        "request_id": 1,
    }

    event.set()

    response = await communicator.receive_json_from()

    assert response == {
        "errors": [],
        "data": {"pk": 2},
        "action": "test_async_action",
        "response_status": 200,
        "request_id": 1,
    }

    await communicator.disconnect()
