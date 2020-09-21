import pytest
from channels.testing import WebsocketCommunicator

from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.consumers import AsyncAPIConsumer


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_no_action_keyword_request():

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

    # Test a normal connection with malformed request: the action keyword is missing
    communicator = WebsocketCommunicator(AConsumer, "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to({"pk": 2, "request_id": 1})

    response = await communicator.receive_json_from()

    assert response == {
        {
            "errors": ['Method "None" not allowed.'],
            "response_status": 405,
            "request_id": 1,
        }
    }

    await communicator.disconnect()
