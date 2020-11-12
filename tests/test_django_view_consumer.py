import pytest
from channels.testing import WebsocketCommunicator
from rest_framework.response import Response
from rest_framework.views import APIView

from djangochannelsrestframework.consumers import view_as_consumer


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_view_as_consumer():

    results = {}

    class TestView(APIView):
        def get(self, request, format=None):
            results["TestView-get"] = True
            return Response(["test1", "test2"])

    # Test a normal connection
    communicator = WebsocketCommunicator(
        view_as_consumer(TestView.as_view()), "/testws/"
    )

    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"action": "retrieve", "request_id": 1})

    response = await communicator.receive_json_from()

    assert "TestView-get" in results

    assert response == {
        "errors": [],
        "data": ["test1", "test2"],
        "action": "retrieve",
        "response_status": 200,
        "request_id": 1,
    }
