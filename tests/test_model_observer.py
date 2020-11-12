import asyncio

import pytest
from channels import DEFAULT_CHANNEL_LAYER
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model, user_logged_in
from rest_framework import serializers

from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin
from tests.models import TestModel


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_model_instance_mixin(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    communicator = WebsocketCommunicator(TestConsumer(), "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"action": "retrieve", "pk": 100, "request_id": 1})

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None,
    }

    u1 = await database_sync_to_async(get_user_model().objects.create)(
        username="test1", email="42@example.com"
    )
    u2 = await database_sync_to_async(get_user_model().objects.create)(
        username="test2", email="45@example.com"
    )

    # lookup a pk that is not there
    await communicator.send_json_to(
        {"action": "retrieve", "pk": u1.id - 1, "request_id": 1}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None,
    }

    # lookup up u1
    await communicator.send_json_to(
        {"action": "retrieve", "pk": u1.id, "request_id": 1}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": [],
        "response_status": 200,
        "request_id": 1,
        "data": {"email": "42@example.com", "id": u1.id, "username": "test1"},
    }

    # lookup up u1
    await communicator.send_json_to(
        {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "subscribe_instance",
        "errors": [],
        "response_status": 201,
        "request_id": 4,
        "data": None,
    }

    u3 = await database_sync_to_async(get_user_model().objects.create)(
        username="test3", email="46@example.com"
    )

    # lookup up u1
    await communicator.send_json_to(
        {
            "action": "update_username",
            "pk": u1.id,
            "username": "thenewname",
            "request_id": 5,
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "update_username",
        "errors": [],
        "response_status": 200,
        "request_id": 5,
        "data": {"pk": u1.id},
    }

    response = await communicator.receive_json_from()

    assert response == {
        "action": "update",
        "errors": [],
        "response_status": 200,
        "request_id": 4,
        "data": {"email": "42@example.com", "id": u1.id, "username": "thenewname"},
    }

    await database_sync_to_async(u1.delete)()

    response = await communicator.receive_json_from()

    assert response == {
        "action": "delete",
        "errors": [],
        "response_status": 204,
        "request_id": 4,
        "data": {"pk": 13},
    }

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_two_observer_model_instance_mixins(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestUserConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    class TestOtherConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = TestModel.objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, name=None, **kwargs):
            tm = await database_sync_to_async(self.get_object)(pk=pk)
            tm.name = name
            await database_sync_to_async(tm.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    communicator1 = WebsocketCommunicator(TestOtherConsumer(), "/testws/")
    connected, _ = await communicator1.connect()
    assert connected

    # Test a normal connection
    communicator2 = WebsocketCommunicator(TestUserConsumer(), "/testws/")
    connected, _ = await communicator2.connect()
    assert connected

    u1 = await database_sync_to_async(get_user_model().objects.create)(
        username="test1", email="42@example.com"
    )
    t1 = await database_sync_to_async(TestModel.objects.create)(name="test2")

    await communicator1.send_json_to(
        {"action": "subscribe_instance", "pk": t1.id, "request_id": 4}
    )

    response = await communicator1.receive_json_from()

    assert response == {
        "action": "subscribe_instance",
        "errors": [],
        "response_status": 201,
        "request_id": 4,
        "data": None,
    }

    await communicator2.send_json_to(
        {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
    )

    response = await communicator2.receive_json_from()

    assert response == {
        "action": "subscribe_instance",
        "errors": [],
        "response_status": 201,
        "request_id": 4,
        "data": None,
    }

    # update the user

    u1.username = "no not a value"

    await database_sync_to_async(u1.save)()

    # user is updated
    await communicator2.receive_json_from()

    # test model is not
    assert await communicator1.receive_nothing()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_unsubscribe_observer_model_instance_mixin(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumerUnsubscribe(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    communicator = WebsocketCommunicator(TestConsumerUnsubscribe(), "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    u1 = await database_sync_to_async(get_user_model().objects.create)(
        username="test1", email="42@example.com"
    )

    # lookup up u1
    await communicator.send_json_to(
        {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
    )

    response = await communicator.receive_json_from()
    assert await communicator.receive_nothing()

    assert response == {
        "action": "subscribe_instance",
        "errors": [],
        "response_status": 201,
        "request_id": 4,
        "data": None,
    }

    await communicator.send_json_to(
        {
            "action": "update_username",
            "pk": u1.id,
            "username": "thenewname",
            "request_id": 5,
        }
    )

    a = await communicator.receive_json_from()

    b = await communicator.receive_json_from()

    assert {
        "action": "update_username",
        "errors": [],
        "response_status": 200,
        "request_id": 5,
        "data": {"pk": u1.id},
    } in [a, b]

    assert {
        "action": "update",
        "errors": [],
        "response_status": 200,
        "request_id": 4,
        "data": {"email": "42@example.com", "id": u1.pk, "username": "thenewname"},
    } in [a, b]

    # unsubscribe
    # lookup up u1

    await communicator.send_json_to(
        {"action": "unsubscribe_instance", "pk": u1.id, "request_id": 4}
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "unsubscribe_instance",
        "errors": [],
        "response_status": 204,
        "request_id": 4,
        "data": None,
    }
    assert await communicator.receive_nothing()

    await communicator.send_json_to(
        {
            "action": "update_username",
            "pk": u1.id,
            "username": "thenewname",
            "request_id": 5,
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "update_username",
        "errors": [],
        "response_status": 200,
        "request_id": 5,
        "data": {"pk": u1.id},
    }

    await communicator.disconnect()
