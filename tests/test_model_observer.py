import asyncio

import pytest
from channels import DEFAULT_CHANNEL_LAYER
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model, user_logged_in
from rest_framework import serializers

from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin
from tests.models import TestModel


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email',)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_model_instance_mixin(settings):
    settings.CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {
                "expiry": 100500,
            },
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self):
            await super().accept()

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    communicator = WebsocketCommunicator(TestConsumer, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "retrieve",
            "pk": 100,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    u1 = await database_sync_to_async(get_user_model().objects.create)(
        username='test1', email='42@example.com'
    )
    u2 = await database_sync_to_async(get_user_model().objects.create)(
        username='test2', email='45@example.com'
    )

    # lookup a pk that is not there
    await communicator.send_json_to(
        {
            "action": "retrieve",
            "pk": u1.id - 1,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    # lookup up u1
    await communicator.send_json_to(
        {
            "action": "retrieve",
            "pk": u1.id,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": [],
        "response_status": 200,
        "request_id": 1,
        "data": {
            'email': '42@example.com', 'id': u1.id, 'username': 'test1'
        }
    }

    # lookup up u1
    await communicator.send_json_to(
        {
            "action": "subscribe_instance",
            "pk": u1.id,
            "request_id": 4
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "subscribe_instance",
        "errors": [],
        "response_status": 201,
        "request_id": 4,
        "data": None
    }

    u3 = await database_sync_to_async(get_user_model().objects.create)(
        username='test3', email='46@example.com'
    )

    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_json_from()

    u1.username = 'thenewname'
    await database_sync_to_async(u1.save)()

    response = await communicator.receive_json_from()

    assert response == {
        "action": "update",
        "errors": [],
        "response_status": 200,
        "request_id": 4,
        "data": {'email': '42@example.com', 'id': 13, 'username': 'thenewname'},
    }

    await database_sync_to_async(u1.delete)()

    response = await communicator.receive_json_from()

    assert response == {
        "action": "delete",
        "errors": [],
        "response_status": 204,
        "request_id": 4,
        "data": {'pk': 13},
    }

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
def test_no_change_of_model():
    class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self):
            await super().accept()

    with pytest.raises(ValueError,
                       match='Subclasses of observed consumers cant change the model class'):
        class SubConsumer(TestConsumer):
            queryset = TestModel.objects.all()
