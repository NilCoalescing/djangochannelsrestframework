import asyncio

import pytest
from asgiref.sync import async_to_sync
from channels import DEFAULT_CHANNEL_LAYER
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from channels.testing import WebsocketCommunicator
from django.contrib.auth import user_logged_in, get_user_model
from django.db import transaction
from django.utils.text import slugify

from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.observer import observer, model_observer


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_wrapper(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self):
            await self.handle_user_logged_in.subscribe()
            await super().accept()

        @observer(user_logged_in)
        async def handle_user_logged_in(self, *args, observer=None, **kwargs):
            await self.send_json({"message": kwargs, "observer": observer is not None})

    communicator = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test", email="test@example.com"
    )

    await database_sync_to_async(user_logged_in.send)(
        sender=user.__class__, request=None, user=user
    )

    response = await communicator.receive_json_from()

    assert {"message": {}, "observer": True} == response

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_wrapper(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_observer_wrapper.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_observer_wrapper(self, message, observer=None, **kwargs):
            await self.send_json(message)

    communicator = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test", email="test@example.com"
    )

    response = await communicator.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.observer.wrapper",
    } == response

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_wrapper_in_transaction(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await TestConsumer.user_change_wrapper_in_transaction.subscribe(self)
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_wrapper_in_transaction(
            self, message, observer=None, **kwargs
        ):
            await self.send_json(message)

    communicator = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    @database_sync_to_async
    def create_user_and_wait():

        with transaction.atomic():
            user = get_user_model().objects.create(
                username="test", email="test@example.com"
            )
            assert async_to_sync(communicator.receive_nothing(timeout=0.1))
            user.username = "mike"
            user.save()
            assert async_to_sync(communicator.receive_nothing(timeout=0.1))
            return user

    user = await create_user_and_wait()

    response = await communicator.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.wrapper.in.transaction",
    } == response

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_delete_wrapper(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumerObserverDelete(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_observer_delete.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_observer_delete(self, message, observer=None, **kwargs):
            await self.send_json(message)

    communicator = WebsocketCommunicator(TestConsumerObserverDelete(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected
    await communicator.receive_nothing()

    user = await database_sync_to_async(get_user_model())(
        username="test", email="test@example.com"
    )
    await database_sync_to_async(user.save)()

    response = await communicator.receive_json_from()
    await communicator.receive_nothing()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.observer.delete",
    } == response
    pk = user.pk

    await database_sync_to_async(user.delete)()

    response = await communicator.receive_json_from()

    await communicator.receive_nothing()

    assert {
        "action": "delete",
        "pk": pk,
        "type": "user.change.observer.delete",
    } == response

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_many_connections_wrapper(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_many_connections_wrapper.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_many_connections_wrapper(self, message, **kwargs):
            await self.send_json(message)

    communicator1 = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator1.connect()

    assert connected

    communicator2 = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator2.connect()

    assert connected

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test", email="test@example.com"
    )

    response = await communicator1.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.many.connections.wrapper",
    } == response

    await communicator1.disconnect()

    response = await communicator2.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.many.connections.wrapper",
    } == response

    await communicator2.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_many_consumers_wrapper(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_many_consumers_wrapper_1.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_many_consumers_wrapper_1(self, message, **kwargs):
            await self.send_json(message)

    class TestConsumer2(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_many_consumers_wrapper_2.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_many_consumers_wrapper_2(self, message, **kwargs):
            await self.send_json(message)

    communicator1 = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator1.connect()

    assert connected

    communicator2 = WebsocketCommunicator(TestConsumer2(), "/testws/")

    connected, _ = await communicator2.connect()

    assert connected

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test", email="test@example.com"
    )

    response = await communicator1.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.many.consumers.wrapper.1",
    } == response

    await communicator1.disconnect()

    response = await communicator2.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.many.consumers.wrapper.2",
    } == response

    await communicator2.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_custom_groups_wrapper(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_custom_groups_wrapper.subscribe(username="test")
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_custom_groups_wrapper(self, message, **kwargs):
            await self.send_json(message)

        @user_change_custom_groups_wrapper.groups
        def user_change_custom_groups_wrapper(
            self, instance=None, username=None, **kwargs
        ):
            if username:
                yield "-instance-username-{}".format(slugify(username))
            else:
                yield "-instance-username-{}".format(instance.username)

    communicator = WebsocketCommunicator(TestConsumer(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test", email="test@example.com"
    )

    response = await communicator.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.custom.groups.wrapper",
    } == response

    await communicator.disconnect()

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test2", email="test@example.com"
    )

    # no event since this is only subscribed to 'test'
    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_json_from()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_custom_groups_wrapper_with_split_function_api(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500,},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumerObserverCustomGroups(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_custom_groups.subscribe(username="test")
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_custom_groups(self, message, **kwargs):
            await self.send_json(message)

        @user_change_custom_groups.groups_for_signal
        def user_change_custom_groups(self, instance=None, **kwargs):
            yield "-instance-username-{}".format(instance.username)

        @user_change_custom_groups.groups_for_consumer
        def user_change_custom_groups(self, username=None, **kwargs):
            yield "-instance-username-{}".format(slugify(username))

    communicator = WebsocketCommunicator(TestConsumerObserverCustomGroups(), "/testws/")

    connected, _ = await communicator.connect()

    assert connected

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test", email="test@example.com"
    )

    response = await communicator.receive_json_from()

    assert {
        "action": "create",
        "pk": user.pk,
        "type": "user.change.custom.groups",
    } == response

    await communicator.disconnect()

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test2", email="test@example.com"
    )

    # no event since this is only subscribed to 'test'
    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_json_from()
