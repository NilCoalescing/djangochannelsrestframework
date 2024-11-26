import pytest
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from djangochannelsrestframework.consumers import view_as_consumer
from tests.communicator import connected_communicator


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_view_as_consumer():

    results = {}

    class TestView(APIView):
        def get(self, request, format=None):
            results["TestView-get"] = True
            return Response(["test1", "test2"])

    # Test a normal connection
    async with connected_communicator(view_as_consumer(TestView.as_view())) as communicator:

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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_view_as_consumer_get_params():

    results = {}

    class TestView(APIView):
        def get(self, request, format=None):
            results["TestView-get"] = True
            return Response(self.request.GET)

    # Test a normal connection
    async with connected_communicator(view_as_consumer(TestView.as_view())) as communicator:

        await communicator.send_json_to(
            {"action": "retrieve", "request_id": 1, "query": {"value": 1, "othervalue": 42}}
        )

        response = await communicator.receive_json_from()

        assert "TestView-get" in results

        assert response == {
            "errors": [],
            "data": {"value": 1, "othervalue": 42},
            "action": "retrieve",
            "response_status": 200,
            "request_id": 1,
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_view_as_consumer_get_url_params():

    results = {}

    class TestView(viewsets.ViewSet):
        def retrieve(self, request, pk, *args, **kwargs):
            results["TestView-retrieve"] = pk
            return Response(self.request.GET)

    # Test a normal connection
    async with connected_communicator(view_as_consumer(TestView.as_view({"get": "retrieve"}))) as communicator:

        await communicator.send_json_to(
            {"action": "retrieve", "request_id": 1, "parameters": {"pk": 42}}
        )

        response = await communicator.receive_json_from()

        assert results["TestView-retrieve"] == 42

        assert response == {
            "errors": [],
            "data": {},
            "action": "retrieve",
            "response_status": 200,
            "request_id": 1,
        }
