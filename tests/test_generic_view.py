import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework import serializers

from channels_api.decorators import action
from channels_api.generics import GenericAsyncWebsocketAPIView


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_generic_view():

    results = {}

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        @action()
        def test_sync_action(self, pk=None):
            user = self.get_object(action='test_async_action', pk=pk)

            s = self.get_serializer(
                action='test_async_action',
                action_kwargs={'pk': pk},
                instance=user
            )
            return s.data, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "test_sync_action",
            "pk": 2,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
            "action": "test_sync_action",
            "errors": ["Not found"],
            "response_status": 404,
            "request_id": 1,
            "data": None,
        }

    user = get_user_model().objects.create(
        username='test1', email='test@example.com'
    )

    pk = user.id

    assert get_user_model().objects.filter(pk=pk).exists()

    await communicator.disconnect()

    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {
            "action": "test_sync_action",
            "pk": pk,
            "request_id": 2
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "test_sync_action",
        "errors": [],
        "response_status": 200,
        "request_id": 2,
        "data": {'email': 'test@example.com', 'id': 1, 'username': 'test1'}
    }

    await communicator.disconnect()
