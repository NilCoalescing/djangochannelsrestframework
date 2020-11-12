import pytest
from channels.testing import WebsocketCommunicator

from djangochannelsrestframework.decorators import action
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
